import os
import re
from PyInstaller.building.api import PYZ, EXE, COLLECT
from PyInstaller.building.build_main import Analysis

onefile = False
name = 'squoosh-native'

match (os.name):
    case 'nt':
        dllext = '.dll'
    case 'posix':
        dllext = '.so'
    case _:
        raise NotImplementedError(f'Not supported on os.name = {os.name}')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        (f'libsvpng{dllext}', '.'),
        ('squoosh.pak', '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # PySide6-Essentials
        # https://pypi.org/project/PySide6-Essentials/
        # 'PySide6.QtCore',
        # 'PySide6.QtGui',
        # 'PySide6.QtWidgets',
        'PySide6.QtHelp',
        # 'PySide6.QtNetwork',
        'PySide6.QtConcurrent',
        'PySide6.QtDBus',
        'PySide6.QtDesigner',
        'PySide6.QtOpenGL',
        'PySide6.QtOpenGLWidgets',
        # 'PySide6.QtPrintSupport',
        'PySide6.QtQml',
        'PySide6.QtQuick',
        'PySide6.QtQuickControls2',
        'PySide6.QtQuickWidgets',
        'PySide6.QtXml',
        'PySide6.QtTest',
        'PySide6.QtSql',
        'PySide6.QtSvg',
        'PySide6.QtSvgWidgets',
        'PySide6.QtUiTools',
        # PySide6-Addons
        # https://pypi.org/project/PySide6-Addons/
        'PySide6.Qt3DAnimation',
        'PySide6.Qt3DCore',
        'PySide6.Qt3DExtras',
        'PySide6.Qt3DInput',
        'PySide6.Qt3DLogic',
        'PySide6.Qt3DRender',
        'PySide6.QtAxContainer',
        'PySide6.QtBluetooth',
        'PySide6.QtCharts',
        'PySide6.QtDataVisualization',
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
        'PySide6.QtNetworkAuth',
        'PySide6.QtNfc',
        'PySide6.QtPositioning',
        'PySide6.QtQuick3D',
        'PySide6.QtRemoteObjects',
        'PySide6.QtScxml',
        'PySide6.QtSensors',
        'PySide6.QtSerialPort',
        'PySide6.QtStateMachine',
        'PySide6.QtVirtualKeyboard',
        # 'PySide6.QtWebChannel',
        # 'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineQuick',
        # 'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebSockets',
        'PySide6.QtPdf',
        'PySide6.QtPdfWidgets',
        'PySide6.QtHttpServer',
    ],
    noarchive=False,
)

locales = {
    'zh_CN',
}

d = a.datas
a.datas = []
for entry in d:
    path = entry[0].replace('\\', '/')
    # Remove unnecessary files from /usr/share when building with webview[gtk]
    if path.startswith('share'):
        continue
    # Remove unused locales when building with webview[pyside6]
    if (m := re.search(r'^PySide6/Qt/translations/qt(?:base|webengine)?_((?:(?<!help_).)+?)\.qm$', path)) and m.group(1) not in locales:
        continue
    if (m := re.search(r'^PySide6/Qt/translations/qt_help_(.+?)\.qm$', path)) and m.group(1) not in locales:
        continue
    if (m := re.search(r'^PySide6/Qt/translations/qtwebengine_locales/(.+?)\.pak$', path)) and m.group(1).replace('-', '_') not in locales:
        continue
    # Remove setuptools dist-info on Windows
    if re.search(r'^setuptools-\d+\.\d+\.\d+\.dist-info', path):
        continue
    # Remove Android support
    if path == 'webview/lib/pywebview-android.jar':
        continue
    # Remove clr-loader x86 dlls
    if path.startswith('clr_loader/ffi/dlls/x86'):
        continue
    a.datas.append(entry)

for entry in sorted(a.datas):
    print(entry, os.path.getsize(entry[1]) if entry[2] != 'SYMLINK' else None)

d = a.binaries
a.binaries = []
for entry in d:
    path = entry[0].replace('\\', '/')
    # Remove MSVCRT/UCRT dlls on Windows
    if entry[0].startswith('api-ms-win-') or entry[0] in {'ucrtbase.dll', 'VCRUNTIME140.dll', 'VCRUNTIME140_1.dll'}:
        continue
    # Remove MSHTML support
    if (m := re.search(r'^webview/lib/WebBrowserInterop\.x(?:64|86)\.dll$', path)):
        continue
    a.binaries.append(entry)

for entry in sorted(a.binaries):
    print(entry, os.path.getsize(entry[1]) if entry[2] != 'SYMLINK' else None)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    *((
        a.binaries,
        a.zipfiles,
        a.datas,
    ) if onefile else ()),
    [],
    **({
        'exclude_binaries': True,
    } if not onefile else {}),
    name=name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=os.name != 'nt',
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon='icon/icon.ico',
    contents_directory='internal',
)

if not onefile:
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=os.name != 'nt',
        upx=True,
        upx_exclude=[],
        name=name,
    )
