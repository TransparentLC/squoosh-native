import base64
import bottle
import datetime
import hashlib
import json
import mimetypes
import msgpack
import os
import sys
import traceback
import typing
import webview
import zipfile
from webview.dom import DOMEventHandler

__all__ = [
    'app',
    'expose',
    'mount',
    'exposeDnDHook',
    'initMsgpackApi',
    'WVResourceLocal',
    'WVResourceZip',
    'WVResourceObfuscatedZip',
]

# Misconfigure (text/plain) on Windows?
mimetypes.add_type('text/javascript', '.js')
mimetypes.add_type('text/javascript', '.mjs')

# 是否使用PyInstaller打包
isFrozen = hasattr(sys, '_MEIPASS') and getattr(sys, 'frozen', False)
# 非打包：执行的py文件所在的路径 打包：contents directory的路径
contentPath: str = os.path.realpath(sys._MEIPASS if isFrozen else '')
# 非打包：执行的py文件所在的路径 打包：exe所在的路径
executablePath = os.path.dirname(os.path.realpath(sys.executable if isFrozen else __file__))

class WVResourceInfo(typing.NamedTuple):
    size: int
    mtime: datetime.datetime

class WVResource:
    def __init__(self) -> None:
        raise NotImplementedError()

    def transform(self, path: str) -> str:
        return path

    def exists(self, path: str) -> bool:
        raise NotImplementedError()

    def info(self, path: str) -> WVResourceInfo:
        raise NotImplementedError()

    def open(self, path: str) -> typing.BinaryIO:
        raise NotImplementedError()

class WVResourceLocal(WVResource):
    def __init__(self, root: str) -> None:
        self.root = root

    def transform(self, path: str) -> str:
        return os.path.join(self.root, path)

    def exists(self, path: str) -> bool:
        return os.path.exists(path)

    def info(self, path: str) -> WVResourceInfo:
        return WVResourceInfo(
            size=os.path.getsize(path),
            mtime=datetime.datetime.fromtimestamp(os.path.getmtime(path)),
        )

    def open(self, path: str) -> typing.BinaryIO:
        return open(path, 'rb')

class WVResourceZip(WVResource):
    def __init__(self, zippath: str) -> None:
        self.zip = zipfile.ZipFile(zippath, 'r')

    def exists(self, path: str) -> bool:
        return path in self.zip.namelist()

    def info(self, path: str) -> WVResourceInfo:
        info = self.zip.getinfo(path)
        return WVResourceInfo(
            size=info.file_size,
            mtime=datetime.datetime(*info.date_time),
        )

    def open(self, path: str) -> typing.BinaryIO:
        return self.zip.open(path, 'r')

class WVResourceObfuscatedZip(WVResourceZip):
    def __init__(self, zippath: str, salt: bytes) -> None:
        super().__init__(zippath)
        self.hctx = hashlib.blake2b(digest_size=16, salt=salt)

    def transform(self, path: str) -> str:
        hctx = self.hctx.copy()
        hctx.update(path.encode('utf-8'))
        return base64.b85encode(hctx.digest()).decode().replace('*', '[').replace('?', ']')

mountmap: dict[str, list[WVResource]] = {}
msgpackApimap: dict[str, typing.Callable] = {}

def mount(mountpoint: str, resource: WVResource):
    '''
    在内置HTTP Server的指定URL前缀下挂载资源包
    查找资源时按照挂载的URL前缀从长到短和挂载顺序从后到前来读取资源

    Parameters
    ----------
    mountpoint : str
        挂载的URL前缀
    resource : WVResource
        资源包
    '''
    if mountpoint not in mountmap:
        mountmap[mountpoint] = []
        for k in sorted(mountmap, key=len, reverse=True):
            mountmap[k] = mountmap.pop(k)
    mountmap[mountpoint].insert(0, resource)

app = bottle.Bottle()

@app.post('/api/<fn>')
def _(fn: str):
    if (func := msgpackApimap.get(fn, None)) is None:
        return bottle.HTTPError(404)
    if bottle.request.headers['Content-Type'] != 'application/msgpack':
        return bottle.HTTPError(400)
    try:
        return bottle.HTTPResponse(msgpack.dumps((True, func(*msgpack.load(bottle.request.body)))), headers={'Content-Type': 'application/msgpack'})
    except Exception as ex:
        traceback.print_exc()
        return bottle.HTTPResponse(msgpack.dumps((False, [type(ex).__name__, str(ex)])), headers={'Content-Type': 'application/msgpack'})

@app.get('/')
@app.get('/<_:path>')
def _(**kwargs):
    if bottle.request.environ.get('HTTP_USER_AGENT') != webview.token:
        return bottle.HTTPError(403)
    pathUri: str = bottle.request.path
    if pathUri.endswith('/'):
        pathUri += 'index.html'
    for k in mountmap:
        if not pathUri.startswith(k):
            continue
        for r in mountmap[k]:
            path = r.transform(pathUri.removeprefix(k))
            if not r.exists(path):
                continue
            info = r.info(path)
            if ims := bottle.request.environ.get('HTTP_IF_MODIFIED_SINCE'):
                ims = bottle.parse_date(ims.split(';')[0].strip())
            if ims is not None and ims >= info.mtime.timestamp():
                return bottle.HTTPResponse(status=304, date=datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'))
            headers = {
                'Content-Length': info.size,
                'Last-Modified': info.mtime.strftime('%a, %d %b %Y %H:%M:%S GMT'),
                'Accept-Ranges': 'bytes',
            }
            mimetype, encoding = mimetypes.guess_type(pathUri)
            if mimetype:
                headers['Content-Type'] = mimetype
                if mimetype.startswith('text/'):
                    headers['Content-Type'] += ';charset=utf-8'
            if encoding:
                headers['Content-Encoding'] = encoding
            body = '' if bottle.request.method == 'HEAD' else r.open(path)
            if 'HTTP_RANGE' in bottle.request.environ:
                if not (ranges := list(bottle.parse_range_header(bottle.request.environ['HTTP_RANGE'], info.size))):
                    return bottle.HTTPError(416, 'Requested Range Not Satisfiable')
                offset, end = ranges[0]
                headers['Content-Range'] = f'bytes {offset}-{end - 1}/{info.size}'
                headers['Content-Length'] = end - offset
                if body:
                    body = bottle._file_iter_range(body, offset, end - offset)
                return bottle.HTTPResponse(body, status=206, **headers)
            return bottle.HTTPResponse(body, **headers)
    return bottle.HTTPError(404)

def expose(window: webview.Window, name: typing.Optional[str]):
    '''
    在JS环境中导出Python环境的函数

    Parameters
    ----------
    window : webview.Window
        需要导出函数的窗口
    name : typing.Optional[str]
        在JS环境下导出的函数的名称，默认为Python环境下的函数名称
    '''
    def decorator(f: typing.Callable):
        n, f.__name__ = f.__name__, name or f.__name__
        window.expose(f)
        f.__name__ = n
        return f
    return decorator

def exposeMsgpack(window: webview.Window, name: typing.Optional[str]):
    '''
    在JS环境中导出Python环境的函数
    和pywebview自带的Window.expose不同在于使用msgpack而不是JSON通信，因此可以传输二进制数据

    Parameters
    ----------
    window : webview.Window
        需要导出函数的窗口
    name : typing.Optional[str]
        在JS环境下导出的函数的名称，默认为Python环境下的函数名称
    '''
    def decorator(f: typing.Callable):
        msgpackApimap[name] = f
        window.evaluate_js(f'window.pywebview.api["{name}"] = (...args) => window.pywebview._callMsgpackApi("{name}", ...args)')
        return f
    return decorator

def initMsgpackApi(window: webview.Window):
    window.evaluate_js('''
        window.pywebview._callMsgpackApi = (fn, ...args) => fetch(
            `/api/${fn}`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/msgpack',
                },
                body: msgpack.encode(args),
            },
        )
                .then(r => {
                    if (r.status >= 400) throw new Error(r.statusText);
                    return r.arrayBuffer();
                })
                .then(r => {
                    const [success, result] = msgpack.decode(r);
                    if (!success) throw new Error(`${result[0]}: ${result[1]}`);
                    return result;
                })
    ''')

def exposeDnDHook(window: webview.Window):
    '''
    添加拖拽相关支持
    需要先执行await pywebview.api.hookDnD()
    然后使用pywebview.dnd.callbacks.{add,remove}添加或删除函数，Event参数和ondrop类似

    Parameters
    ----------
    window : webview.Window
        需要添加拖拽相关支持的窗口
    '''
    @expose(window, 'hookDnD')
    def _():
        def noop(*args, **kwargs):
            pass

        def onDrop(e):
            if len(e['dataTransfer']['files']) == 0:
                return
            window.evaluate_js('window.pywebview.dnd.handler(' + json.dumps(e) + ')')

        window.evaluate_js('''
            window.pywebview.dnd = {
                callbacks: new Set,
                handler(e) {
                    this.callbacks.forEach(fn => fn(e));
                },
            };
        ''')
        window.dom.document.events.dragenter += DOMEventHandler(noop, True, True)
        window.dom.document.events.dragstart += DOMEventHandler(noop, True, True)
        window.dom.document.events.dragover += DOMEventHandler(noop, True, True)
        window.dom.document.events.drop += DOMEventHandler(onDrop, True, True)
