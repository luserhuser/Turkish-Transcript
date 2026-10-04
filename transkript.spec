# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all

# Collect packages with data files and native DLLs
packages_to_collect = [
    'faster_whisper',
    'ctranslate2',
    'onnxruntime',
    'webview',
    'pythonnet',
    'clr_loader',
    'av',
    'tokenizers',
]

datas = [
    ('ui', 'ui'),
    ('models/small', 'models/small'),
]
binaries = []
hiddenimports = [
    'engine',
    'engine.audio',
    'engine.checkpoint',
    'engine.domain_vocabulary',
    'engine.exceptions',
    'engine.hardware',
    'engine.logging_config',
    'engine.transcriber',
    'tkinter',
    'tkinter.filedialog',
    'psutil',
]

for pkg in packages_to_collect:
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
        datas.extend(pkg_datas)
        binaries.extend(pkg_binaries)
        hiddenimports.extend(pkg_hidden)
    except Exception as e:
        print(f"Warning collecting {pkg}: {e}")

# Exclude heavy unnecessary modules to keep build lightweight & fast
excludes = [
    'torch',
    'torchvision',
    'torchaudio',
    'scipy',
    'matplotlib',
    'pandas',
    'pydeck',
    'altair',
    'streamlit',
    'IPython',
    'notebook',
    'jupyter',
    'openai-whisper',
    'google',
    'google.generativeai',
    'moviepy',
    'auto_editor',
]

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Transkript',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Transkript',
)
