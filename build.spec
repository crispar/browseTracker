# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Browser Link Tracker.
Build with: pyinstaller build.spec
"""

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        # Include any data files if needed
        # ('assets/icon.ico', 'assets'),
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'sqlite3',
        'urllib.parse',
        'webbrowser',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'pygame',
        'pytest',
        'black',
    ],
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
    name='LinkTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False to hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
    icon='assets/icon.ico' if Path('assets/icon.ico').exists() else None,
)