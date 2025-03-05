# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Собираем все необходимые данные и зависимости
fastapi_collect = collect_all("fastapi")
uvicorn_collect = collect_all("uvicorn")
sqlalchemy_collect = collect_all("sqlalchemy")
asyncpg_collect = collect_all("asyncpg")

a = Analysis(
    ['app/main.py'],  # Замените 'main.py' на имя вашего основного файла
    pathex=[],
    binaries=[],
    datas=[
        *fastapi_collect[0],
        *uvicorn_collect[0],
        *sqlalchemy_collect[0],
        *asyncpg_collect[0],
        ('app/api', 'app/api'),  # Включаем директорию api
        ('app/db', 'app/db'),    # Включаем директорию db
    ],
    hiddenimports=[
        *fastapi_collect[1],
        *uvicorn_collect[1],
        *sqlalchemy_collect[1],
        *asyncpg_collect[1],
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'asyncpg.pgproto.pgproto',
        'sqlalchemy.ext.asyncio',
        'sqlalchemy.ext.asyncio.engine',
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
    name='BLS Mark Server',  # Имя выходного файла
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Это обеспечивает отображение окна командной строки
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='ico/BLS-Server-Logo.ico'
)