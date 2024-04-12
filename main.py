import os
import pprint
import shlex
import subprocess
import tempfile
import time
import webview
import wvruntime

import image_codec
import svpng

DEBUG = bool(os.environ.get('DEBUG') and not wvruntime.isFrozen)

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
        return image_codec.checkCodec()

    @wvruntime.exposeMsgpack(window, 'compressImage')
    def _(image: image_codec.ImageData, encoderState: image_codec.EncoderState):
        pprint.pprint(encoderState)
        if encoderState['type'] not in image_codec.encoderOptionsClassMapping:
            raise RuntimeError(f'Invalid encoder type: {encoderState['type']}')
        encoderOptionsClass = image_codec.encoderOptionsClassMapping[encoderState['type']]
        tempInput = tempfile.mktemp('.png')
        tempOutput = tempfile.mktemp()
        ts = time.perf_counter()
        svpng.write(tempInput, image['width'], image['height'], image['data'], True)
        command = encoderOptionsClass(**encoderState['options']).buildCommand(tempInput, tempOutput)
        print(shlex.join(command))
        subprocess.check_call(command, creationflags=(not DEBUG and subprocess.CREATE_NO_WINDOW))
        te = time.perf_counter()
        os.remove(tempInput)
        print('Encode time:', te - ts)
        with open(tempOutput, 'rb') as f:
            d = f.read()
        os.remove(tempOutput)
        return d

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
