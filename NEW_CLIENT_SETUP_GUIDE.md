# New Client Setup Guide (Rebrand + Build + Deliver)

How to give this same billing software to another business, with that business's
name, logo, address, bank details, and QR code, and send them their own
`Setup.exe`.

Throughout this guide the new business is written as:

| Placeholder | Meaning | Example |
|---|---|---|
| `<New Name>` | Display name (spaces allowed) | `Shree CNC` |
| `<NewShort>` | Short technical name: letters and digits only, **no spaces** | `ShreeCNC` |

Replace these with the real names every time you see them.

---

## 0. What changes and what stays the same

**Changes (per client):**
- Logo and payment QR image
- Business name in the sidebar, browser tab titles, and the invoice
- Address, phone numbers, bank details, and disclaimer on the invoice
- Installer name, install folder, Windows service name, data folder, and desktop shortcut

**Stays the same (do NOT rename):**
- The Python package folder `jalaram_cnc\` and anything spelled `jalaram_cnc` or
  `JALARAM_CNC_DATA_DIR`. They are internal only; the friend never sees them, and
  renaming them breaks imports.
- The `core\` app, database models, migrations, and all features.
- Port `8000`. Each friend runs the app on their own laptop, so they don't conflict.
  (Change the port only if two clients' apps ever run on the same PC.)

The result on the new friend's laptop:

```text
C:\Program Files\<New Name>\<NewShort>.exe          <- application
C:\ProgramData\<NewShort>\db.sqlite3                <- their data + backups + logs
Windows service: <NewShort>Service
Desktop shortcut: "<New Name>"
```

---

## 1. Make a separate copy of the project

> ⚠️ **Do not copy the folder with File Explorer.** The working folder contains
> Jalaram's real data: `db.sqlite3`, `.env`, `logs\`, `backups\`, `media\`,
> `build\`, `dist\`, `staticfiles\`. If you copy it, the new friend could receive
> Jalaram's customers and bills.

Use `git clone` instead. It copies only the committed source code, not the private data.

```powershell
cd "C:\Users\tarang.patel\Desktop\Tarang\Backup\Tarang Backup\Tp_personal\Nexa_projects"
git clone "Jalaram CNC" "<New Name>"
cd "<New Name>"
```

Commit or push any unfinished Jalaram work first, because only committed code is cloned.

**Optional (recommended): give it its own GitHub repo.** Create an empty private repo
on GitHub (for example `ShreeCNC`), then:

```powershell
git remote rename origin jalaram          # keeps a link to the original for future fixes
git remote add origin https://github.com/tp1810/<NewShort>.git
git push -u origin master
```

From here on, **every step happens inside the new `<New Name>` folder.**

---

## 2. Collect the details from the new friend

- [ ] Business name as it should appear in the sidebar (for example `Shree CNC` + subtitle `Laser Cutting`)
- [ ] Business name as it should appear on the invoice header (for example `SHREE CNC & LASER CUTTING`)
- [ ] Full address with pincode
- [ ] Phone number(s)
- [ ] Bank name, branch, account number, IFSC
- [ ] Logo image (square works best; JPG or PNG)
- [ ] Payment QR code image (their UPI QR)
- [ ] Invoice disclaimer line (currently: "We will not be responsible for any material after leaving the office.")
- [ ] Default item description when left empty (currently: `CNC Product`)

---

## 3. Replace the logo and QR code

Overwrite these two files with the friend's images, **keeping the exact same file names**:

```text
static\images\logo.jpeg
static\images\qr_code.jpeg
```

If their image is a `.png`, either convert it to `.jpeg` (open it in Paint and use
**Save as > JPEG**) or keep it as `.png` and update every `logo.jpeg` / `qr_code.jpeg`
reference in `templates\base.html` and `templates\bills\detail.html`.

---

## 4. Rename the app, installer, service, and data folder (script)

This renames everything the friend sees on Windows (installer, program folder,
service, shortcut, ProgramData folder, browser titles) in one pass. Open
**PowerShell in the new project folder**, set the two names on the first lines, and run:

```powershell
# ---- EDIT THESE TWO LINES ----
$NewName  = 'Shree CNC'     # display name, spaces allowed
$NewShort = 'ShreeCNC'      # letters/digits only, NO spaces
# ------------------------------

$OldName = 'Jalaram CNC'; $OldShort = 'JalaramCNC'

# 1) Rename the packaging files
git mv packaging\JalaramCNC.spec        "packaging\$NewShort.spec"
git mv packaging\JalaramCNCService.xml  "packaging\${NewShort}Service.xml"

# 2) Replace names inside files (case-sensitive, so 'jalaram_cnc' is NOT touched)
$files = @(
    'packaging\installer.iss',
    "packaging\$NewShort.spec",
    "packaging\${NewShort}Service.xml",
    'build_installer.ps1',
    'create_deployment.bat',
    'jalaram_cnc\runtime_paths.py',
    'jalaram_cnc\cli.py',
    'core\apps.py',
    'core\context_processors.py',
    'pyproject.toml'
) + (Get-ChildItem templates -Recurse -Filter *.html | ForEach-Object { $_.FullName })

foreach ($f in $files) {
    $path = (Resolve-Path $f).Path
    $text = [IO.File]::ReadAllText($path)
    $text = $text -creplace [regex]::Escape($OldShort), $NewShort
    $text = $text -creplace [regex]::Escape($OldName),  $NewName
    [IO.File]::WriteAllText($path, $text)   # writes UTF-8 without BOM
}

# 3) Give the installer its own unique ID (VERY IMPORTANT, see below)
$guid = [guid]::NewGuid().ToString().ToUpper()
$iss  = (Resolve-Path 'packaging\installer.iss').Path
$text = [IO.File]::ReadAllText($iss) -replace 'B0C97A31-49E9-4F38-9377-31969E8D0F0E', $guid
[IO.File]::WriteAllText($iss, $text)
Write-Host "New AppId: $guid  (write this down; never change it again for this client)"
```

### What the script changed, and why

| File | What changes |
|---|---|
| `packaging\installer.iss` | App name, publisher, `C:\Program Files\<New Name>`, `C:\ProgramData\<NewShort>`, shortcut names, service name, output file `<NewShort>-Setup.exe`, **new AppId** |
| `packaging\<NewShort>Service.xml` | Windows service id, name, description, exe name, log folder |
| `packaging\<NewShort>.spec` | PyInstaller exe/folder name (`<NewShort>.exe`) |
| `build_installer.ps1` | Uses the renamed spec/xml, prints the new installer path |
| `jalaram_cnc\runtime_paths.py` | Data folder: `C:\ProgramData\<NewShort>` |
| `jalaram_cnc\cli.py` | Console messages, OneDrive backup folder `<NewShort>_Backups` |
| `core\apps.py`, `core\context_processors.py` | Admin name / business name |
| `templates\**\*.html` | Browser tab titles (`Dashboard — <New Name>`), logo alt text, System Health service commands |

**Why the new AppId matters:** the AppId is how Windows recognizes "the same program".
If two clients' installers share an AppId, one installer would treat the other as an
**upgrade** and overwrite it. Each client needs its own AppId, created once and never changed.
Later updates for this client must keep the same AppId so they upgrade in place and keep the data.

### One manual fix in `packaging\installer.iss`

Delete this line in the `[Files]` section. It only existed to import Jalaram's old
database from their pre-installer setup, and a new client doesn't need it:

```text
Source: "C:\<NewShort>\db.sqlite3"; DestDir: ... onlyifdoesntexist uninsneveruninstall
```

Also check that the `MyAppPublisher` line at the top is correct, for example:

```text
#define MyAppPublisher "Shree CNC Laser Cutting"
```

---

## 5. Update the business details (manual edits)

The script handled names. The remaining edits are the business's own details.

### 5a. Sidebar and default browser title — `templates\base.html`

| Line (approx.) | Change |
|---|---|
| 7 | `<title>{% block title %}<New Name> ...{% endblock %}</title>` |
| 25 | `<span class="brand-main">Shree CNC</span>` (main name) |
| 26 | `<span class="brand-sub">Laser Cutting</span>` (subtitle; use `&amp;` for `&`) |

### 5b. Business name — `core\context_processors.py`

```python
'business_name': 'Shree CNC Laser Cutting',
```

### 5c. The invoice (bill) — `templates\bills\detail.html`

**This is the only invoice template the app uses.** The screen view, **Download PDF**,
**Share**, and **Print** buttons, and the PDF buttons on the Bills and Customer pages all
render this file.

| Line (approx.) | What | Current value |
|---|---|---|
| 164 | Invoice company name | `JALARAM CNC &amp; LASER CUTTING` |
| 165 | Address | `02, Samarth Square Complex, Modasa Road<br>Kapadwanj &ndash; 387620` |
| 166 | Phone numbers | `+91 75738 55710 ... +91 63513 25475` |
| 205 | Default item description | `default:"CNC Product"` |
| 251 | Disclaimer | `We will not be responsible for any material...` |
| 260 | Bank name | `State Bank of India` |
| 264 | Branch | `Kapadwanj` |
| 268 | Account number | `36474515254` |
| 272 | IFSC | `SBIN0000287` |

Tips:
- In HTML, write `&` as `&amp;`. Use `<br>` for a line break in the address.
- If the friend has only one phone number, delete the `&nbsp;&bull;&nbsp; ...` part.
- If they don't want bank details or a QR code, you can delete the `inv-bank-details`
  or `inv-qr-section` block.

### 5d. Files you can ignore

These still contain Jalaram details, but **no screen uses them** (leftovers from older PDF
methods). They do not affect the friend's app. Update them only if you want the repo clean:

```text
templates\bills\invoice.html
templates\bills\print.html
templates\bills\pdf_template.html
core\bill_generator.py
install\*   (old pre-installer setup scripts; not used by the new EXE installer)
setup.bat, static\css\style.css (comment only)
```

### 5e. Check for anything missed

```powershell
git grep -n -i -E "jalaram cnc|jalaramcnc|samarth|kapadwanj|modasa|7573855710|6351325475|36474515254|SBIN0000287|art & craft|art &amp; craft" -- templates core\context_processors.py packaging build_installer.ps1 jalaram_cnc\cli.py jalaram_cnc\runtime_paths.py
```

Anything this prints (apart from test data in `core\tests.py`) still needs changing.
`jalaram_cnc` (with an underscore) is expected and must stay.

### 5f. Optional: version number

For a new client you can start at `1.0.0`. Keep these four in sync:

- `jalaram_cnc\cli.py` → `APP_VERSION`
- `pyproject.toml` → `version`
- `packaging\installer.iss` → default `MyAppVersion`
- `build_installer.ps1` → default `$Version`

Then run `uv lock` so `uv.lock` matches.

---

## 6. Test it on your laptop before building

```powershell
uv venv --python 3.14
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 8001
```

Port `8001` is used here in case the installed Jalaram app is already using `8000` on your laptop.

Open http://127.0.0.1:8001 and check:

- [ ] Sidebar shows the new logo and name
- [ ] Browser tab title shows the new name
- [ ] Add a test customer and a test bill
- [ ] The bill page shows the new name, address, phones, bank details, and QR
- [ ] **Download PDF** looks correct (logo not stretched, text fits)
- [ ] **Print** preview looks correct on A4

Stop the server with `Ctrl+C`. The test data sits in this folder's `db.sqlite3`, which is
**never** packed into the installer, so the friend starts with an empty database. You can
delete `db.sqlite3` if you like.

---

## 7. Commit the changes

```powershell
git add -A
git commit -m "Rebrand for <New Name>"
git push
```

Committing first means you can rebuild the exact same installer later.

---

## 8. Build the installer EXE

Double-click **`build_installer.bat`** in the new folder, or run:

```powershell
.\build_installer.ps1 -Version 1.0.0
```

The build script:
1. Installs the dependencies into `.venv`
2. Runs Django checks, the migration check, and all tests (the build stops if any fail)
3. Collects static files (this is where the new logo/QR get packed)
4. Downloads WinSW (the service wrapper) if needed
5. Builds `<NewShort>.exe` with PyInstaller
6. Installs Inno Setup automatically via `winget` if it isn't installed yet
7. Compiles the installer

The build creates this file:

```text
packaging\output\<NewShort>-Setup.exe
```

**This single file is all you send.** Do not send `dist\`, `build\`, source code, `.env`,
or the database.

Optionally, record a checksum so you can confirm the file arrived intact:

```powershell
Get-FileHash packaging\output\<NewShort>-Setup.exe -Algorithm SHA256
```

---

## 9. Send it and install on the friend's laptop

**Sending:** Google Drive link, a USB stick, or WhatsApp **as a Document** (not as media).
Some email services block `.exe` files; if so, zip it first.

**On the friend's laptop (Windows 10/11, 64-bit):**
1. Double-click `<NewShort>-Setup.exe`.
2. If a blue **"Windows protected your PC"** screen appears, click **More info → Run anyway**.
   This happens because the installer is not code-signed, and is expected.
3. Click **Yes** on the admin (UAC) prompt, then **Install**.
4. The installer sets up the data folder, database, backups, and the auto-starting Windows
   service, then checks that the app responds.
5. At the end, tick **Open <New Name>**, or later double-click the **<New Name>** desktop icon.
6. The app opens at `http://127.0.0.1:8000`. No internet, Python, or setup is needed.

**After installation (recommended):** set the database-delete password. Open
**Command Prompt as Administrator** and run:

```cmd
"C:\Program Files\<New Name>\<NewShort>.exe" set-db-password
```

**Quick checks on their laptop:**
- [ ] Desktop icon opens the app
- [ ] Create one bill and download its PDF
- [ ] **System Health** page shows the database and backup as OK
- [ ] Restart the laptop and confirm the app opens again (the service starts automatically)

Their data lives in `C:\ProgramData\<NewShort>\`, with backups under `backups\daily` and
`backups\monthly`, plus a OneDrive copy if OneDrive was detected.

---

## 10. Sending updates later

When you fix a bug or add a feature:

1. Make the change in the client's folder (or copy it over from Jalaram, see below).
2. Bump the version in the four places listed in step 5f.
3. Commit, then run `build_installer.bat` again.
4. Send the new `<NewShort>-Setup.exe`. The friend runs it **over the existing install**
   and should **not** uninstall first. Their data, bills, and backups are kept, and any new
   database migrations run automatically.

**Never change the AppId, `<NewShort>`, or the service name after the first delivery.**
If you do, Windows treats the update as a separate program, and the data folder path changes.

**Bringing a Jalaram fix into the new client** (if you kept the `jalaram` remote from step 1):

```powershell
git fetch jalaram
git log jalaram/master --oneline          # find the fix's commit id
git cherry-pick <commit-id>
```

If the fix touched branded files (templates, installer), resolve the conflicts by keeping
the new client's name and details.

---

## Quick checklist

- [ ] `git clone` into a new folder (never copy with Explorer)
- [ ] Replace `static\images\logo.jpeg` and `qr_code.jpeg`
- [ ] Run the rename script (step 4) and record the new AppId
- [ ] Delete the old `C:\...\db.sqlite3` import line in `installer.iss`; check the publisher
- [ ] Edit `base.html` sidebar, `context_processors.py`, `bills\detail.html` invoice
- [ ] Run the `git grep` leftover check
- [ ] Test with `runserver 8001` and check a bill, PDF, and print
- [ ] Commit
- [ ] `build_installer.bat` → `packaging\output\<NewShort>-Setup.exe`
- [ ] Send the EXE → friend installs → set the delete password → verify
