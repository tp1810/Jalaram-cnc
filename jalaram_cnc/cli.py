import argparse
import os
import secrets
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request
from contextlib import closing

from jalaram_cnc.runtime_paths import CONFIG_FILE, DATA_DIR, DB_PATH, LOG_DIR, ensure_data_dirs

APP_VERSION = '1.1.0'
BACKUP_INITIAL_DELAY_SECONDS = 10
BACKUP_CHECK_INTERVAL_SECONDS = 60 * 60


def find_onedrive_backup_dir():
    for variable in ('OneDriveCommercial', 'OneDriveConsumer', 'OneDrive'):
        value = os.environ.get(variable, '').strip()
        if value and os.path.isdir(value):
            return os.path.join(value, 'JalaramCNC_Backups')
    return None


def ensure_configuration() -> None:
    ensure_data_dirs()
    if CONFIG_FILE.exists():
        return
    lines = [
        'DEBUG=False',
        f'DJANGO_SECRET_KEY={secrets.token_urlsafe(48)}',
        'ALLOWED_HOSTS=127.0.0.1,localhost',
        'SERVER_HOST=127.0.0.1',
        'SERVER_PORT=8000',
    ]
    onedrive_backup_dir = find_onedrive_backup_dir()
    if onedrive_backup_dir:
        lines.append(f'ONEDRIVE_BACKUP_DIR={onedrive_backup_dir}')
    lines.append('')
    CONFIG_FILE.write_text(
        '\n'.join(lines),
        encoding='utf-8',
    )


def django_command(*arguments: str) -> None:
    ensure_configuration()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jalaram_cnc.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(['JalaramCNC', *arguments])


def doctor() -> int:
    ensure_configuration()
    print(f'Jalaram CNC {APP_VERSION}')
    print(f'Data directory: {DATA_DIR}')
    print(f'Log directory:  {LOG_DIR}')
    print(f'Database:       {DB_PATH}')
    if not DB_PATH.exists():
        print('Database status: MISSING')
        return 1
    try:
        with closing(sqlite3.connect(str(DB_PATH))) as connection:
            result = connection.execute('PRAGMA integrity_check').fetchone()
        print(f'Database status: {result[0] if result else "unknown"}')
    except sqlite3.Error as exc:
        print(f'Database status: ERROR ({exc})')
        return 1
    django_command('check')
    from scripts.backup import recent_valid_backup_exists
    print(f'Recent backup:  {"OK" if recent_valid_backup_exists(24) else "OLDER THAN 24 HOURS OR MISSING"}')
    return 0


def backup_if_needed() -> bool:
    if not DB_PATH.exists():
        return False
    from scripts.backup import recent_valid_backup_exists, run_backup
    if recent_valid_backup_exists(24):
        return False
    run_backup()
    return True


def backup_worker(
    initial_delay: int = BACKUP_INITIAL_DELAY_SECONDS,
    check_interval: int = BACKUP_CHECK_INTERVAL_SECONDS,
) -> None:
    stop_event = threading.Event()
    if stop_event.wait(initial_delay):
        return
    while True:
        try:
            backup_if_needed()
        except Exception as exc:
            print(f'[Jalaram CNC] Automatic backup failed: {exc}', flush=True)
        if stop_event.wait(check_interval):
            return


def start_backup_worker() -> threading.Thread:
    worker = threading.Thread(
        target=backup_worker,
        name='JalaramCNCBackup',
        daemon=True,
    )
    worker.start()
    return worker


def serve() -> None:
    ensure_configuration()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jalaram_cnc.settings')
    start_backup_worker()
    from scripts.start_server import run_server
    run_server()


def wait_until_ready(timeout_seconds: int = 30) -> int:
    ensure_configuration()
    host = os.environ.get('SERVER_HOST', '127.0.0.1')
    port = os.environ.get('SERVER_PORT', '8000')
    deadline = time.monotonic() + timeout_seconds
    url = f'http://{host}:{port}/'
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    print(f'Jalaram CNC is ready at {url}')
                    return 0
        except (OSError, urllib.error.URLError):
            time.sleep(0.25)
    print(f'Jalaram CNC did not become ready within {timeout_seconds} seconds.')
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(prog='JalaramCNC')
    parser.add_argument(
        'command',
        nargs='?',
        default='serve',
        choices=('serve', 'init', 'migrate', 'check', 'doctor', 'backup', 'restore', 'set-db-password', 'delete-db', 'wait-ready', 'version'),
    )
    args = parser.parse_args()

    if args.command == 'serve':
        serve()
    elif args.command == 'init':
        django_command('migrate', '--noinput')
    elif args.command in ('migrate', 'check'):
        django_command(args.command)
    elif args.command == 'doctor':
        return doctor()
    elif args.command == 'backup':
        ensure_configuration()
        from scripts.backup import run_backup
        run_backup()
    elif args.command == 'restore':
        from scripts.restore import main as restore_main
        restore_main()
    elif args.command == 'set-db-password':
        from scripts.set_db_password import main as set_password_main
        set_password_main()
    elif args.command == 'delete-db':
        from scripts.delete_db import main as delete_main
        delete_main()
    elif args.command == 'wait-ready':
        return wait_until_ready()
    elif args.command == 'version':
        print(APP_VERSION)
    return 0