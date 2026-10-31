# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build for the Maze Pathfinding Visualizer.
#
#   Build:   python -m PyInstaller MazePathfindingVisualizer.spec --noconfirm --clean
#   Output:  dist\MazePathfindingVisualizer.exe   (single file, no console window)
#
# The app draws everything on a Tkinter canvas, so there are no images or other
# data files to bundle. The same command runs in the build-exe job of
# .github/workflows/tests.yml, and a tag such as v1.1 publishes the result as a
# GitHub release.

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[],
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
    name='MazePathfindingVisualizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
