#!/usr/bin/env python3
"""
Daily backup script for Jalaram CNC.
Scheduled via Windows Task Scheduler — runs every night at 10:00 PM.

Usage:
    python scripts/backup.py

Creates:
    backups/daily/db_YYYY-MM-DD_HHMMSS.sqlite3  (kept 30 days, local)
    backups/monthly/db_YYYY-MM.sqlite3           (kept 12 months, local)
    <OneDrive>/JalaramCNC_Backups/daily/...      (if ONEDRIVE_BACKUP_DIR set in .env)
    logs/backup.log
"""
import os
import shutil
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from jalaram_cnc.runtime_paths import (
    CONFIG_FILE,
    DAILY_BACKUP_DIR,
    DB_PATH,
    LOG_DIR,
    MONTHLY_BACKUP_DIR,
    ensure_data_dirs,
)

try:
    from dotenv import load_dotenv
    load_dotenv(CONFIG_FILE)
except ImportError:
    pass

DAILY_DIR = DAILY_BACKUP_DIR
MONTHLY_DIR = MONTHLY_BACKUP_DIR
LOG_PATH = LOG_DIR / 'backup.log'

KEEP_DAILY   = 30
KEEP_MONTHLY = 12

# OneDrive mirror destination (set by install.bat, stored in .env)
_OD_ROOT = os.environ.get('ONEDRIVE_BACKUP_DIR', '').strip()
OD_DAILY_DIR   = Path(_OD_ROOT) / 'daily'   if _OD_ROOT else None
OD_MONTHLY_DIR = Path(_OD_ROOT) / 'monthly' if _OD_ROOT else None


def log(msg: str) -> None:
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def run_backup() -> None:
    ensure_data_dirs()
    log('=' * 55)
    log('Backup started')

    if not DB_PATH.exists():
        log(f'ERROR: Database not found at {DB_PATH}')
        sys.exit(1)

    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    MONTHLY_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    stamp = now.strftime('%Y-%m-%d_%H%M%S')
    daily_path = DAILY_DIR / f'db_{stamp}.sqlite3'
    temporary_path = DAILY_DIR / f'.db_{stamp}.tmp'

    try:
        with closing(sqlite3.connect(str(DB_PATH))) as source:
            with closing(sqlite3.connect(str(temporary_path))) as destination:
                source.backup(destination)
    except Exception as exc:
        temporary_path.unlink(missing_ok=True)
        log(f'ERROR: Backup creation failed: {exc}')
        raise RuntimeError('Backup creation failed') from exc

    try:
        with closing(sqlite3.connect(str(temporary_path))) as connection:
            result = connection.execute('PRAGMA integrity_check').fetchone()
        if result[0] != 'ok':
            raise ValueError(f'integrity_check returned: {result[0]}')
        temporary_path.replace(daily_path)
        size_kb = daily_path.stat().st_size // 1024
        log(f'Backup created and verified: {daily_path.name}  ({size_kb} KB)')
    except Exception as exc:
        temporary_path.unlink(missing_ok=True)
        log(f'ERROR: Backup verification failed: {exc}')
        raise RuntimeError('Backup verification failed') from exc

    # Monthly backup on the 1st of every month
    if now.day == 1:
        monthly_path = MONTHLY_DIR / f'db_{now.strftime("%Y-%m")}.sqlite3'
        shutil.copy2(daily_path, monthly_path)
        log(f'Monthly backup saved: {monthly_path.name}')
        if OD_MONTHLY_DIR:
            try:
                OD_MONTHLY_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy2(daily_path, OD_MONTHLY_DIR / monthly_path.name)
                log(f'OneDrive monthly mirror: {monthly_path.name}')
            except Exception as exc:
                log(f'WARN: OneDrive monthly mirror failed: {exc}')

    # Mirror daily backup to OneDrive (OneDrive client syncs it to cloud)
    if OD_DAILY_DIR:
        try:
            OD_DAILY_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(daily_path, OD_DAILY_DIR / daily_path.name)
            log(f'OneDrive daily mirror: {daily_path.name}')
        except Exception as exc:
            log(f'WARN: OneDrive daily mirror failed: {exc}')

    # Remove daily backups older than KEEP_DAILY days
    cutoff = now - timedelta(days=KEEP_DAILY)
    removed = 0
    for old in sorted(DAILY_DIR.glob('db_*.sqlite3')):
        try:
            mtime = datetime.fromtimestamp(old.stat().st_mtime)
            if mtime < cutoff:
                old.unlink()
                removed += 1
        except Exception:
            pass
    if removed:
        log(f'Removed {removed} old daily backup(s) (>{KEEP_DAILY} days)')

    # Remove monthly backups beyond KEEP_MONTHLY
    monthly_files = sorted(MONTHLY_DIR.glob('db_*.sqlite3'))
    while len(monthly_files) > KEEP_MONTHLY:
        monthly_files[0].unlink()
        log(f'Removed old monthly backup: {monthly_files[0].name}')
        monthly_files = monthly_files[1:]

    log('Backup completed successfully')
    log('=' * 55)


def recent_valid_backup_exists(hours: int = 24) -> bool:
    if not DAILY_DIR.exists():
        return False
    cutoff = datetime.now() - timedelta(hours=hours)
    for backup_file in sorted(DAILY_DIR.glob('db_*.sqlite3'), reverse=True):
        if datetime.fromtimestamp(backup_file.stat().st_mtime) <= cutoff:
            continue
        try:
            with closing(sqlite3.connect(str(backup_file))) as connection:
                result = connection.execute('PRAGMA quick_check').fetchone()
            if result and result[0] == 'ok':
                return True
        except sqlite3.Error:
            continue
    return False


if __name__ == '__main__':
    if '--if-needed' in sys.argv:
        if recent_valid_backup_exists(hours=24):
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  Recent valid backup found (<24 h). Skipping startup backup.")
            sys.exit(0)
    run_backup()
