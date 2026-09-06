import os
import sys
from pathlib import Path


SOURCE_DIR = Path(__file__).resolve().parent.parent
IS_FROZEN = bool(getattr(sys, 'frozen', False))
APP_DIR = Path(getattr(sys, '_MEIPASS', SOURCE_DIR)).resolve() if IS_FROZEN else SOURCE_DIR

if os.environ.get('JALARAM_CNC_DATA_DIR'):
    DATA_DIR = Path(os.environ['JALARAM_CNC_DATA_DIR']).expanduser().resolve()
elif IS_FROZEN and os.name == 'nt':
    DATA_DIR = Path(os.environ.get('PROGRAMDATA', r'C:\ProgramData')) / 'JalaramCNC'
else:
    DATA_DIR = SOURCE_DIR

CONFIG_FILE = DATA_DIR / ('configuration.env' if IS_FROZEN else '.env')
DB_PATH = DATA_DIR / 'db.sqlite3'
LOG_DIR = DATA_DIR / 'logs'
BACKUP_DIR = DATA_DIR / 'backups'
DAILY_BACKUP_DIR = BACKUP_DIR / 'daily'
MONTHLY_BACKUP_DIR = BACKUP_DIR / 'monthly'
MEDIA_DIR = DATA_DIR / 'media'
TEMPLATE_DIR = APP_DIR / 'templates'
STATIC_SOURCE_DIR = APP_DIR / 'static'
STATIC_ROOT = APP_DIR / 'staticfiles'


def ensure_data_dirs() -> None:
    for directory in (
        DATA_DIR,
        LOG_DIR,
        DAILY_BACKUP_DIR,
        MONTHLY_BACKUP_DIR,
        MEDIA_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)