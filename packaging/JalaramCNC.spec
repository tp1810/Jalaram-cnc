import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


project_root = Path(SPECPATH).parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jalaram_cnc.settings')

hidden_imports = (
    collect_submodules('core')
    + collect_submodules('django')
    + collect_submodules('jalaram_cnc')
    + collect_submodules('scripts')
    + collect_submodules('whitenoise')
)

analysis = Analysis(
    [str(project_root / 'app.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / 'templates'), 'templates'),
        (str(project_root / 'staticfiles'), 'staticfiles'),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['playwright', 'reportlab', 'weasyprint'],
    noarchive=False,
    optimize=1,
)

python_archive = PYZ(analysis.pure)

executable = EXE(
    python_archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name='JalaramCNC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

collection = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='JalaramCNC',
)