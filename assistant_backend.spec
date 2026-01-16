# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['assistant/entrypoints/backend_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assistant', 'assistant'), # Bundle whole package structure
        # Add config/assets if needed
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan.on',
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
        'dxcam',
        'faster_whisper',
        'websockets.legacy',
        'websockets.legacy.server',
        'engineio.async_drivers.aiohttp',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'test', 'unittest', 'email', 'http.server', 'xmlrpc', 'xml'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='assistant-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # Set to False for GUI-only (hide console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='assistant-backend',
)
