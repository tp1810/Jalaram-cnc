"""
Jalaram CNC Art & Craft — A4 Bill PDF Generator
Uses ReportLab. Layout mirrors the official Jalaram bill format.
"""

from datetime import date as dt_date
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def generate_bill(bill) -> bytes:
    """
    Generate a professional A4 PDF bill for a Bill model instance.

    Returns raw PDF bytes.
    """
    buffer = BytesIO()
    page_width, page_height = A4
    c = canvas.Canvas(buffer, pagesize=A4)

    black = colors.black
    dark  = colors.HexColor("#1a1a2e")
    grey_header = colors.HexColor("#dedede")
    grey_row    = colors.HexColor("#f7f7f7")
    orange      = colors.HexColor("#e07b00")

    left  = 15 * mm
    right = page_width - 15 * mm
    width = right - left

    y = page_height - 10 * mm

    # ── TOP BORDER LINE ──────────────────────────────────────────────
    c.setLineWidth(2)
    c.setStrokeColor(dark)
    c.line(left, y + 3 * mm, right, y + 3 * mm)
    y -= 2 * mm

    # ── TOP CONTACT ROW ──────────────────────────────────────────────
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left, y, "Dhruv Patel")
    c.drawRightString(right, y, "Nishith Patel")
    y -= 5 * mm

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#444444"))
    c.drawString(left, y, "Mo. 7573855710")
    c.drawRightString(right, y, "Mo. 6351325475")
    y -= 9 * mm

    # ── MAIN TITLE ───────────────────────────────────────────────────
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(page_width / 2, y, "CNC & LASER CUTTING")
    y -= 8 * mm

    # ── SUBTITLE ─────────────────────────────────────────────────────
    part1 = "Jalaram Art & Craft"
    part2 = "  (CNC Design Studio)"
    w1 = c.stringWidth(part1, "Times-BoldItalic", 14)
    w2 = c.stringWidth(part2, "Helvetica", 10)
    sub_x = (page_width - w1 - w2) / 2
    c.setFont("Times-BoldItalic", 14)
    c.setFillColor(dark)
    c.drawString(sub_x, y, part1)
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#555555"))
    c.drawString(sub_x + w1, y, part2)
    y -= 9 * mm

    # ── ADDRESS BOX ──────────────────────────────────────────────────
    box_h = 8 * mm
    box_y = y - box_h
    c.setLineWidth(1.4)
    c.setStrokeColor(dark)
    c.roundRect(left, box_y, width, box_h, 3, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(dark)
    c.drawCentredString(
        page_width / 2,
        box_y + 2.5 * mm,
        "Address : 02, Samarth Square Complex, Modasa Road, Kapadwanj"
    )
    y = box_y - 5 * mm

    # ── EMAIL ─────────────────────────────────────────────────────────
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#555555"))
    c.drawCentredString(page_width / 2, y, "E-mail :- jalaramcnc8154@gmail.com")
    y -= 7 * mm

    # ── DIVIDER ───────────────────────────────────────────────────────
    c.setLineWidth(0.8)
    c.setStrokeColor(colors.HexColor("#cccccc"))
    c.line(left, y + 2 * mm, right, y + 2 * mm)
    y -= 4 * mm

    # ── BILL NO & DATE ────────────────────────────────────────────────
    bill_date = bill.created_at.strftime("%d/%m/%Y")
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(dark)
    c.drawString(left, y, f"NO.   {bill.bill_number}")
    c.drawRightString(right, y, f"Date:   {bill_date}")
    y -= 5 * mm
    c.setLineWidth(0.5)
    c.setStrokeColor(colors.HexColor("#cccccc"))
    c.line(left, y + 1 * mm, right, y + 1 * mm)
    y -= 5 * mm

    # ── M/s ROW ───────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(dark)
    ms_label  = "M/s  "
    ms_lw     = c.stringWidth(ms_label,             "Helvetica-Bold", 10)
    ms_name_w = c.stringWidth(bill.customer_name,   "Helvetica-Bold", 10)
    c.drawString(left, y, ms_label + bill.customer_name)
    c.setLineWidth(0.5)
    c.setStrokeColor(colors.HexColor("#aaaaaa"))
    underline_x = left + ms_lw + ms_name_w + 2 * mm
    c.line(underline_x, y - 0.8 * mm, right, y - 0.8 * mm)
    y -= 7 * mm

    # ── VILL / MO ROW ────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(dark)
    vill_label = "Vill.  "
    mo_label   = "Mo.  "
    vill_lw    = c.stringWidth(vill_label,          "Helvetica-Bold", 10)
    city_w     = c.stringWidth(bill.customer_city,  "Helvetica-Bold", 10)
    mo_lw      = c.stringWidth(mo_label,            "Helvetica-Bold", 10)
    number_w   = c.stringWidth(bill.customer_phone, "Helvetica-Bold", 10)

    mid = page_width / 2
    c.drawString(left, y, vill_label + bill.customer_city)
    c.drawString(mid + 2 * mm, y, mo_label + bill.customer_phone)

    c.setLineWidth(0.5)
    c.setStrokeColor(colors.HexColor("#aaaaaa"))
    c.line(left + vill_lw + city_w + 2 * mm, y - 0.8 * mm, mid - 1 * mm, y - 0.8 * mm)
    c.line(mid + 2 * mm + mo_lw + number_w + 2 * mm, y - 0.8 * mm, right, y - 0.8 * mm)
    y -= 7 * mm

    # ── ITEMS TABLE ───────────────────────────────────────────────────
    # Column widths
    c0 = 12 * mm   # No.
    c2 = 30 * mm   # Size
    c3 = 32 * mm   # Amount
    c1 = width - c0 - c2 - c3  # Description (fills remaining)

    col_widths = [c0, c1, c2, c3]
    col_x = [left]
    for cw in col_widths[:-1]:
        col_x.append(col_x[-1] + cw)

    headers   = ["No.", "Description of Goods", "Size", "Amount"]
    header_h  = 9 * mm
    table_top = y

    # Header background
    c.setFillColor(grey_header)
    c.rect(left, table_top - header_h, width, header_h, fill=1, stroke=0)
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 10)
    for i, hdr in enumerate(headers):
        c.drawCentredString(col_x[i] + col_widths[i] / 2, table_top - header_h + 2.8 * mm, hdr)

    # Header border
    c.setLineWidth(1.2)
    c.setStrokeColor(dark)
    c.rect(left, table_top - header_h, width, header_h, stroke=1, fill=0)
    for cx in col_x[1:]:
        c.line(cx, table_top, cx, table_top - header_h)

    # Data rows — always 12 rows to keep the bill height consistent
    items     = list(bill.items.all())
    num_rows  = 12
    row_h     = 9 * mm
    row_top   = table_top - header_h

    for i in range(num_rows):
        ry = row_top - (i + 1) * row_h

        # Alternating row fill
        if i % 2 == 0:
            c.setFillColor(grey_row)
            c.rect(left, ry, width, row_h, fill=1, stroke=0)

        c.setFillColor(black)
        if i < len(items):
            item = items[i]
            c.setFont("Helvetica", 9.5)
            c.setFillColor(colors.HexColor("#333333"))
            c.drawCentredString(col_x[0] + col_widths[0] / 2, ry + 2.8 * mm, str(i + 1))
            desc = item.description if item.description else "CNC Art & Craft Product"
            c.drawString(col_x[1] + 2 * mm, ry + 2.8 * mm, desc[:42])   # truncate if too long
            c.drawCentredString(col_x[2] + col_widths[2] / 2, ry + 2.8 * mm, str(item.size))
            c.drawRightString(col_x[3] + col_widths[3] - 2 * mm, ry + 2.8 * mm,
                              f"{float(item.amount):,.2f}")

        c.setLineWidth(0.4)
        c.setStrokeColor(colors.HexColor("#cccccc"))
        c.line(left, ry, right, ry)

    # Outer table border + vertical dividers
    area_h = num_rows * row_h
    c.setLineWidth(1.2)
    c.setStrokeColor(dark)
    c.rect(left, row_top - area_h, width, area_h, stroke=1, fill=0)
    for cx in col_x[1:]:
        c.line(cx, row_top, cx, row_top - area_h)

    # ── SUBTOTAL ROW (if tax applies) ─────────────────────────────────
    subtotal   = bill.subtotal
    tax_rate   = bill.tax_rate
    tax_amount = bill.tax_amount
    total      = bill.total

    current_y = row_top - area_h

    if tax_rate > 0:
        sub_row_h = 8 * mm
        # Subtotal
        sub_y = current_y - sub_row_h
        c.setFillColor(colors.HexColor("#f0f2f7"))
        c.rect(left, sub_y, width, sub_row_h, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#444444"))
        c.setFont("Helvetica", 9.5)
        label_span = col_x[3] - left
        c.drawRightString(col_x[3] - 3 * mm, sub_y + 2.5 * mm, "Subtotal")
        c.drawRightString(col_x[3] + col_widths[3] - 2 * mm, sub_y + 2.5 * mm,
                          f"Rs. {float(subtotal):,.2f}")
        c.setLineWidth(0.5)
        c.setStrokeColor(colors.HexColor("#cccccc"))
        c.line(left, sub_y, right, sub_y)
        c.line(col_x[3], sub_y, col_x[3], sub_y + sub_row_h)
        current_y = sub_y

        # Tax row
        tax_y = current_y - sub_row_h
        c.setFillColor(colors.HexColor("#f0f2f7"))
        c.rect(left, tax_y, width, sub_row_h, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#444444"))
        c.setFont("Helvetica", 9.5)
        c.drawRightString(col_x[3] - 3 * mm, tax_y + 2.5 * mm, f"Tax @ {tax_rate}%")
        c.drawRightString(col_x[3] + col_widths[3] - 2 * mm, tax_y + 2.5 * mm,
                          f"Rs. {float(tax_amount):,.2f}")
        c.setLineWidth(0.5)
        c.setStrokeColor(colors.HexColor("#cccccc"))
        c.line(left, tax_y, right, tax_y)
        c.line(col_x[3], tax_y, col_x[3], tax_y + sub_row_h)
        current_y = tax_y

    # ── TOTAL ROW ─────────────────────────────────────────────────────
    tot_h = 10 * mm
    tot_y = current_y - tot_h
    c.setFillColor(dark)
    c.rect(left, tot_y, width, tot_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 11)
    label_span_w = col_x[3] - left
    c.drawCentredString(left + label_span_w / 2, tot_y + 3 * mm, "Total Amount")
    c.drawRightString(col_x[3] + col_widths[3] - 2 * mm, tot_y + 3 * mm,
                      f"Rs. {float(total):,.0f}/-")
    c.setLineWidth(1.2)
    c.setStrokeColor(dark)
    c.rect(left, tot_y, width, tot_h, stroke=1, fill=0)
    c.line(col_x[3], tot_y, col_x[3], tot_y + tot_h)

    y = tot_y - 10 * mm

    # ── NOTES (if any) ────────────────────────────────────────────────
    if bill.notes and bill.notes.strip():
        c.setFont("Helvetica-Oblique", 8.5)
        c.setFillColor(colors.HexColor("#666666"))
        c.drawString(left, y, f"Note: {bill.notes.strip()}")
        y -= 7 * mm

    # ── FOOTER ────────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(dark)
    c.drawRightString(right, y, "For, CNC & LASER CUTTING")
    y -= 6 * mm
    c.setFont("Times-BoldItalic", 11)
    c.setFillColor(orange)
    c.drawRightString(right, y, "Jalaram Art & Craft")
    y -= 5 * mm

    # Signature line
    sig_x = right - 45 * mm
    c.setLineWidth(0.5)
    c.setStrokeColor(colors.HexColor("#aaaaaa"))
    c.line(sig_x, y, right, y)
    c.setFont("Helvetica", 7.5)
    c.setFillColor(colors.HexColor("#888888"))
    c.drawCentredString(sig_x + (right - sig_x) / 2, y - 4 * mm, "Authorised Signatory")

    # ── BOTTOM BORDER LINE ────────────────────────────────────────────
    c.setLineWidth(2)
    c.setStrokeColor(dark)
    c.line(left, 12 * mm, right, 12 * mm)

    # Computer-generated note
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#aaaaaa"))
    c.drawCentredString(page_width / 2, 9 * mm, "This is a computer-generated bill.")

    c.save()
    return buffer.getvalue()
