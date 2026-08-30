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
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load .env so ONEDRIVE_BACKUP_DIR is available (dotenv optional)
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / '.env')
except ImportError:
    pass

DB_PATH        = PROJECT_ROOT / 'db.sqlite3'
DAILY_DIR      = PROJECT_ROOT / 'backups' / 'daily'
MONTHLY_DIR    = PROJECT_ROOT / 'backups' / 'monthly'
LOG_PATH       = PROJECT_ROOT / 'logs' / 'backup.log'

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

    # Use SQLite's backup API — safe while Django is running
    try:
        src = sqlite3.connect(str(DB_PATH))
        dst = sqlite3.connect(str(daily_path))
        src.backup(dst)
        dst.close()
        src.close()
    except Exception as exc:
        log(f'ERROR: Backup creation failed: {exc}')
        sys.exit(1)

    # Verify the backup can be opened and passes integrity check
    try:
        conn = sqlite3.connect(str(daily_path))
        result = conn.execute('PRAGMA integrity_check').fetchone()
        conn.close()
        if result[0] != 'ok':
            raise ValueError(f'integrity_check returned: {result[0]}')
        size_kb = daily_path.stat().st_size // 1024
        log(f'Backup created and verified: {daily_path.name}  ({size_kb} KB)')
    except Exception as exc:
        log(f'ERROR: Backup verification failed: {exc}')
        daily_path.unlink(missing_ok=True)
        sys.exit(1)

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


def _recent_backup_exists(hours: int = 20) -> bool:
    """Return True if a backup file exists that is newer than `hours` hours."""
    if not DAILY_DIR.exists():
        return False
    cutoff = datetime.now() - timedelta(hours=hours)
    return any(
        datetime.fromtimestamp(f.stat().st_mtime) > cutoff
        for f in DAILY_DIR.glob('db_*.sqlite3')
    )


if __name__ == '__main__':
    if '--if-needed' in sys.argv:
        if _recent_backup_exists(hours=20):
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  Recent backup found (<20 h). Skipping startup backup.")
            sys.exit(0)
    run_backup()
