# -*- mode: python ; coding: utf-8 -*-
import os

a = Analysis(
    ['app.py'],
    pathex=[
        r'C:\Users\ThisPC\AppData\Roaming\Python\Python313\site-packages',
        r'C:\Python313\Lib\site-packages'
    ],
    binaries = [
        (r'C:\Users\ThisPC\AppData\Roaming\Python\Python313\site-packages\pyzbar\libiconv.dll', '.'),
        (r'C:\Users\ThisPC\AppData\Roaming\Python\Python313\site-packages\pyzbar\libzbar-64.dll', '.'),
        (r'C:\Users\ThisPC\AppData\Roaming\Python\Python313\site-packages\psycopg2\_psycopg.cp313-win_amd64.pyd', 'psycopg2'),
    ],
    datas=[('flask_server', 'flask_server'), ('forms', 'forms'), ('forms_img', 'forms_img'), ('icons', 'icons'), ('images', 'images'), ('.env', '.'), ('audit_log_viewer.py', '.'), ('audit_logger.py', '.'), ('auto_form.py', '.'), ('book_viewer.py', '.'), ('db_config.py', '.'), ('everify_form.py', '.'), ('everify_server.log', '.'), ('Login_Dialog.py', '.'), ('MainWindow.py', '.'), ('Manage_User_Widget.py', '.'), ('manage_users.py', '.'), ('pdfviewer.py', '.'), ('qr_scanner_window.py', '.'), ('releasing_docs.py', '.'), ('releasing_log_viewer.py', '.'), ('requirements.txt', '.'), ('Search_Birth_Window.py', '.'), ('Search_Death_Window.py', '.'), ('Search_Marriage_Window.py', '.'), ('search.py', '.'), ('stats.py', '.'), ('stylesheets.py', '.'), ('tagging_birth.py', '.'), ('tagging_death.py', '.'), ('tagging_main.py', '.'), ('tagging_marriage.py', '.'), ('verify.py', '.')],
    hiddenimports=['flask', 'requests', 'jwt', 'jwt.algorithms', 'opencv-python', 'pyzbar', 'numpy', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'sqlite3', 'matplotlib', 'matplotlib.backends.backend_qt5agg', 'reportlab', 'psycopg2', 'psycopg2._psycopg', 'psycopg2.extensions', 'psycopg2.extras', 'psycopg2.tz', 'psycopg2.pool', 'psycopg2.sql', 'psycopg2.types', 'psycopg2.errors', 'psycopg2.adapt'],
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
    [],
    exclude_binaries=True,
    name='OCCR RVS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icons\\RVS-icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='app',
)
