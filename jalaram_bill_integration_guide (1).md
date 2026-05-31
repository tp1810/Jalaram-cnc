# Jalaram Art & Craft — Bill PDF Generator (Django Integration Guide)

## Overview

This document provides everything needed to integrate a professional **A4 bill PDF generator** for **Jalaram CNC Art & Craft** into a Django web application.

- PDF is generated using Python's `reportlab` library
- Date is **auto-filled** using today's date — no manual input needed
- Customer name, city, mobile are dynamically inserted via a form
- Up to **12 line items** supported per bill

---

## Requirements

```bash
pip install reportlab
pip install django
```

---

## Project File Structure

```
your_project/
├── billing/
│   ├── __init__.py
│   ├── views.py
│   ├── urls.py
│   ├── forms.py
│   ├── bill_generator.py     ← Core PDF generator (do not modify layout)
│   └── templates/
│       └── billing/
│           └── bill_form.html
├── your_project/
│   ├── settings.py
│   └── urls.py
└── manage.py
```

---

## bill_generator.py — Core PDF Generator

> Place this file at `billing/bill_generator.py`. Do not change the layout logic.

```python
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def generate_bill(data, output_path):
    """
    Generate a Jalaram CNC Art & Craft A4 bill PDF.

    Args:
        data (dict): Bill data dictionary (see structure below).
        output_path (str or file-like): File path OR a Django HttpResponse / BytesIO object.
    """
    page_width, page_height = A4
    c = canvas.Canvas(output_path, pagesize=A4)

    black = colors.black
    left  = 15 * mm
    right = page_width - 15 * mm
    width = right - left

    y = page_height - 10 * mm

    # ── TOP CONTACT ROW ──────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left, y, "Dhruv Patel")
    c.drawRightString(right, y, "Nishith Patel")
    y -= 5.5 * mm

    c.setFont("Helvetica", 9)
    c.drawString(left, y, "Mo. 7573855710")
    c.drawRightString(right, y, "Mo. 6351325475")
    y -= 9 * mm

    # ── MAIN TITLE ───────────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(page_width / 2, y, "CNC & LASER CUTTING")
    y -= 8 * mm

    # ── SUBTITLE ─────────────────────────────────────────────────────────────
    part1 = "Jalaram Art & Craft"
    part2 = "  (CNC Design Studio)"
    w1 = c.stringWidth(part1, "Times-BoldItalic", 14)
    w2 = c.stringWidth(part2, "Helvetica", 10)
    sub_x = (page_width - w1 - w2) / 2
    c.setFont("Times-BoldItalic", 14)
    c.drawString(sub_x, y, part1)
    c.setFont("Helvetica", 10)
    c.drawString(sub_x + w1, y, part2)
    y -= 9 * mm

    # ── ADDRESS BOX ──────────────────────────────────────────────────────────
    box_h = 8 * mm
    box_y = y - box_h
    c.setLineWidth(1.4)
    c.roundRect(left, box_y, width, box_h, 3, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(
        page_width / 2,
        box_y + 2.2 * mm,
        "Address : 02, Samarth Square Complex, Modasa Road, Kapadwanj"
    )
    y = box_y - 5 * mm

    # ── EMAIL ─────────────────────────────────────────────────────────────────
    c.setFont("Helvetica", 9)
    c.drawCentredString(page_width / 2, y, "E-mail :- jalaramcnc8154@gmail.com")
    y -= 8 * mm

    # ── BILL NO & DATE ────────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left, y, f"NO.   {data['bill_no']}")
    c.drawRightString(right, y, f"Date:   {data['date']}")
    y -= 6 * mm
    c.setLineWidth(0.6)
    c.line(left, y + 1 * mm, right, y + 1 * mm)
    y -= 4 * mm

    # ── M/s ROW ───────────────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 10)
    ms_label   = "M/s  "
    ms_label_w = c.stringWidth(ms_label,              "Helvetica-Bold", 10)
    ms_name_w  = c.stringWidth(data['customer_name'], "Helvetica-Bold", 10)
    c.drawString(left, y, ms_label + data['customer_name'])
    underline_x = left + ms_label_w + ms_name_w + 2 * mm
    c.setLineWidth(0.5)
    c.line(underline_x, y - 0.8 * mm, right, y - 0.8 * mm)
    y -= 7 * mm

    # ── VILL / MO ROW ────────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 10)
    vill_label = "Vill.  "
    mo_label   = "Mo.  "
    vill_lw    = c.stringWidth(vill_label,              "Helvetica-Bold", 10)
    city_w     = c.stringWidth(data['customer_city'],   "Helvetica-Bold", 10)
    mo_lw      = c.stringWidth(mo_label,                "Helvetica-Bold", 10)
    number_w   = c.stringWidth(data['customer_number'], "Helvetica-Bold", 10)

    mid = page_width / 2
    c.drawString(left, y, vill_label + data['customer_city'])
    c.drawString(mid + 2 * mm, y, mo_label + data['customer_number'])

    c.setLineWidth(0.5)
    c.line(left + vill_lw + city_w + 2 * mm, y - 0.8 * mm, mid - 1 * mm, y - 0.8 * mm)
    c.line(mid + 2 * mm + mo_lw + number_w + 2 * mm, y - 0.8 * mm, right, y - 0.8 * mm)
    y -= 6 * mm

    # ── ITEMS TABLE ───────────────────────────────────────────────────────────
    c0 = 12 * mm
    c2 = 28 * mm
    c3 = 30 * mm
    c1 = width - c0 - c2 - c3

    col_widths = [c0, c1, c2, c3]
    col_x = [left]
    for cw in col_widths[:-1]:
        col_x.append(col_x[-1] + cw)

    headers  = ["No.", "Description of Goods", "Size", "Amount"]
    header_h = 9 * mm
    table_top = y

    c.setFillColor(colors.HexColor("#dedede"))
    c.rect(left, table_top - header_h, width, header_h, fill=1, stroke=0)
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 10)
    for i, hdr in enumerate(headers):
        c.drawCentredString(col_x[i] + col_widths[i] / 2, table_top - header_h + 2.8 * mm, hdr)
    c.setLineWidth(1.2)
    c.rect(left, table_top - header_h, width, header_h, stroke=1, fill=0)
    for cx in col_x[1:]:
        c.line(cx, table_top, cx, table_top - header_h)

    row_h    = 9 * mm
    num_rows = 12
    area_h   = num_rows * row_h
    row_top  = table_top - header_h

    for i in range(num_rows):
        ry = row_top - (i + 1) * row_h
        if i % 2 == 0:
            c.setFillColor(colors.HexColor("#f7f7f7"))
            c.rect(left, ry, width, row_h, fill=1, stroke=0)
            c.setFillColor(black)
        if i < len(data["items"]):
            item = data["items"][i]
            c.setFont("Helvetica", 9.5)
            c.drawCentredString(col_x[0] + col_widths[0] / 2, ry + 2.8 * mm, str(item["no"]))
            c.drawString(col_x[1] + 2 * mm, ry + 2.8 * mm, item["description"])
            c.drawCentredString(col_x[2] + col_widths[2] / 2, ry + 2.8 * mm, str(item["size"]))
            c.drawRightString(col_x[3] + col_widths[3] - 2 * mm, ry + 2.8 * mm, f"{item['amount']:,.0f}")
        c.setLineWidth(0.4)
        c.line(left, ry, right, ry)

    c.setLineWidth(1.2)
    c.rect(left, row_top - area_h, width, area_h, stroke=1, fill=0)
    for cx in col_x[1:]:
        c.line(cx, row_top, cx, row_top - area_h)

    # Total row
    tot_y = row_top - area_h - row_h
    c.setFillColor(colors.HexColor("#dedede"))
    c.rect(left, tot_y, width, row_h, fill=1, stroke=0)
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 11)
    label_span_w = col_x[3] - left
    c.drawCentredString(left + label_span_w / 2, tot_y + 3 * mm, "Total Amount")
    c.drawRightString(col_x[3] + col_widths[3] - 2 * mm, tot_y + 3 * mm,
                      f"Rs. {data['total_amount']:,.0f}/-")
    c.setLineWidth(1.2)
    c.rect(left, tot_y, width, row_h, stroke=1, fill=0)
    c.line(col_x[3], tot_y, col_x[3], tot_y + row_h)

    y = tot_y - 8 * mm

    # ── FOOTER ───────────────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(right, y, "For, CNC & LASER CUTTING")
    y -= 6 * mm
    c.setFont("Times-BoldItalic", 11)
    c.drawRightString(right, y, "Jalaram Art & Craft")

    c.save()
```

---

## Bill Data Structure

```python
from datetime import date

bill_data = {
    "bill_no":         "001",                  # Bill number (string)
    "date":            date.today().strftime("%d/%m/%Y"),  # ← Auto-filled, DO NOT ask user
    "customer_name":   "Ramesh Sharma",        # From form input — printed after "M/s"
    "customer_number": "9876543210",           # Customer mobile number
    "customer_city":   "Ahmedabad",            # Customer city / village
    "items": [
        {
            "no":          1,
            "description": "CNC Wood Cutting - 4x8 ft",
            "size":        '4"x8"',
            "amount":      1700       # In rupees (int or float)
        },
        # up to 12 items
    ],
    "total_amount": 3200   # Pre-calculated sum of all item amounts
}
```

> **Key rules for the LLM:**
> - `date` must always be set to `date.today().strftime("%d/%m/%Y")` — never ask the user to enter it
> - `customer_name` is printed directly after "M/s " on the bill — pass it exactly as the user typed
> - `total_amount` must be the sum of all `item["amount"]` values — calculate it in the view, not the template
> - Maximum 12 items — if more are submitted, only the first 12 will appear on the bill

---

## forms.py

```python
from django import forms


class BillItemForm(forms.Form):
    description = forms.CharField(max_length=200, label="Description of Goods")
    size        = forms.CharField(max_length=50,  label="Size")
    amount      = forms.DecimalField(max_digits=10, decimal_places=2, label="Amount (Rs.)")


class BillForm(forms.Form):
    bill_no         = forms.CharField(max_length=20,  label="Bill No.")
    customer_name   = forms.CharField(max_length=100, label="Customer Name")
    customer_number = forms.CharField(max_length=15,  label="Customer Mobile")
    customer_city   = forms.CharField(max_length=100, label="City / Village")
```

---

## views.py

```python
import io
from datetime import date
from django.http import HttpResponse
from django.shortcuts import render
from .forms import BillForm, BillItemForm
from .bill_generator import generate_bill


def bill_form_view(request):
    """Renders the bill entry form."""
    bill_form  = BillForm()
    item_forms = [BillItemForm(prefix=f"item_{i}") for i in range(12)]
    return render(request, "billing/bill_form.html", {
        "bill_form":  bill_form,
        "item_forms": item_forms,
    })


def generate_bill_view(request):
    """Handles POST — builds bill_data and streams PDF."""
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    bill_form = BillForm(request.POST)
    items     = []
    total     = 0.0

    for i in range(12):
        item_form = BillItemForm(request.POST, prefix=f"item_{i}")
        if item_form.is_valid():
            desc   = item_form.cleaned_data["description"].strip()
            size   = item_form.cleaned_data["size"].strip()
            amount = float(item_form.cleaned_data["amount"])
            if desc:   # only include rows where description is filled
                total += amount
                items.append({
                    "no":          len(items) + 1,
                    "description": desc,
                    "size":        size,
                    "amount":      amount,
                })

    if not bill_form.is_valid() or not items:
        return HttpResponse("Invalid form data. Please go back and fill all required fields.", status=400)

    bill_data = {
        "bill_no":         bill_form.cleaned_data["bill_no"],
        "date":            date.today().strftime("%d/%m/%Y"),   # ← auto date
        "customer_name":   bill_form.cleaned_data["customer_name"],
        "customer_number": bill_form.cleaned_data["customer_number"],
        "customer_city":   bill_form.cleaned_data["customer_city"],
        "items":           items,
        "total_amount":    total,
    }

    buffer = io.BytesIO()
    generate_bill(bill_data, buffer)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="bill_{bill_data["bill_no"]}.pdf"'
    return response
```

---

## urls.py (billing app)

```python
from django.urls import path
from . import views

urlpatterns = [
    path("",               views.bill_form_view,     name="bill_form"),
    path("generate/",      views.generate_bill_view,  name="generate_bill"),
]
```

## urls.py (project root)

```python
from django.urls import path, include

urlpatterns = [
    path("billing/", include("billing.urls")),
]
```

---

## bill_form.html — Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Jalaram Art & Craft — Generate Bill</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 860px; margin: 40px auto; padding: 0 20px; }
    h2   { color: #333; }
    .section { background: #f9f9f9; border: 1px solid #ddd; border-radius: 6px; padding: 20px; margin-bottom: 24px; }
    label  { display: block; margin-top: 10px; font-weight: bold; font-size: 13px; }
    input  { width: 100%; padding: 7px 10px; margin-top: 4px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
    table  { width: 100%; border-collapse: collapse; }
    th, td { padding: 6px 8px; border: 1px solid #ccc; font-size: 13px; }
    th     { background: #dedede; }
    td input { border: none; padding: 4px; width: 100%; }
    button { margin-top: 20px; padding: 12px 30px; background: #1a1a1a; color: white; border: none; border-radius: 5px; font-size: 15px; cursor: pointer; }
    button:hover { background: #444; }
  </style>
</head>
<body>

<h2>Jalaram Art & Craft — Bill Generator</h2>

<form method="POST" action="{% url 'generate_bill' %}">
  {% csrf_token %}

  <div class="section">
    <h3>Bill Details</h3>
    <label>Bill No.</label>
    <input type="text" name="bill_no" required placeholder="e.g. 001">

    <label>Customer Name <small>(printed after M/s)</small></label>
    <input type="text" name="customer_name" required placeholder="Full name">

    <label>Customer Mobile</label>
    <input type="text" name="customer_number" required placeholder="10-digit number">

    <label>City / Village</label>
    <input type="text" name="customer_city" required placeholder="e.g. Ahmedabad">
  </div>

  <div class="section">
    <h3>Items <small>(fill only the rows you need — max 12)</small></h3>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Description of Goods</th>
          <th>Size</th>
          <th>Amount (Rs.)</th>
        </tr>
      </thead>
      <tbody>
        {% for i in "123456789012"|make_list %}
        {% with forloop.counter0 as idx %}
        <tr>
          <td style="text-align:center; color:#999;">{{ forloop.counter }}</td>
          <td><input type="text"   name="item_{{ idx }}-description" placeholder="e.g. CNC Wood Cutting"></td>
          <td><input type="text"   name="item_{{ idx }}-size"        placeholder='e.g. 4"x8"' style="width:80px"></td>
          <td><input type="number" name="item_{{ idx }}-amount"      placeholder="0" min="0" step="0.01" style="width:100px"></td>
        </tr>
        {% endwith %}
        {% endfor %}
      </tbody>
    </table>
  </div>

  <button type="submit">Generate Bill PDF</button>
</form>

</body>
</html>
```

---

## Key Behaviours Summary

| Field | Source | Notes |
|---|---|---|
| `bill_no` | User form input | Manual entry |
| `date` | `date.today()` in view | **Auto — never ask user** |
| `customer_name` | User form input | Printed directly after "M/s" |
| `customer_number` | User form input | Printed after "Mo." |
| `customer_city` | User form input | Printed after "Vill." |
| `items` | Form rows (up to 12) | Empty rows are skipped automatically |
| `total_amount` | Calculated in view | Sum of all filled item amounts |

---

## Prompt to Give Your Copilot / LLM

Paste this exactly:

> "I have a Django project. Integrate the attached `bill_generator.py` into a `billing` app using the structure and code provided in this guide. The date must always be auto-filled using `date.today()` — do not add a date field to the form. Customer name is typed by the user and printed after 'M/s' on the bill. Use the exact `views.py`, `forms.py`, `urls.py`, and `bill_form.html` from this guide. Do not change the `generate_bill()` function layout."
