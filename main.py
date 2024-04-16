import os
import pprint
import shlex
import subprocess
import tempfile
import threading
import time
import typing
import webview
import wvruntime
from concurrent.futures import ThreadPoolExecutor

import image_cli
import svpng

DEBUG = bool(os.environ.get('DEBUG') and not wvruntime.isFrozen)

def noConcurrency(defaultReturn: typing.Any = None):
    counter = 0
    counterLock = threading.Lock()
    functionLock = threading.Lock()
    def decorator(f: typing.Callable):
        def wrapper(*args, **kwargs):
            nonlocal counter
            with counterLock:
                counter += 1
                x = counter
            with functionLock:
                if x != counter:
                    return defaultReturn
                return f(*args, **kwargs)
        return wrapper
    return decorator

def init(window: webview.Window):
    wvruntime.initMsgpackApi(window)
    wvruntime.exposeDnDHook(window)

    @wvruntime.expose(window, 'fileDialog')
    def _(kwargs={}):
        return window.create_file_dialog(**kwargs)

    @wvruntime.exposeMsgpack(window, 'readFile')
    def _(file: str, size: int | None = None):
        with open(file, 'rb') as f:
            return f.read(size)

    @wvruntime.exposeMsgpack(window, 'writeFile')
    def _(file: str, data: bytes):
        with open(file, 'wb') as f:
            f.write(data)

    @wvruntime.expose(window, 'checkCodec')
    def _():
        return image_cli.checkCodec()

    @wvruntime.expose(window, 'checkMetric')
    def _():
        return image_cli.checkMetric()

    @wvruntime.exposeMsgpack(window, 'compressImage')
    @noConcurrency(b'')
    def _(image: image_cli.ImageData, encoderState: image_cli.EncoderState):
        pprint.pprint(encoderState)
        if encoderState['type'] not in image_cli.encoderOptionsClassMapping:
            raise RuntimeError(f'Invalid encoder type: {encoderState['type']}')
        encoderOptionsClass = image_cli.encoderOptionsClassMapping[encoderState['type']]
        tempInput = tempfile.mktemp('.png')
        tempOutput = tempfile.mktemp()
        ts = time.perf_counter()
        svpng.write(tempInput, image['width'], image['height'], image['data'], True)
        command = encoderOptionsClass(**encoderState['options']).buildCommand(tempInput, tempOutput)
        print(shlex.join(command))
        subprocess.check_call(command, creationflags=(not DEBUG and subprocess.CREATE_NO_WINDOW))
        te = time.perf_counter()
        print('Encode time:', te - ts)
        os.remove(tempInput)
        with open(tempOutput, 'rb') as f:
            d = f.read()
        os.remove(tempOutput)
        return d

    @wvruntime.exposeMsgpack(window, 'calculateMetrics')
    @noConcurrency()
    def _(original: image_cli.ImageData, distorted: image_cli.ImageData):
        originalFile = tempfile.mktemp('.png')
        distortedFile = tempfile.mktemp('.png')
        ts = time.perf_counter()
        svpng.write(originalFile, original['width'], original['height'], original['data'], True)
        svpng.write(distortedFile, distorted['width'], distorted['height'], distorted['data'], True)
        cm = image_cli.checkMetric()
        with ThreadPoolExecutor() as executor:
            r = dict((
                *executor.map(
                    lambda x: (x, image_cli.metricClassMapping[x].calculate(originalFile, distortedFile)),
                    (k for k, v in cm.items() if v),
                ),
                *((k, None) for k, v in cm.items() if not v),
            ))
        te = time.perf_counter()
        print('Metrics time:', te - ts)
        os.remove(originalFile)
        os.remove(distortedFile)
        return r

    window.evaluate_js('window.dispatchEvent(new CustomEvent("pywebviewapiready"))')

wvruntime.mount('/', (
    wvruntime.WVResourceLocal(os.path.join(wvruntime.contentPath, 'squoosh/.tmp/build/static'))
    if DEBUG else
    wvruntime.WVResourceObfuscatedZip(os.path.join(wvruntime.contentPath, 'squoosh.pak'), b'$qu0Osh-N4t1v3!!')
))

if DEBUG:
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--remote-allow-origins=*'

webview.start(
    func=init,
    args=webview.create_window('Squoosh Native', wvruntime.app, width=1080, height=800, min_size=(800, 600)),
    debug=DEBUG,
    user_agent=webview.token,
)
