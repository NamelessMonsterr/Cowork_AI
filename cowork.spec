# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Cowork AI Assistant.

Build with: pyinstaller cowork.spec
"""

import sys
import os

block_cipher = None

# Collect data files
datas = [
    # Config files
    ('assistant/config', 'assistant/config'),
]

# Hidden imports for dynamic imports
hiddenimports = [
    # FastAPI
    'fastapi',
    'uvicorn',
    'starlette',
    'pydantic',
    
    # Windows automation
    'pywinauto',
    'pywinauto.controls',
    'pywinauto.controls.uiawrapper',
    'pyautogui',
    'keyboard',
    
    # Screen capture
    'mss',
    'PIL',
    'cv2',
    'numpy',
    
    # OCR
    'screen_ocr',
    
    # Voice
    'faster_whisper',
    'edge_tts',
    'sounddevice',
    
    # Async
    'asyncio',
    'websockets',
]

# Exclude unnecessary packages
excludes = [
    'tkinter',
    'matplotlib',
    'scipy',
    'jupyter',
    'IPython',
    'pytest',
]

a = Analysis(
    ['assistant/main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CoworkAssistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI mode
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
)
