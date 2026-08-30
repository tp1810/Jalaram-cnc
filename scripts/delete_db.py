#!/usr/bin/env python3
"""
Password-protected database delete utility.

The database cannot be deleted without the password set via set_db_password.py.
An emergency backup is always created before deletion.

Usage:
    python scripts/delete_db.py
"""
import getpass
import hashlib
import shutil
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH    = PROJECT_ROOT / 'db.sqlite3'
HASH_FILE  = SCRIPT_DIR / '.db_password_hash'
BACKUP_DIR = PROJECT_ROOT / 'backups'


def main() -> None:
    print('=' * 50)
    print('  JALARAM CNC — DATABASE DELETE')
    print('=' * 50)

    if not HASH_FILE.exists():
        print('\nNo delete password is set.')
        print('Run  python scripts/set_db_password.py  first.')
        sys.exit(1)

    if not DB_PATH.exists():
        print(f'\nDatabase does not exist at: {DB_PATH}')
        sys.exit(0)

    size_kb = DB_PATH.stat().st_size // 1024
    print(f'\nDatabase : {DB_PATH}')
    print(f'Size     : {size_kb} KB')
    print('\n  WARNING: This permanently deletes ALL customers,')
    print('           bills, and payment data.')
    print()

    password = getpass.getpass('Enter admin password to authorise deletion: ')
    stored   = HASH_FILE.read_text().strip()

    if hashlib.sha256(password.encode()).hexdigest() != stored:
        print('\nIncorrect password. Operation cancelled.')
        sys.exit(1)

    confirm = input('\nFinal confirmation — type  DELETE  to proceed: ').strip()
    if confirm != 'DELETE':
        print('Cancelled.')
        sys.exit(0)

    # Always save an emergency backup before deleting
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    emergency = BACKUP_DIR / f'pre_delete_{datetime.now().strftime("%Y-%m-%d_%H%M%S")}.sqlite3'
    shutil.copy2(DB_PATH, emergency)
    print(f'\nEmergency backup saved: {emergency.name}')

    DB_PATH.unlink()
    print('Database deleted.')
    print('\nTo start fresh:  python manage.py migrate')


if __name__ == '__main__':
    main()
