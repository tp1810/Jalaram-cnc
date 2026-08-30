#!/usr/bin/env python3
"""
Restore Jalaram CNC database from a backup.

Usage:
    python scripts/restore.py

Lists available backups, lets you choose one, verifies it,
saves the current database as a safety copy, then restores.
"""
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH      = PROJECT_ROOT / 'db.sqlite3'
DAILY_DIR    = PROJECT_ROOT / 'backups' / 'daily'
MONTHLY_DIR  = PROJECT_ROOT / 'backups' / 'monthly'
BACKUP_DIR   = PROJECT_ROOT / 'backups'


def list_backups() -> list:
    files = []
    for d in [DAILY_DIR, MONTHLY_DIR]:
        if d.exists():
            files.extend(sorted(d.glob('db_*.sqlite3'), reverse=True))
    return files


def main() -> None:
    print('=' * 55)
    print('  JALARAM CNC — DATABASE RESTORE')
    print('=' * 55)

    backups = list_backups()
    if not backups:
        print('\nNo backups found in backups/daily/ or backups/monthly/')
        sys.exit(1)

    show = backups[:25]
    print(f'\nAvailable backups ({len(backups)} total, showing latest 25):\n')
    for i, b in enumerate(show, 1):
        mtime = datetime.fromtimestamp(b.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
        size_kb = b.stat().st_size // 1024
        tag = 'monthly' if 'monthly' in str(b) else 'daily  '
        print(f'  {i:3d}. [{tag}]  {b.name:<45}  {mtime}  {size_kb} KB')

    print()
    raw = input('Enter backup number to restore (0 = cancel): ').strip()
    try:
        n = int(raw)
    except ValueError:
        print('Invalid input.')
        sys.exit(1)

    if n == 0:
        print('Cancelled.')
        sys.exit(0)

    if not (1 <= n <= len(show)):
        print('Invalid selection.')
        sys.exit(1)

    chosen = show[n - 1]
    print(f'\nSelected: {chosen}')

    # Verify backup integrity before touching the live database
    try:
        conn = sqlite3.connect(str(chosen))
        result = conn.execute('PRAGMA integrity_check').fetchone()
        conn.close()
        if result[0] != 'ok':
            print(f'ERROR: Backup integrity check failed: {result[0]}')
            sys.exit(1)
        print('Backup integrity: OK')
    except Exception as exc:
        print(f'ERROR: Cannot read backup: {exc}')
        sys.exit(1)

    confirm = input('\nWARNING: This will REPLACE the live database. Type YES to continue: ').strip()
    if confirm != 'YES':
        print('Cancelled.')
        sys.exit(0)

    # Save the current database as a safety copy
    if DB_PATH.exists():
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        safety = BACKUP_DIR / f'pre_restore_{datetime.now().strftime("%Y-%m-%d_%H%M%S")}.sqlite3'
        shutil.copy2(DB_PATH, safety)
        print(f'Current database saved to: {safety.name}')

    shutil.copy2(chosen, DB_PATH)
    print(f'\nDatabase restored from: {chosen.name}')
    print('Restart the JalaramCNCService (or the server) for changes to take effect.')


if __name__ == '__main__':
    main()
