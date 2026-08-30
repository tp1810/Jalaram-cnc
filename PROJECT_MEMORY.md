# JALARAM CNC — PROJECT MEMORY & DOCUMENTATION

**Last Updated**: August 30, 2026  
**Project**: Jalaram CNC Bill Management System  
**Framework**: Django 6.0.5, Python 3.x  
**Database**: SQLite (`db.sqlite3`)  
**Package Manager**: `uv` (venv at `.venv/`)  
**Status**: Active / Production-ready for local use

---

## BUSINESS DETAILS (hardcoded in templates)

| Field | Value |
|---|---|
| Business Name | Jalaram CNC Art & Craft |
| Address | 02, Samarth Square Complex, Modasa Road, Kapadwanj |
| Phone | +91 7573855710 / +91 6351325475 |
| Bank | State Bank of India, Kapadwanj |
| Account No | 36474515254 |
| IFSC | SBIN0000287 |

Logo: `static/images/logo.jpeg`  
QR Code: `static/images/qr_code.jpeg`

---

## HOW TO RUN

```bash
# First time setup
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium       # needed for /bills/<pk>/pdf/
python manage.py migrate
python manage.py runserver
```

Or with `uv`:
```bash
uv pip install -r requirements.txt
```

App runs at: `http://127.0.0.1:8000/`

---

## PROJECT STRUCTURE

```
Jalaram CNC/
+-- db.sqlite3
+-- manage.py
+-- main.py
+-- requirements.txt
+-- setup.bat
+-- biomedix_invoice_template.html   # reference design only
+-- PROJECT_MEMORY.md
|
+-- core/                            # main Django app
|   +-- models.py
|   +-- views.py
|   +-- forms.py
|   +-- urls.py
|   +-- admin.py
|   +-- apps.py
|   +-- context_processors.py
|   +-- bill_generator.py            # ReportLab helper (NOT used by any URL)
|   +-- migrations/
|       +-- 0001_initial.py
|       +-- 0002_payment_fields.py
|
+-- jalaram_cnc/                     # Django project settings
|   +-- settings.py
|   +-- urls.py
|   +-- wsgi.py
|
+-- templates/
|   +-- base.html
|   +-- dashboard.html
|   +-- bills/
|   |   +-- list.html
|   |   +-- detail.html              # inline invoice + html2pdf.js
|   |   +-- form.html                # create/edit with Tom Select
|   |   +-- print.html               # used by bill_pdf (Playwright)
|   |   +-- invoice.html             # older standalone template (kept)
|   |   +-- pdf_template.html        # legacy (kept for compatibility)
|   |   +-- unpaid.html
|   |   +-- monthly_revenue.html
|   +-- customers/
|       +-- list.html
|       +-- detail.html
|       +-- form.html
|
+-- static/
    +-- css/style.css
    +-- images/
        +-- logo.jpeg
        +-- qr_code.jpeg
```

---

## DEPENDENCIES

### Python (`requirements.txt`)
```
Django==6.0.5
reportlab>=3.6.13     # used in bill_generator.py (NOT routed — legacy)
pillow
weasyprint>=60.0      # in requirements but NOT used (Playwright replaced it)
```
**Playwright** is used for server-side PDF but is installed separately:
```bash
playwright install chromium
```

### Frontend CDNs (in templates)
| Library | Version | Used In |
|---|---|---|
| Bootstrap 5 | 5.3.2 | base.html |
| Bootstrap Icons | 1.11.3 | base.html |
| Google Fonts (Inter) | — | base.html |
| SweetAlert2 | 11 | base.html |
| html2pdf.js | 0.10.1 | bills/detail.html |
| Tom Select (Bootstrap 5 theme) | 2.3.1 | bills/form.html |

---

## DATABASE SCHEMA

### Customer
| Field | Type | Notes |
|---|---|---|
| id | AutoField | PK |
| name | CharField(200) | |
| phone_number | CharField(15) | **unique** |
| city | CharField(100) | |
| created_at | DateTimeField | auto |
| updated_at | DateTimeField | auto |

`__str__` → `"Name (phone_number)"`  
Ordered by `-created_at`

### Bill
| Field | Type | Notes |
|---|---|---|
| id | AutoField | PK |
| bill_number | PositiveIntegerField | unique, auto-set on create via Max()+1 |
| customer | FK(Customer) | nullable, SET_NULL on delete |
| customer_name | CharField(200) | denormalised copy |
| customer_phone | CharField(15) | denormalised copy |
| customer_city | CharField(100) | denormalised copy |
| discount | IntegerField | default 0 |
| extra_charges | IntegerField | default 0 |
| paid_amount | IntegerField | default 0 |
| notes | TextField | blank=True |
| created_at | DateTimeField | auto |
| updated_at | DateTimeField | auto |

**Calculated properties** (Python only, not DB columns):

| Property | Formula |
|---|---|
| `subtotal` | `sum(item.amount for item in items.all())` |
| `total` | `subtotal - discount + extra_charges` |
| `due_amount` | `max(0, total - paid_amount)` |
| `is_paid` | `due_amount == 0` |
| `payment_status` | `'Unpaid'` / `'Partial'` / `'Paid'` |

`__str__` → `"Bill #N - Customer Name"`

### BillItem
| Field | Type | Notes |
|---|---|---|
| id | AutoField | PK |
| bill | FK(Bill) | CASCADE, related_name='items' |
| description | CharField(200) | blank=True (optional) |
| size | CharField(100) | required |
| quantity | PositiveIntegerField | default 1 |
| amount | IntegerField | required, whole rupees |

> **All money values are IntegerField** — whole rupees, no decimals.

---

## URL ROUTES

All routes are in `core/urls.py`, mounted at `/` via `jalaram_cnc/urls.py`.

### Dashboard
| URL | Name | View |
|---|---|---|
| `/` | `dashboard` | Dashboard with stats, recent bills/customers |

### Customers
| URL | Name | View | Notes |
|---|---|---|---|
| `/customers/` | `customer_list` | List with search | |
| `/customers/add/` | `customer_create` | Create form | |
| `/customers/phone-lookup/` | `customer_phone_lookup` | AJAX JSON | Returns customer by phone |
| `/customers/live-search/` | `live_search_customers` | AJAX JSON | Search by name/phone |
| `/customers/<pk>/` | `customer_detail` | Detail + bill history | |
| `/customers/<pk>/edit/` | `customer_update` | Edit form | |
| `/customers/<pk>/delete/` | `customer_delete` | POST only | |
| `/customers/<pk>/api/` | `customer_api` | AJAX JSON | Returns name/phone/city |

### Bills
| URL | Name | View | Notes |
|---|---|---|---|
| `/bills/` | `bill_list` | List with search | |
| `/bills/create/` | `bill_create` | Create form | |
| `/bills/unpaid/` | `unpaid_bills` | Unpaid list | Sorted by due amount desc |
| `/bills/monthly-revenue/` | `monthly_revenue` | Revenue by month | |
| `/bills/live-search/` | `live_search_bills` | AJAX JSON | Search by name/phone/number |
| `/bills/<pk>/` | `bill_detail` | Inline invoice | PDF/Print/Share buttons |
| `/bills/<pk>/edit/` | `bill_edit` | Edit form | |
| `/bills/<pk>/delete/` | `bill_delete` | POST only | |
| `/bills/<pk>/pdf/` | `bill_pdf` | Playwright PDF | Downloads PDF file |

> `bill_print` URL **does not exist** — it was removed. Do not reference `{% url 'bill_print' %}` anywhere.

---

## VIEWS REFERENCE (`core/views.py`)

### Helper functions
- `_image_b64(rel_static_path)` — reads static file, returns `data:image/...;base64,...` URI (for Playwright rendering)
- `_n2w(n)` / `_amount_words(amount)` — converts integer amount to words ("Five Hundred Rupees Only"), Indian number system
- `_customers_dict()` — returns `{str(id): {name, phone, city}}` dict for the bill form JSON context

### View logic highlights

**`bill_create` / `bill_edit`** — Smart customer management:
1. Phone number is the unique customer identifier
2. If a customer is selected from dropdown + phone unchanged → update name/city if different
3. If phone is changed → find/create customer with new phone
4. If manual entry (no dropdown) → look up by phone, auto-create if new

**`bill_pdf`** — Playwright server-side PDF:
- Renders `bills/print.html` with `is_preview=True`, `logo_b64`, `qr_b64`
- Opens Chromium headless, sets HTML content, exports PDF (A4, no margins)
- Returns `application/pdf` inline response
- If Playwright fails → returns HTTP 500 with error text

**`dashboard`** — uses `prefetch_related('items')` + Python list comprehension (F() expressions can't be used on @property fields)

**`unpaid_bills`** — sorted in Python: `(-due_amount, created_at)`

---

## FORMS REFERENCE (`core/forms.py`)

### `CustomerForm`
- Fields: `name`, `phone_number`, `city`

### `BillForm`
- Fields: `customer`, `customer_name`, `customer_phone`, `customer_city`, `discount`, `extra_charges`, `paid_amount`, `notes`
- `customer`: required=False, Tom Select searchable dropdown (name + phone)
- `customer_city`: required=False
- `discount`, `extra_charges`, `paid_amount`: required=False, `clean_*` methods default to `0` if blank
- New bill: initial values for discount/extra_charges/paid_amount are `''` (shows placeholder, not 0)
- `clean()`: validates customer_name and customer_phone are non-empty; strips whitespace

### `BillItemForm` + `BillItemFormSet`
- Fields: `description` (optional), `size`, `quantity`, `amount`
- FormSet: `min_num=1`, `extra=1`, `can_delete=True`

---

## TEMPLATES REFERENCE

### `base.html`
- Sidebar (`<aside class="sidebar">`) + topbar (`<header class="topbar">`) + `<main class="page-content">`
- Blocks: `title`, `page_heading`, `content`, `extra_css`, `extra_js`
- Context processor provides `today` (date) and `business_name` to every template

### `bills/detail.html`
- Renders the full invoice inline (no iframe) using CSS matching `print.html` design
- Invoice element: `id="inv-page-content"` on `.inv-page` div
- Action buttons: Back, Edit, Download PDF, Print, Share, Delete
- **Print button**: `onclick="window.print()"` — prints the current page directly
- **@media print CSS**: hides sidebar, topbar, action bar; renders only the invoice
- **`downloadInvoicePDF()`**: clones `#inv-page-content` into off-screen `position:fixed; left:-9999px; width:794px` container to avoid Bootstrap column width constraints, then uses html2pdf.js
- **`shareBill()`**: same clone approach, generates PDF blob, uses Web Share API; falls back to download
- `pdfOpts()`: `margin:0, scale:2, useCORS:true, pagebreak:{mode:'avoid-all'}, jsPDF:{format:'a4'}`
- `BILL_NUM` JS variable set from `{{ bill.bill_number }}`
- Amount in words displayed via `{{ amount_words }}` context variable

### `bills/print.html`
- Standalone page with full invoice (no base.html extends)
- Used exclusively by `bill_pdf` view (Playwright renders it server-side)
- Has a toolbar (`.no-print`) hidden when `is_preview=True`
- Uses base64 images from `logo_b64` / `qr_b64` context vars (needed because Playwright can't load static files via relative URL)
- Shows Advance Paid only if `paid_amount > 0`; shows Due Payment only if `paid_amount > 0 AND due_amount > 0`

### `bills/form.html`
- Extends `base.html`, uses `{% block extra_css %}` for Tom Select CSS
- **Tom Select**: initialised on `#id_customer`; dispatches native `change` event so existing autofill JS works
- **Autofill**: selecting customer from dropdown fills name/phone/city; typing phone triggers `/customers/phone-lookup/` debounced AJAX
- **"Paid in Full" toggle** (`#paid-full-check`): sets paid_amount = total, locks field; unchecking restores
- `fmt(n)` JS function: `Math.round(n)` — integer display, no decimals
- `updateSummary()`: live calculation of subtotal/total/due shown in right column
- Customer data passed as `{{ customers_dict|json_script:"customer-data" }}` (XSS-safe)

### `dashboard.html`
- 4 stat cards: Total Customers, Total Bills, This Month Revenue (₹), Pending Due (₹)
- Recent Bills table (last 6), Recent Customers list (last 5)
- Quick action cards: Unpaid Bills, Monthly Revenue, View All Bills

### `bills/unpaid.html`
- Table: Bill#, Customer, Phone, Total, Paid Amount (badge: ₹X if paid, "Not Paid" if 0), Due Amount, Date, Actions
- Summary card showing total due

---

## CONTEXT PROCESSOR (`core/context_processors.py`)

```python
def site_info(request):
    return {'today': timezone.now().date(), 'business_name': 'Jalaram CNC Art & Craft'}
```
Available in every template as `{{ today }}` and `{{ business_name }}`.

---

## ADMIN (`core/admin.py`)

- `CustomerAdmin`: list_display name/phone/city/created_at; search by name/phone/city
- `BillAdmin`: list_display bill_number/customer_name/phone/city/created_at; readonly bill_number; inline BillItemInline
- `BillItemInline`: TabularInline, fields description/size/amount

---

## SETTINGS HIGHLIGHTS (`jalaram_cnc/settings.py`)

| Setting | Value | Notes |
|---|---|---|
| `DEBUG` | `True` (env: `DEBUG`) | Set to False in production |
| `SECRET_KEY` | placeholder | **Change before production** |
| `ALLOWED_HOSTS` | `['*']` | **Restrict in production** |
| `DATABASE` | SQLite `db.sqlite3` | |
| `STATIC_URL` | `/static/` | |
| `STATICFILES_DIRS` | `[BASE_DIR / 'static']` | |
| Context processors | `core.context_processors.site_info` | adds today + business_name |

---

## KNOWN GOTCHAS / IMPORTANT NOTES

1. **`bill_print` URL is gone** — removed entirely. Never use `{% url 'bill_print' ... %}` in any template — it will crash the page with `NoReverseMatch` at render time (Django resolves `{% url %}` tags in template rendering, not just when called from JS).

2. **Money is IntegerField** — all amounts (discount, extra_charges, paid_amount, BillItem.amount) are whole rupees. No decimal points anywhere in the system.

3. **@property totals can't use F() expressions** — subtotal/total/due_amount are Python properties, not DB columns. All views that filter/sort by these must use `prefetch_related('items')` and Python list comprehensions.

4. **bill_number auto-increment** uses `Max('bill_number') + 1` — not thread-safe under very high concurrency (not an issue for local/single-user use).

5. **Playwright must be installed separately** — `playwright install chromium`. If missing, `/bills/<pk>/pdf/` returns HTTP 500.

6. **WeasyPrint is in requirements.txt but NOT used** — leftover from an earlier version; Playwright is the actual PDF renderer.

7. **ReportLab (`bill_generator.py`) is NOT routed** — exists in the codebase but no URL/view calls it.

8. **Customer phone_number is unique** — attempting to create two customers with the same phone raises `IntegrityError`. The bill create/edit logic handles this by upsert logic (find existing → update, or create new).

9. **Tom Select replaces the native `<select>`** — when TomSelect is initialized on `#id_customer`, the native select is hidden. The existing `change` event listener is preserved because TomSelect's `onChange` callback dispatches a native `change` event.

10. **PDF from detail.html uses a clone** — `downloadInvoicePDF()` clones the invoice div into a `position:fixed; left:-9999px; width:794px` off-screen container. This is necessary because Bootstrap's column system constrains the rendered width, which caused left-cropping in earlier versions.

---

## INVOICE LAYOUT (print.html / detail.html)

```
+-------------------------------------------------------------+
| [LOGO 90px]  Jalaram CNC Art & Craft              INVOICE   |
|              Address, Phone                  Bill #: [auto] |
|                                              Date:  [auto]  |
+-------------------------+-----------------------------------+
| BILL TO                 |  Bill Number  :  #NNN             |
| Customer Name           |  Date         :  DD Mon YYYY      |
| Phone: XXXXXXXXXX       |  Payment      :  Paid/Partial/..  |
| City                    |                                    |
+-------------------------+-----------------------------------+
| #  | Description |    Size       |  Qty  |  Amount (Rs)     |
| 1  | [text]      | [12x18 inch]  |   2   |       500        |
+-------------------------------------------------------------+
|                         Sub Total    :          Rs NNN      |
|                         Discount     :         -Rs NNN      |
|                         Extra Charges:         +Rs NNN      |
|                         TOTAL AMOUNT :          Rs NNN      |
+-------------------------------------------------------------+
|  Amount in Words: Five Hundred Rupees Only                  |
+-------------------------------------------------------------+
|  (if paid_amount > 0)  Advance Paid  :  Rs NNN              |
|  (if due > 0)          Due Payment   :  Rs NNN              |
+-------------------------+-----------------------------------+
| BANK DETAILS            |      [QR CODE 120px]              |
| Bank : SBI, Kapadwanj   |  Scan to Pay                      |
| A/C  : 36474515254      |                                    |
| IFSC : SBIN0000287      |                                    |
+-------------------------+-----------------------------------+
```

---

## COMMON TASKS

### Run development server
```bash
.venv\Scripts\python.exe manage.py runserver
```

### Apply migrations after model changes
```bash
.venv\Scripts\python.exe manage.py makemigrations
.venv\Scripts\python.exe manage.py migrate
```

### Check for errors
```bash
.venv\Scripts\python.exe manage.py check
```

### Access Django admin
```
http://127.0.0.1:8000/admin/
```
Create superuser first: `.venv\Scripts\python.exe manage.py createsuperuser`

---

## VERSION HISTORY

| Date | Change |
|---|---|
| 2026-08-30 | Full PROJECT_MEMORY rewrite — accurate to actual codebase |
| 2026-08-30 | Fixed: bill_print removal, extra_charges required error, encoding corruption (₹/—/→), Tom Select searchable dropdown, clone-based PDF, @media print CSS |
| 2026-08-29 | html2pdf.js client-side PDF, inline invoice rendering on detail page, IntegerField migration, Paid-in-Full toggle |
| 2026-08-29 | Initial: customers, bills, payment tracking, live search, Playwright PDF, professional invoice design |
