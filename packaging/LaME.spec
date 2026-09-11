# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for a distributable LaME build.

Build from the repository root, after the two gitignored build artifacts exist::

    (cd blockly && npm install && npx webpack)          # blockly/dist/bundle.js
    python -m sphinx -b html docs/source docs/build/html
    python packaging/make_icons.py
    pyinstaller packaging/LaME.spec

Produces a one-dir build in ``dist/`` -- ``dist/LaME.app`` on macOS, ``dist/LaME/`` on
Windows. One-dir is not optional: PyInstaller's PyQt6-WebEngine support (the
``QtWebEngineProcess`` helper, the ``.pak`` resources and ``icudtl.dat``) only works in
that layout, and LaME needs WebEngine for the workflow designer and the help browser.

Layout invariant: ``src/app/config.py`` derives BASEDIR from ``__file__``, which in a
one-dir build resolves to the bundle root. Everything it reaches for -- ``resources/``,
``blockly/``, ``docs/build/html/`` -- must therefore sit at the bundle root, which is
what the ``datas`` entries below arrange.
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).resolve().parent
PACKAGING = ROOT / 'packaging'

IS_MAC = sys.platform == 'darwin'
IS_WIN = sys.platform == 'win32'


def sibling_package(name):
    """Return the installed location of an editable sibling package."""
    import importlib

    return Path(importlib.import_module(name).__file__).resolve().parent


def importable_pathex(name):
    """Make an editable package findable by PyInstaller's static analysis.

    Three of the four siblings are installed editable via a plain ``.pth`` file, which
    PyInstaller reads. ``global_geochemistry`` instead uses setuptools' MetaPathFinder
    strategy (its package lives in a directory literally named ``src``, remapped at
    import time), and PyInstaller does not run that finder -- the module simply comes
    out missing.

    Stage a directory containing the package under its real name and return the
    directory to add to ``pathex``. A symlink is used where the platform allows it and
    a copy otherwise, so this behaves the same on Windows without developer mode.

    Parameters
    ----------
    name : str
        Importable package name.

    Returns
    -------
    str :
        Directory to append to ``pathex``.
    """
    import shutil

    package_dir = sibling_package(name)
    if package_dir.name == name:
        return str(package_dir.parent)

    stage = ROOT / 'build' / 'pathstub'
    stage.mkdir(parents=True, exist_ok=True)
    target = stage / name

    if target.is_symlink() or target.exists():
        if target.is_symlink():
            target.unlink()
        else:
            shutil.rmtree(target)
    try:
        target.symlink_to(package_dir, target_is_directory=True)
    except (OSError, NotImplementedError):
        shutil.copytree(package_dir, target)

    return str(stage)


def required(path):
    """Fail the build loudly if a build artifact is missing, rather than shipping without it."""
    path = Path(path)
    if not path.exists():
        raise SystemExit(
            f"packaging/LaME.spec: required input missing: {path}\n"
            "Build the blockly bundle and the docs before running PyInstaller "
            "(see the module docstring)."
        )
    return str(path)


# --- Data ------------------------------------------------------------------------
# (source, destination-relative-to-bundle-root)

datas = [
    (str(ROOT / 'resources'), 'resources'),
    (required(ROOT / 'blockly' / 'index.html'), 'blockly'),
    (required(ROOT / 'blockly' / 'dist'), 'blockly/dist'),
    (required(ROOT / 'docs' / 'build' / 'html'), 'docs/build/html'),
    (str(ROOT / 'lame_splash.png'), '.'),
    (str(ROOT / 'LaME-64.png'), '.'),
    (str(ROOT / 'user_preferences'), 'user_preferences'),
]

# lame_core owns ICONPATH and STYLE_PATH: src/app/config.py overrides BASEDIR and
# APPDATA_PATH but *not* those two, so they still resolve from lame_core's own
# __file__. Drop these and every icon and both stylesheets disappear at runtime.
datas += collect_data_files('lame_core')
datas += collect_data_files('blueberry')
datas += collect_data_files('global_geochemistry')

# siesta reads these at runtime but declares no package-data, so collect_data_files
# does not see them.
_siesta = sibling_package('siesta')
datas += [
    (str(_siesta / 'reSTStyle.yaml'), 'siesta'),
    (str(_siesta / 'booktabs.css'), 'siesta'),
]

# global_geochemistry reaches these through `parents[2]`, i.e. one level above its
# package directory -- outside the package, so they land at the bundle root.
_gg_root = sibling_package('global_geochemistry').parent
datas += [
    (str(_gg_root / 'ref_models'), 'ref_models'),
    (str(_gg_root / 'pacific_basin_robinson.csv'), '.'),
]

# Data-bearing third-party packages.
for _pkg in ('matplotlib', 'cmcrameri', 'pyproj'):
    datas += collect_data_files(_pkg)


# --- Imports ---------------------------------------------------------------------

hiddenimports = [
    # Imported bare, relying on the repo root being sys.path[0]; see src/app/SpotTools.py
    # and the generated designer/*_ui.py modules.
    'resources_rc',
    # Only ever imported transitively by pandas' .xlsx reads, so static analysis
    # misses it -- but earthref.xlsx / element_info.xlsx / georem.xlsx need it.
    'openpyxl',
]
# sklearn defers most submodule imports, and rst2pdf/docutils discover extensions
# through entry points; neither is visible to static analysis.
for _pkg in ('sklearn', 'rst2pdf', 'docutils'):
    hiddenimports += collect_submodules(_pkg)

excludes = [
    # A second Qt binding on the path breaks the frozen app at import time.
    'PyQt5', 'PySide2', 'PySide6',
    'tkinter', 'pytest', 'IPython', 'notebook', 'jupyter',
]


# --- Build -----------------------------------------------------------------------

a = Analysis(
    [str(ROOT / 'main.py')],
    pathex=[str(ROOT), importable_pathex('global_geochemistry')],
    binaries=[],
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
    name='LaME',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX corrupts Qt's dylibs and the WebEngine helper -- must stay off.
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PACKAGING / ('LaME.icns' if IS_MAC else 'LaME.ico')),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='LaME',
)

if IS_MAC:
    app = BUNDLE(
        coll,
        name='LaME.app',
        icon=str(PACKAGING / 'LaME.icns'),
        bundle_identifier='edu.adelaide.lame',
        info_plist={
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '11.0',
            'CFBundleName': 'LaME',
            'CFBundleDisplayName': 'Laser Map Explorer',
            'CFBundleShortVersionString': '0.1.0',
            'CFBundleVersion': '0.1.0',
        },
    )
