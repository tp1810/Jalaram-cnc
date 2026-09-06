"""
Jalaram CNC — Full Setup Script
Run this with the system Python 3.14 (no venv needed to start):

  1. Open Command Prompt AS ADMINISTRATOR
  2. cd C:\\JalaramCNC
  3. python install\\setup.py
"""
import os
import subprocess
import sys
import winreg
from pathlib import Path

ROOT        = Path(__file__).resolve().parent.parent  # C:\JalaramCNC
VENV        = ROOT / '.venv'
PY          = VENV / 'Scripts' / 'python.exe'
NSSM        = ROOT / 'install' / 'tools' / 'nssm.exe'
LOGS        = ROOT / 'logs'
SERVICE     = 'JalaramCNCService'


def banner(text):
    print(f'\n  {text}')
    print('  ' + '-' * (len(text) + 2))


def run(cmd, check=True, **kw):
    r = subprocess.run(cmd, **kw)
    if check and r.returncode != 0:
        print(f'\n  [ERROR] Command failed: {cmd}')
        input('\n  Press Enter to exit...')
        sys.exit(1)
    return r


print()
print('  ============================================================')
print('    JALARAM CNC  |  Setup Script')
print('  ============================================================')

# ── 1. Admin check ──────────────────────────────────────────────
try:
    import ctypes
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print('\n  [ERROR] Must be run as Administrator.')
        print('  Open CMD → right-click → Run as administrator')
        input('\n  Press Enter to exit...')
        sys.exit(1)
except Exception:
    pass  # skip on non-Windows

os.chdir(ROOT)

# ── 2. Create venv ──────────────────────────────────────────────
banner('Step 1/8  Creating virtual environment')
if PY.exists():
    print('  Already exists — skipping.')
else:
    run([sys.executable, '-m', 'venv', str(VENV)])
    print('  Done.')

# ── 3. Install packages ─────────────────────────────────────────
banner('Step 2/8  Installing packages (needs internet)')
run([str(PY), '-m', 'pip', 'install', '--upgrade', 'pip', '-q',
     '--no-warn-script-location'])
run([str(PY), '-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt'),
     '-q', '--no-warn-script-location'])
print('  All packages installed.')

# ── 4. Create folders ───────────────────────────────────────────
banner('Step 3/8  Creating folders')
for d in [LOGS, ROOT / 'backups' / 'daily', ROOT / 'backups' / 'monthly']:
    d.mkdir(parents=True, exist_ok=True)
print('  Done.')

# ── 5. Create .env ──────────────────────────────────────────────
banner('Step 4/8  Creating configuration (.env)')
if (ROOT / '.env').exists():
    print('  .env already exists — keeping current settings.')
else:
    sk_result = run([str(PY), '-c',
        'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'],
        capture_output=True, text=True)
    sk = sk_result.stdout.strip()

    od_dir = ''
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r'SOFTWARE\Microsoft\OneDrive')
        od_dir, _ = winreg.QueryValueEx(key, 'UserFolder')
        winreg.CloseKey(key)
    except Exception:
        pass

    lines = [
        'DEBUG=False',
        f'DJANGO_SECRET_KEY={sk}',
        'ALLOWED_HOSTS=127.0.0.1,localhost',
        'SERVER_HOST=127.0.0.1',
        'SERVER_PORT=8000',
    ]
    if od_dir:
        lines.append(f'ONEDRIVE_BACKUP_DIR={od_dir}\\JalaramCNC_Backups')
        print(f'  OneDrive found: {od_dir}')
    else:
        print('  OneDrive not found — local backup only.')

    (ROOT / '.env').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('  .env created with secure secret key.')

# ── 6. Django migrate + collectstatic ───────────────────────────
banner('Step 5/8  Setting up database and static files')
run([str(PY), 'manage.py', 'migrate', '--noinput'])
run([str(PY), 'manage.py', 'collectstatic', '--noinput', '--clear'],
    capture_output=True)
print('  Done.')

# ── 7. Database delete password ─────────────────────────────────
banner('Step 6/8  Set database delete password')
print('  WRITE THIS PASSWORD DOWN. You need it to delete the database.\n')
subprocess.run([str(PY), str(ROOT / 'scripts' / 'set_db_password.py')])

# ── 8. NSSM Windows service ─────────────────────────────────────
banner('Step 7/8  Installing Windows auto-start service')
if not NSSM.exists():
    print(f'  [SKIP] nssm.exe not found at: {NSSM}')
    print('  Download from https://nssm.cc/download')
    print('  Then run this script again.')
else:
    subprocess.run([str(NSSM), 'stop',   SERVICE], capture_output=True)
    subprocess.run([str(NSSM), 'remove', SERVICE, 'confirm'], capture_output=True)

    nssm_cmds = [
        [str(NSSM), 'install', SERVICE, str(PY)],
        [str(NSSM), 'set', SERVICE, 'AppParameters',   str(ROOT / 'scripts' / 'start_server.py')],
        [str(NSSM), 'set', SERVICE, 'AppDirectory',    str(ROOT)],
        [str(NSSM), 'set', SERVICE, 'Description',     'Jalaram CNC Billing System'],
        [str(NSSM), 'set', SERVICE, 'Start',           'SERVICE_AUTO_START'],
        [str(NSSM), 'set', SERVICE, 'AppStdout',       str(LOGS / 'app.log')],
        [str(NSSM), 'set', SERVICE, 'AppStderr',       str(LOGS / 'error.log')],
        [str(NSSM), 'set', SERVICE, 'AppRotateFiles',  '1'],
        [str(NSSM), 'set', SERVICE, 'AppRotateBytes',  '10485760'],
        [str(NSSM), 'set', SERVICE, 'AppExit Default', 'Restart'],
        [str(NSSM), 'set', SERVICE, 'AppRestartDelay', '5000'],
    ]
    for cmd in nssm_cmds:
        subprocess.run(cmd, capture_output=True)

    result = subprocess.run([str(NSSM), 'start', SERVICE], capture_output=True)
    import time; time.sleep(4)

    sc = subprocess.run(['sc', 'query', SERVICE], capture_output=True, text=True)
    if 'RUNNING' in sc.stdout:
        print('  Service installed and RUNNING.')
    else:
        print('  Service installed. May take a moment to start.')
        print(f'  Check: {LOGS}\\error.log if app does not open.')

# ── 9. Task Scheduler (backup) ──────────────────────────────────
banner('Step 8/8  Scheduling backup tasks')
py_s  = str(PY)
bak_s = str(ROOT / 'scripts' / 'backup.py')
subprocess.run(['schtasks', '/delete', '/tn', 'JalaramCNC_DailyBackup',   '/f'], capture_output=True)
subprocess.run(['schtasks', '/delete', '/tn', 'JalaramCNC_StartupBackup', '/f'], capture_output=True)
subprocess.run([
    'schtasks', '/create', '/tn', 'JalaramCNC_DailyBackup',
    '/tr', f'"{py_s}" "{bak_s}"',
    '/sc', 'daily', '/st', '22:00', '/ru', 'SYSTEM', '/rl', 'HIGHEST', '/f'
], capture_output=True)
subprocess.run([
    'schtasks', '/create', '/tn', 'JalaramCNC_StartupBackup',
    '/tr', f'"{py_s}" "{bak_s}" --if-needed',
    '/sc', 'onstart', '/delay', '0002:00', '/ru', 'SYSTEM', '/rl', 'HIGHEST', '/f'
], capture_output=True)
print('  Daily backup: 10:00 PM')
print('  Startup backup: on boot if last backup was >20 hours ago')

# ── 10. Desktop shortcut ────────────────────────────────────────
public_desktop = Path(os.environ.get('PUBLIC', 'C:\\Users\\Public')) / 'Desktop'
shortcut = public_desktop / 'Jalaram CNC.url'
shortcut.write_text('[InternetShortcut]\nURL=http://localhost:8000\n', encoding='utf-8')
print(f'\n  Desktop shortcut created.')

# ── Done ────────────────────────────────────────────────────────
print()
print('  ============================================================')
print('    SETUP COMPLETE!')
print('  ============================================================')
print()
print('   Open app : http://localhost:8000')
print('   Shortcut : "Jalaram CNC" on Desktop')
print()
print('   NEXT: Restart the laptop to confirm the app')
print('   starts automatically without doing anything.')
print()
input('  Press Enter to exit...')
