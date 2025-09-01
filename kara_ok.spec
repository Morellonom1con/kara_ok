# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['kara_ok.py'],
    pathex=[],
    binaries=[],
    datas=[('lyrics_fetcher.js', '.'), ('json_to_lrc.js', '.'), ('cache', 'cache'), ('current_queue', 'current_queue'), ('output', 'output')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='kara_ok',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
