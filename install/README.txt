==============================================================
  JALARAM CNC BILLING SYSTEM
  Complete Setup Guide — From Scratch to Running
==============================================================


══════════════════════════════════════════════════════════════
  PART A — FOR YOU (SENDER)
  What to prepare before sending the ZIP
══════════════════════════════════════════════════════════════

STEP A1: Download two tools into  install\tools\
─────────────────────────────────────────────────

  Open the file:  install\tools\DOWNLOAD_THESE.txt
  It has the exact download links and steps.

  You need:
    install\tools\uv.exe      (Python installer, ~10 MB)
    install\tools\nssm.exe    (Windows service manager, ~300 KB)

STEP A2: Create the deployment package
──────────────────────────────────────

  Double-click:  create_deployment.bat  (in the project root)

  This creates a clean  dist\JalaramCNC\  folder.
  Then:
    1. Put  uv.exe  and  nssm.exe  into  dist\JalaramCNC\install\tools\
    2. Right-click the JalaramCNC folder → Send to → Compressed folder
    3. You get:  JalaramCNC.zip  (~5 MB without tools, ~15 MB with tools)
    4. Send JalaramCNC.zip to your friend (WhatsApp, Google Drive, USB, etc.)


══════════════════════════════════════════════════════════════
  PART B — FOR YOUR FRIEND (RECEIVER)
  What to do on the laptop — takes about 10 minutes
══════════════════════════════════════════════════════════════

STEP B1: Unzip to the correct folder
─────────────────────────────────────

  Right-click JalaramCNC.zip → Extract All
  Extract to:  C:\

  After extraction the structure should be:

    C:\JalaramCNC\
    ├── manage.py
    ├── install\
    │   ├── install.bat       ← the one-click installer
    │   └── tools\
    │       ├── uv.exe
    │       └── nssm.exe
    ├── scripts\
    ├── core\
    └── ...

  IMPORTANT: The folder must be exactly  C:\JalaramCNC\
  NOT inside another folder like  C:\JalaramCNC\JalaramCNC\

STEP B2: Run the installer (ONE CLICK)
──────────────────────────────────────

  1. Open File Explorer → go to  C:\JalaramCNC\install\
  2. Right-click  install.bat
  3. Click  "Run as administrator"
  4. Click Yes if Windows asks for permission

  The installer will do everything automatically:
    ✓ Install Python 3.14  (downloads ~35 MB, needs internet)
    ✓ Install all app packages
    ✓ Set up the database
    ✓ Ask you to set a delete-protection password
    ✓ Install the auto-start Windows service
    ✓ Schedule daily backup at 10:00 PM
    ✓ Create "Jalaram CNC" shortcut on Desktop

  When asked to SET THE DELETE PASSWORD:
    Type a password you will remember (e.g. "jalaram@2024")
    Type it again to confirm
    WRITE IT DOWN somewhere safe

  Total time: about 5-10 minutes

STEP B3: Verify it works
──────────────────────────

  1. Double-click "Jalaram CNC" on the Desktop
     (or open browser → http://localhost:8000)
  2. You should see the Jalaram CNC dashboard

STEP B4: Test auto-start (important!)
────────────────────────────────────

  1. Restart the laptop
  2. After Windows loads (no need to do anything else),
     open browser → http://localhost:8000
  3. Dashboard should appear automatically
  4. If it does — installation is complete!


══════════════════════════════════════════════════════════════
  DAILY USAGE (for the friend)
══════════════════════════════════════════════════════════════

  Turn on laptop
       ↓
  App starts automatically (no action needed)
       ↓
  Double-click "Jalaram CNC" on Desktop
       ↓
  http://localhost:8000 opens
       ↓
  Use the billing system

  That's it. No command prompt. No terminal. No Python.


══════════════════════════════════════════════════════════════
  BACKUP — HOW IT WORKS
══════════════════════════════════════════════════════════════

  Automatic:
    Every night at 10:00 PM the laptop saves a backup
    (laptop must be ON — it can have the screen locked)

  Backup location:
    C:\JalaramCNC\backups\daily\      (last 30 daily)
    C:\JalaramCNC\backups\monthly\    (last 12 monthly)

  OneDrive:
    If OneDrive was signed in during installation,
    backups also go to:
      OneDrive\JalaramCNC_Backups\daily\
    OneDrive automatically syncs these to the cloud.

  Run backup manually anytime (open CMD in C:\JalaramCNC\):
    .venv\Scripts\python scripts\backup.py

  Restore from backup:
    .venv\Scripts\python scripts\restore.py


══════════════════════════════════════════════════════════════
  DATABASE PROTECTION
══════════════════════════════════════════════════════════════

  To delete the database (permanent, use with caution):
    .venv\Scripts\python scripts\delete_db.py
    → Enter the password you set during installation
    → An emergency backup is always saved first

  To change the delete password:
    .venv\Scripts\python scripts\set_db_password.py


══════════════════════════════════════════════════════════════
  MANAGING THE SERVICE
══════════════════════════════════════════════════════════════

  From Command Prompt (as Administrator):

    Start   :  net start  JalaramCNCService
    Stop    :  net stop   JalaramCNCService
    Status  :  sc query   JalaramCNCService

  Or: press Windows key → type "Services" → find JalaramCNCService


══════════════════════════════════════════════════════════════
  LOG FILES
══════════════════════════════════════════════════════════════

    C:\JalaramCNC\logs\app.log       Django application log
    C:\JalaramCNC\logs\error.log     Error log (check if app fails)
    C:\JalaramCNC\logs\backup.log    Backup history


══════════════════════════════════════════════════════════════
  SYSTEM HEALTH PAGE (in the app)
══════════════════════════════════════════════════════════════

  Open the app → sidebar → "System Health"
  Shows: database status, last backup time, disk space, OneDrive status


══════════════════════════════════════════════════════════════
  TROUBLESHOOTING
══════════════════════════════════════════════════════════════

  App not opening after restart?
    1. Check C:\JalaramCNC\logs\error.log
    2. Open CMD as admin → type: sc query JalaramCNCService
    3. If status is not RUNNING: net start JalaramCNCService

  Static files not loading (CSS looks broken)?
    CMD in C:\JalaramCNC\:
      .venv\Scripts\python manage.py collectstatic --noinput

  Need to uninstall?
    Right-click C:\JalaramCNC\install\uninstall.bat
    Run as administrator
    (Data and backups are NOT deleted)

==============================================================