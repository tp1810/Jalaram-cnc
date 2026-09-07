# JALARAM CNC - PROJECT MEMORY & OPERATIONS

**Last Updated**: September 7, 2026
**Current Release**: 1.1.0
**Project**: Jalaram CNC Bill Management System
**Framework**: Django 6.0.5 / Python 3.14
**Production Server**: Waitress on `127.0.0.1:8000`
**Database**: SQLite
**Development Package Manager**: `uv`
**Distribution**: PyInstaller `onedir` + WinSW + Inno Setup
**Status**: Offline Windows production build

---

## BUSINESS DETAILS

| Field | Value |
|---|---|
| Business Name | Jalaram CNC Art & Craft |
| Address | 02, Samarth Square Complex, Modasa Road, Kapadwanj |
| Phone | +91 7573855710 / +91 6351325475 |
| Bank | State Bank of India, Kapadwanj |
| Account No | 36474515254 |
| IFSC | SBIN0000287 |

- Logo: `static/images/logo.jpeg`
- Payment QR: `static/images/qr_code.jpeg`

---

## CURRENT ARCHITECTURE

```text
Browser at http://127.0.0.1:8000
        |
        v
Waitress local WSGI server
        |
        v
Django application
        |
        v
SQLite database in C:\ProgramData\JalaramCNC
```

- The installed application is local-only and binds to `127.0.0.1`.
- No domain, hosting, internet connection, or database server is required.
- `JalaramCNCService` starts the app automatically through WinSW.
- WinSW restarts the packaged process after failures.
- WhiteNoise serves collected static files in production.
- Browser libraries and fonts are bundled under `static/vendor` for offline use.
- PDF creation is browser-side with bundled html2pdf.js.
- Playwright, Chromium, WeasyPrint, and ReportLab are not runtime dependencies.

---

## DEVELOPMENT AND INSTALLED PATHS

### Development checkout

When Python is not frozen, writable data remains in the repository:

```text
Jalaram CNC\
|- db.sqlite3
|- .env
|- logs\
|- backups\
`- media\
```

### Installed application files

```text
C:\Program Files\Jalaram CNC\
|- JalaramCNC.exe
|- JalaramCNCService.exe
|- JalaramCNCService.xml
|- Jalaram CNC.url
`- _internal\
```

### Installed persistent data

```text
C:\ProgramData\JalaramCNC\
|- db.sqlite3
|- configuration.env
|- .db_password_hash        # only after setting a delete password
|- logs\
|  |- app.log
|  |- error.log
|  |- backup.log
|  `- WinSW service logs
|- media\
`- backups\
   |- daily\
   `- monthly\
```

`jalaram_cnc/runtime_paths.py` owns source/frozen path selection. Use `JALARAM_CNC_DATA_DIR` only for isolated tests or support work.

---

## DEVELOPMENT SETUP

```powershell
uv venv --python 3.14
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Development URL:

```text
http://127.0.0.1:8000
```

Runtime dependencies:

```text
Django==6.0.5
pillow
waitress>=3.0.0
python-dotenv>=1.0.0
whitenoise>=6.7.0
```

Build dependency:

```text
pyinstaller==6.22.2
```

---

## CREATING THE WINDOWS EXE INSTALLER

### Build command

```powershell
.\build_installer.ps1 -Version 1.1.0
```

Or run:

```text
build_installer.bat
```

`create_deployment.bat` now forwards to `build_installer.bat`; it no longer creates the old source ZIP.

### Build pipeline

1. Installs runtime requirements into `.venv` with `uv`.
2. Installs the pinned PyInstaller build requirements.
3. Runs `manage.py check`.
4. Verifies every model change has a committed migration with `makemigrations --check --dry-run`.
5. Runs the complete `core` test suite.
6. Runs `collectstatic --clear`.
7. Downloads WinSW 2.12.0 if it is not cached in `packaging/tools`.
8. Runs PyInstaller using `packaging/JalaramCNC.spec`.
9. Adds WinSW and `JalaramCNCService.xml` to the frozen output.
10. Finds Inno Setup 6, installing it with `winget` when necessary.
11. Compiles `packaging/installer.iss`.

PyInstaller command used by the script:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean packaging\JalaramCNC.spec
```

Final distributable:

```text
packaging\output\JalaramCNC-Setup.exe
```

Send only `JalaramCNC-Setup.exe` to the destination laptop. Do not send `dist`, source files, Python, `.env`, `uv`, or a source ZIP.

### Release version checklist

Synchronize the version in:

- `jalaram_cnc/cli.py` - `APP_VERSION`
- `pyproject.toml` - `project.version`
- `packaging/installer.iss` - default `MyAppVersion`
- `build_installer.ps1` - default `Version`

Then run:

```powershell
uv lock
.\build_installer.ps1 -Version <new-version>
```

Verify the artifact:

```powershell
Get-Item packaging\output\JalaramCNC-Setup.exe |
    Select-Object FullName, Length, LastWriteTime, VersionInfo
Get-FileHash packaging\output\JalaramCNC-Setup.exe -Algorithm SHA256
```

Do not manually edit `build` or `dist`; both are generated.

### Git tracking for reproducible builds

Commit these build inputs:

```text
app.py
build_installer.ps1
build_installer.bat
create_deployment.bat
requirements.txt
requirements-build.txt
pyproject.toml
uv.lock
packaging\installer.iss
packaging\JalaramCNC.spec
packaging\JalaramCNCService.xml
static\css\
static\images\
static\vendor\
templates\
core\
jalaram_cnc\
scripts\
```

`static/vendor` must be committed because it contains the browser assets required for offline operation. It is source input, not generated output.

Keep these generated/private paths ignored:

```text
.venv\
.env
db.sqlite3
logs\
backups\
media\
staticfiles\
build\
dist\
packaging\tools\
packaging\output\
```

`packaging/tools/WinSW-x64.exe` is downloaded automatically by the build script. `packaging/output/JalaramCNC-Setup.exe` is a release artifact for direct distribution, not required in Git. A clean clone can recreate both by running the build command.

---

## INSTALLER BEHAVIOR

Stable Inno Setup AppId:

```text
{B0C97A31-49E9-4F38-9377-31969E8D0F0E}
```

The double opening brace in `AppId={{...}` is valid Inno Setup syntax for a literal GUID brace.

### Fresh installation

The user double-clicks `JalaramCNC-Setup.exe`, approves UAC, and clicks Install. The installer:

1. Creates `C:\ProgramData\JalaramCNC` and its subfolders.
2. Imports `C:\JalaramCNC\db.sqlite3` only if an installed database does not exist.
3. Generates `configuration.env` with a random Django secret and localhost settings.
4. Detects OneDrive when available and configures an optional mirror.
5. Runs Django migrations.
6. Creates and verifies an initial backup.
7. Installs `JalaramCNCService` through WinSW.
8. Configures immediate Automatic startup and restart-on-failure recovery.
9. Starts the service and waits up to 30 seconds for HTTP 200.
10. Creates Desktop and Start Menu shortcuts.
11. Offers to open `http://127.0.0.1:8000`.

No Python, `.env`, manual folders, commands, service setup, or Task Scheduler setup is required on the destination laptop.

### Upgrade/reinstall

Run the newer installer directly over the current installation. Do not uninstall first.

- The stable AppId upgrades the existing installation instead of duplicating it.
- The installer stops the current service.
- The existing executable creates a verified pre-upgrade backup.
- Application files are replaced.
- Database, configuration, logs, media, and backups remain in `ProgramData`.
- Migrations run before the new service starts.
- Legacy `JalaramCNC_DailyBackup` and `JalaramCNC_StartupBackup` tasks are removed.

### Uninstall

The uninstaller removes the service and legacy tasks. Business data under `C:\ProgramData\JalaramCNC` is retained. Back up the database before manually deleting that directory.

### Migrating the old source installation

For a laptop with `C:\JalaramCNC`:

1. Make an extra copy of `C:\JalaramCNC\db.sqlite3`.
2. Leave the original database in place.
3. Run the current installer.
4. Confirm customers and bills in the installed app.
5. Restart Windows and verify the Desktop shortcut.
6. Delete `C:\JalaramCNC` only after successful verification.

---

## WINDOWS SERVICE AND FAST STARTUP

Service name:

```text
JalaramCNCService
```

WinSW launches:

```text
JalaramCNC.exe serve
```

Behavior:

- Startup type is `Automatic`, not delayed automatic.
- Waitress binds `127.0.0.1:8000` immediately.
- Backup work does not block the web server.
- WinSW retries failures after 5, 15, and 30 seconds.
- The installer uses `JalaramCNC.exe wait-ready` and fails if HTTP 200 is not returned within 30 seconds.

Do not reintroduce `delayed-auto`; it caused a normal Windows delay of roughly 1-2 minutes before port 8000 became available.

---

## BACKUP SYSTEM

Automatic backups do not use Windows Task Scheduler in release 1.0.1.

### Automatic flow

1. Waitress starts immediately.
2. A daemon backup worker waits 10 seconds.
3. It checks for a valid daily backup newer than 24 hours.
4. If none exists, it creates and verifies a backup.
5. It repeats the check every hour while the service runs.

If the laptop was off when a backup became due, the next startup creates one shortly after the app becomes available.

### Backup safety

- Uses SQLite's online backup API while Django is running.
- Writes to a temporary file first.
- Runs `PRAGMA integrity_check` before publishing the backup.
- Removes the temporary file on failure.
- Applies OneDrive mirroring and retention only after verification.
- Backup failures are logged and do not stop Waitress.

### Local locations

```text
C:\ProgramData\JalaramCNC\backups\daily
C:\ProgramData\JalaramCNC\backups\monthly
```

### Retention

- Daily backups older than 30 days are removed after a successful backup.
- A monthly copy is created when a backup runs on the first day of a month.
- The newest 12 monthly copies are retained.

### OneDrive

OneDrive is optional. When detected during first configuration, backups are also copied to:

```text
<OneDrive>\JalaramCNC_Backups\daily
<OneDrive>\JalaramCNC_Backups\monthly
```

If OneDrive is missing or mirroring fails, verified local backups remain valid and the application continues.

### Manual backup

- Use **System Health > Backup Now**, or
- Run `JalaramCNC.exe backup`.

---

## PACKAGED CLI COMMANDS

```cmd
"C:\Program Files\Jalaram CNC\JalaramCNC.exe" <command>
```

| Command | Purpose |
|---|---|
| `serve` | Starts Waitress and the background backup worker |
| `init` | Creates configuration/folders and runs migrations |
| `migrate` | Runs Django migrations |
| `check` | Runs Django system checks |
| `doctor` | Checks paths, SQLite integrity, Django, and backup freshness |
| `backup` | Creates a verified backup immediately |
| `restore` | Interactive restore from local backups |
| `set-db-password` | Sets or changes the database-delete password |
| `delete-db` | Password-protected delete with emergency backup |
| `wait-ready` | Waits up to 30 seconds for local HTTP 200 |
| `version` | Prints the application version |

Service diagnostics:

```cmd
sc query JalaramCNCService
sc start JalaramCNCService
sc stop JalaramCNCService
```

Logs:

```text
C:\ProgramData\JalaramCNC\logs
```

---

## OFFLINE FRONTEND ASSETS

| Library | Bundled version/location |
|---|---|
| Bootstrap | 5.3.2 in `static/vendor/bootstrap` |
| Bootstrap Icons | 1.11.3 in `static/vendor/bootstrap-icons` |
| Inter | Local WOFF2 files in `static/vendor/inter` |
| SweetAlert2 | 11.14.5 in `static/vendor/sweetalert2` |
| html2pdf.js | 0.10.1 in `static/vendor/html2pdf` |
| Tom Select | 2.3.1 in `static/vendor/tom-select` |

Templates that use `{% static %}` must include `{% load static %}` themselves; Django does not inherit loaded template-tag libraries from `base.html`.

---

## DATABASE SCHEMA

### Customer

| Field | Type | Notes |
|---|---|---|
| `id` | AutoField | Primary key |
| `name` | CharField(200) | Required |
| `phone_number` | CharField(15) | Unique customer identity |
| `city` | CharField(100) | Required |
| `created_at` | DateTimeField | Automatic |
| `updated_at` | DateTimeField | Automatic |

### Bill

| Field | Type | Notes |
|---|---|---|
| `id` | AutoField | Primary key |
| `bill_number` | PositiveIntegerField | Unique, assigned with `Max()+1` |
| `customer` | FK(Customer) | Nullable, `SET_NULL` |
| `customer_name` | CharField(200) | Denormalized copy |
| `customer_phone` | CharField(15) | Denormalized copy |
| `customer_city` | CharField(100) | Denormalized copy |
| `discount` | IntegerField | Whole rupees |
| `extra_charges` | IntegerField | Whole rupees |
| `paid_amount` | IntegerField | Whole rupees |
| `notes` | TextField | Optional |
| `created_at` | DateTimeField | Automatic |
| `updated_at` | DateTimeField | Automatic |

Calculated properties:

| Property | Formula |
|---|---|
| `subtotal` | `sum(item.amount for item in items.all())` |
| `total` | `subtotal - discount + extra_charges` |
| `due_amount` | `max(0, total - paid_amount)` |
| `is_paid` | `due_amount == 0` |
| `payment_status` | `Unpaid`, `Partial`, or `Paid` |

### BillItem

| Field | Type | Notes |
|---|---|---|
| `id` | AutoField | Primary key |
| `bill` | FK(Bill) | Cascade, related name `items` |
| `description` | CharField(200) | Optional |
| `size` | CharField(100) | Required |
| `quantity` | PositiveIntegerField | Default 1 |
| `amount` | IntegerField | Whole rupees |

### Expense

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField | Primary key |
| `title` | CharField(200) | Required; stripped before save through the form |
| `amount` | PositiveIntegerField | Whole rupees; minimum value 1 |
| `notes` | TextField | Optional |
| `created_at` | DateTimeField | Automatic expense date and time |

Expenses were added by migration `core/migrations/0002_expense.py`. Development database migration was applied on September 7, 2026; installed and upgraded copies receive it through the existing installer migration step.

All money values are integer rupees.

---

## URL ROUTES

### Dashboard and system

| URL | Name | Purpose |
|---|---|---|
| `/` | `dashboard` | Statistics and recent data |
| `/system-health/` | `system_health` | Database, backup, disk, and runtime status |
| `/system-health/backup-now/` | `run_backup_now` | POST-only manual backup |

### Customers

| URL | Name | Purpose |
|---|---|---|
| `/customers/` | `customer_list` | List/search customers |
| `/customers/add/` | `customer_create` | Add customer |
| `/customers/phone-lookup/` | `customer_phone_lookup` | AJAX phone lookup |
| `/customers/live-search/` | `live_search_customers` | AJAX name/phone search |
| `/customers/<pk>/` | `customer_detail` | Customer and bill history |
| `/customers/<pk>/edit/` | `customer_update` | Edit customer |
| `/customers/<pk>/delete/` | `customer_delete` | POST-only delete |
| `/customers/<pk>/api/` | `customer_api` | Customer JSON |

### Bills

| URL | Name | Purpose |
|---|---|---|
| `/bills/` | `bill_list` | All bills, live search, date filter |
| `/bills/create/` | `bill_create` | Create bill |
| `/bills/unpaid/` | `unpaid_bills` | Outstanding bills and total due |
| `/bills/unpaid/live-search/` | `live_search_unpaid_bills` | Unpaid-only AJAX search |
| `/bills/monthly-revenue/` | `monthly_revenue` | Revenue grouped by month |
| `/bills/live-search/` | `live_search_bills` | AJAX name/phone/number search |
| `/bills/<pk>/` | `bill_detail` | Invoice, PDF, print, and share |
| `/bills/<pk>/edit/` | `bill_edit` | Edit bill |
| `/bills/<pk>/delete/` | `bill_delete` | POST-only delete |

### Expenses

| URL | Name | Purpose |
|---|---|---|
| `/expenses/` | `expense_list` | Monthly-grouped expense register with filters and totals |
| `/expenses/create/` | `expense_create` | Create an expense with automatic date/time |
| `/expenses/<pk>/delete/` | `expense_delete` | POST-only expense delete |

There is no `bill_print` or server-side `bill_pdf` route. PDF generation is browser-side through bundled html2pdf.js.

---

## IMPORTANT UI BEHAVIOR

### Bill creation

- Phone number is the customer identity.
- Selecting a customer fills name, phone, and city.
- Typing a known phone performs a debounced lookup.
- A changed/new phone can link or create the appropriate customer.
- Paid in Full sets and locks `paid_amount` to the calculated total.

### Unpaid Bills

- Shows only bills with `due_amount > 0`.
- Sorted by due amount descending, then date.
- Live search supports customer name, phone, and bill number.
- Search results never include fully paid bills.
- Calendar filter updates visible rows, count, and total due.
- Clear resets both search and date.
- Mobile layout keeps overflow inside the table.

### Expenses

- The sidebar contains **All Expenses** and **Add Expense** links.
- Creating an expense requires a title and whole-rupee amount of at least 1; notes are optional.
- Expense date and time use `created_at` and are recorded automatically on save.
- The expense register groups records into collapsible months in descending order.
- Every month shows its record count and subtotal; the page shows the filtered record count and grand total.
- Filters can be combined: title/notes text search, exact amount, month dropdown, and calendar date.
- Month grouping uses local time so it agrees with calendar-date filtering.
- Deletion is available from the register, requires confirmation, and is enforced as POST-only.
- There is no expense edit screen; the implemented scope is create, list/report, filter, and delete.

### PDF and print

- `bills/detail.html` renders the invoice inline.
- Detail PDF/share captures `#inv-page-content` with bundled html2pdf.js.
- Bill/customer list PDF actions fetch and render the detail invoice.
- Printing uses A4 with zero page margin and exact color adjustment.
- No Chromium or Playwright installation is needed.

---

## GENERATED CONFIGURATION

Installed `configuration.env` normally contains:

```text
DEBUG=False
DJANGO_SECRET_KEY=<random secret>
ALLOWED_HOSTS=127.0.0.1,localhost
SERVER_HOST=127.0.0.1
SERVER_PORT=8000
ONEDRIVE_BACKUP_DIR=<optional detected path>
```

Settings highlights:

- WhiteNoise follows Django SecurityMiddleware.
- Static files resolve from packaged `staticfiles` when frozen.
- SQLite, media, and logs resolve through `runtime_paths.py`.
- Rotating Django application and error logs are enabled.
- Allowed hosts default to localhost only.

---

## TESTING AND RELEASE VALIDATION

Run:

```powershell
.\.venv\Scripts\python.exe manage.py test core --verbosity 2
.\.venv\Scripts\python.exe manage.py check
```

Focused tests cover:

- Unpaid Bills search/date controls.
- Search by customer name, phone, and bill number.
- Exclusion of fully paid bills from unpaid search.
- Expense creation with automatic date/time and stripped titles.
- Rejection of zero-value expenses.
- Monthly expense grouping, record counts, subtotals, and grand total.
- Combined title/notes, exact amount, month, and calendar-date expense filters.
- POST-only expense deletion.
- Backup worker launch before Waitress.
- Backup only when no recent valid copy exists.

The current `core` suite contains 10 tests and passed after the expense feature was added. `makemigrations --check --dry-run` reports no model drift, and `manage.py check` reports no issues.

Release 1.1.0 frozen validation includes:

- Fresh migration and configuration creation.
- Upgrade from a database containing only `core.0001_initial`.
- Automatic application of `core.0002_expense` to the same SQLite file.
- Preservation of existing customer and bill rows during the migration.
- Packaged Expense list/create screens returning HTTP 200 and rendering saved expenses.
- SQLite integrity and verified backup.
- Dashboard and packaged static assets returning HTTP 200.
- Main application screens returning HTTP 200.
- Waitress responding before overdue backup starts.
- Deferred backup and optional OneDrive mirror afterward.
- Successful `wait-ready` check.
- Successful Inno Setup compilation.

---

## KNOWN CONSTRAINTS

1. `bill_number` uses `Max('bill_number') + 1`; acceptable for local single-user use but not high-concurrency safe.
2. Bill totals are Python properties, so filtering/sorting requires prefetched items and Python processing.
3. `bill_edit` does not use the full customer-upsert behavior of `bill_create`.
4. The unsigned installer can trigger SmartScreen; use **More info > Run anyway** or sign future releases.
5. Local backups do not protect against disk loss or theft; OneDrive or USB copies provide off-device protection.
6. Automatic backup timing is freshness-based, not fixed-clock: check hourly and back up when the newest valid copy is at least 24 hours old.

---

## VERSION HISTORY

| Version/Date | Change |
|---|---|
| 1.1.0 - 2026-09-07 | Added Expense persistence and migration, Add Expense and monthly-grouped All Expenses screens, combined search/amount/month/date filters, dynamic filtered totals, POST-only deletion, sidebar/admin support, and regression tests. Build now fails when model changes lack a committed migration or tests fail. Verified in-place upgrade preserves existing customer/bill rows while applying `core.0002_expense`. |
| 1.0.1 - 2026-09-05 | Removed failing Task Scheduler creation and delayed-auto startup. Waitress starts immediately; backup checks run in the background after 10 seconds and hourly thereafter. Added installer readiness verification. |
| 1.0.0 - 2026-09-05 | Added PyInstaller/WinSW/Inno single-EXE deployment, `ProgramData` persistence, upgrade-safe database handling, offline assets, System Health backups, and packaged CLI diagnostics. |
| 2026-09-05 | Added Unpaid Bills live search, date filter, dynamic visible count/total, mobile validation, and regression tests. |
| 2026-09-05 | Fixed missing `{% load static %}` in Bills List and Customer Detail and compiled all templates. |
| 2026-08-30 | Switched UI PDF downloads to html2pdf.js, fixed invoice printing/colors, added disclaimer, and removed duplicate metadata. |
| 2026-08-29 | Initial customers, bills, payment tracking, invoice, and PDF workflows. |
