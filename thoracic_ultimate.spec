# -*- mode: python ; coding: utf-8 -*-
# Ultimate spec file - includes all source files as data

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('ui', 'ui'),
        ('db', 'db'),
        ('utils', 'utils'),
        ('staging', 'staging'),
        ('export', 'export'),
    ],
    hiddenimports=[
        'ui.patient_tab',
        'ui.surgery_tab',
        'ui.path_tab',
        'ui.mol_tab',
        'ui.fu_tab',
        'ui.export_tab',
        'db.models',
        'db.migrate',
        'utils.validators',
        'staging.lookup',
        'export.excel',
        'export.csv',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'sqlite3',
        'openpyxl',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='thoracic_entry',
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
    icon=['assets/app.ico'],
)

