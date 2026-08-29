import base64
import os
from io import BytesIO

from django.conf import settings as _settings
from django.contrib import messages
from django.db import models as db_models
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from .bill_generator import generate_bill
from .forms import BillForm, BillItemFormSet, CustomerForm
from .models import Bill, BillItem, Customer


# ─────────────────────── HELPERS ─────────────────────────────────

def _image_b64(rel_static_path):
    """Return a data-URI string for an image in the static folder (WeasyPrint-safe)."""
    try:
        full = os.path.join(_settings.BASE_DIR, 'static', rel_static_path)
        with open(full, 'rb') as fh:
            raw = base64.b64encode(fh.read()).decode('utf-8')
        ext = rel_static_path.rsplit('.', 1)[-1].lower()
        mime = 'jpeg' if ext in ('jpg', 'jpeg') else ext
        return f'data:image/{mime};base64,{raw}'
    except Exception:
        return ''


_ONES = [
    '', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
    'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen',
    'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen',
]
_TENS = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty',
         'Seventy', 'Eighty', 'Ninety']


def _n2w(n):
    """Convert a non-negative integer to English words (Indian system)."""
    n = int(n)
    if n == 0:
        return 'Zero'

    def _two(x):
        return _ONES[x] if x < 20 else _TENS[x // 10] + (' ' + _ONES[x % 10] if x % 10 else '')

    def _three(x):
        if x >= 100:
            return _ONES[x // 100] + ' Hundred' + (' ' + _two(x % 100) if x % 100 else '')
        return _two(x)

    parts = []
    for div, label in ((10_000_000, 'Crore'), (100_000, 'Lakh'), (1_000, 'Thousand')):
        if n >= div:
            parts.append(_three(n // div) + ' ' + label)
            n %= div
    if n:
        parts.append(_three(n))
    return ' '.join(parts)


def _amount_words(amount):
    """Return 'X Rupees and Y Paise Only' for a Decimal/float amount."""
    from decimal import Decimal as D
    amt = D(str(amount)).quantize(D('0.01'))
    rupees = int(amt)
    paise = int(round((amt - rupees) * 100))
    words = _n2w(rupees) + ' Rupees'
    if paise:
        words += ' and ' + _n2w(paise) + ' Paise'
    return words + ' Only'


# ─────────────────────────── DASHBOARD ───────────────────────────

def dashboard(request):
    total_customers = Customer.objects.count()
    total_bills = Bill.objects.count()

    # Get all bills this month with items
    now = timezone.now()
    bills_this_month = list(
        Bill.objects.filter(
            created_at__year=now.year,
            created_at__month=now.month,
        ).prefetch_related('items')
    )
    monthly_revenue = sum(b.total for b in bills_this_month)

    # Get unpaid bills (where due_amount > 0)
    all_bills = Bill.objects.prefetch_related('items').all()
    unpaid_bills = [b for b in all_bills if b.due_amount > 0]
    unpaid_bills_count = len(unpaid_bills)
    total_due = sum(b.due_amount for b in unpaid_bills)

    recent_bills = Bill.objects.prefetch_related('items').order_by('-created_at')[:6]
    recent_customers = Customer.objects.order_by('-created_at')[:5]

    return render(request, 'dashboard.html', {
        'total_customers': total_customers,
        'total_bills': total_bills,
        'monthly_revenue': monthly_revenue,
        'unpaid_bills_count': unpaid_bills_count,
        'total_due': total_due,
        'bills_this_month': len(bills_this_month),
        'recent_bills': recent_bills,
        'recent_customers': recent_customers,
    })


# ─────────────────────────── CUSTOMERS ───────────────────────────

def customer_list(request):
    query = request.GET.get('q', '').strip()
    customers = Customer.objects.annotate(bill_count=db_models.Count('bills'))
    if query:
        customers = customers.filter(
            db_models.Q(name__icontains=query)
            | db_models.Q(phone_number__icontains=query)
            | db_models.Q(city__icontains=query)
        )
    return render(request, 'customers/list.html', {
        'customers': customers,
        'query': query,
    })


def customer_create(request):
    form = CustomerForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        customer = form.save()
        messages.success(request, f'Customer "{customer.name}" added successfully!')
        return redirect('customer_list')
    return render(request, 'customers/form.html', {
        'form': form,
        'title': 'Add New Customer',
        'button_text': 'Add Customer',
    })


def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    bills = Bill.objects.filter(customer=customer).prefetch_related('items').order_by('-created_at')
    return render(request, 'customers/detail.html', {
        'customer': customer,
        'bills': bills,
    })


def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Customer "{customer.name}" updated successfully!')
        return redirect('customer_detail', pk=customer.pk)
    return render(request, 'customers/form.html', {
        'form': form,
        'customer': customer,
        'title': f'Edit — {customer.name}',
        'button_text': 'Update Customer',
    })


def customer_delete(request, pk):
    if request.method == 'POST':
        customer = get_object_or_404(Customer, pk=pk)
        name = customer.name
        customer.delete()
        messages.success(request, f'Customer "{name}" deleted successfully!')
    return redirect('customer_list')


def customer_api(request, pk):
    """JSON endpoint to auto-fill customer fields in the bill form."""
    customer = get_object_or_404(Customer, pk=pk)
    return JsonResponse({
        'name': customer.name,
        'phone': customer.phone_number,
        'city': customer.city,
    })


# ─────────────────────────── BILLS ───────────────────────────────

def _customers_dict():
    """Return a plain Python dict for use with Django's json_script template filter."""
    rows = Customer.objects.values('id', 'name', 'phone_number', 'city')
    return {
        str(r['id']): {
            'name': r['name'],
            'phone': r['phone_number'],
            'city': r['city'],
        }
        for r in rows
    }


def bill_list(request):
    query = request.GET.get('q', '').strip()
    bills = Bill.objects.prefetch_related('items').order_by('-created_at')
    if query:
        q_filter = (
            db_models.Q(customer_name__icontains=query)
            | db_models.Q(customer_phone__icontains=query)
            | db_models.Q(customer_city__icontains=query)
        )
        # Also search by numeric bill number
        if query.isdigit():
            q_filter |= db_models.Q(bill_number=int(query))
        bills = bills.filter(q_filter)
    return render(request, 'bills/list.html', {
        'bills': bills,
        'query': query,
    })


def bill_create(request):
    if request.method == 'POST':
        form = BillForm(request.POST)
        formset = BillItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            bill = form.save(commit=False)

            customer_fk = form.cleaned_data.get('customer')  # Customer instance or None
            submitted_name  = form.cleaned_data['customer_name']
            submitted_phone = form.cleaned_data['customer_phone']
            submitted_city  = form.cleaned_data['customer_city']

            if customer_fk:
                original_phone = customer_fk.phone_number

                if submitted_phone != original_phone:
                    # ── Phone was changed → treat as a new customer ──
                    try:
                        # New phone already exists → link to that existing customer
                        target = Customer.objects.get(phone_number=submitted_phone)
                        # Update name/city on that record if changed
                        updated = False
                        if submitted_name and submitted_name != target.name:
                            target.name = submitted_name
                            updated = True
                        if submitted_city and submitted_city != target.city:
                            target.city = submitted_city
                            updated = True
                        if updated:
                            target.save()
                        bill.customer = target
                        bill.customer_name = target.name
                        bill.customer_phone = target.phone_number
                        bill.customer_city = target.city
                    except Customer.DoesNotExist:
                        # Completely new phone → create new customer
                        new_customer = Customer.objects.create(
                            name=submitted_name,
                            phone_number=submitted_phone,
                            city=submitted_city,
                        )
                        bill.customer = new_customer
                        bill.customer_name = new_customer.name
                        bill.customer_phone = new_customer.phone_number
                        bill.customer_city = new_customer.city
                else:
                    # ── Same phone: update name/city on the original customer if changed ──
                    updated = False
                    if submitted_name and submitted_name != customer_fk.name:
                        customer_fk.name = submitted_name
                        updated = True
                    if submitted_city and submitted_city != customer_fk.city:
                        customer_fk.city = submitted_city
                        updated = True
                    if updated:
                        customer_fk.save()
                    bill.customer = customer_fk
                    bill.customer_name = customer_fk.name
                    bill.customer_phone = customer_fk.phone_number
                    bill.customer_city = customer_fk.city
            else:
                # ── Manual entry: phone is the primary identifier ──
                try:
                    existing = Customer.objects.get(phone_number=submitted_phone)
                    # Same phone → update name/city if changed
                    updated = False
                    if submitted_name and submitted_name != existing.name:
                        existing.name = submitted_name
                        updated = True
                    if submitted_city and submitted_city != existing.city:
                        existing.city = submitted_city
                        updated = True
                    if updated:
                        existing.save()
                    bill.customer = existing
                    bill.customer_name = existing.name
                    bill.customer_phone = existing.phone_number
                    bill.customer_city = existing.city
                except Customer.DoesNotExist:
                    # Brand-new customer → save to DB
                    new_customer = Customer.objects.create(
                        name=submitted_name,
                        phone_number=submitted_phone,
                        city=submitted_city,
                    )
                    bill.customer = new_customer
                    bill.customer_name = new_customer.name
                    bill.customer_phone = new_customer.phone_number
                    bill.customer_city = new_customer.city

            bill.save()
            formset.instance = bill
            formset.save()
            messages.success(request, f'Bill #{bill.bill_number} created successfully!')
            return redirect('bill_detail', pk=bill.pk)
        messages.error(request, 'Please correct the errors highlighted below.')
    else:
        form = BillForm()
        formset = BillItemFormSet()

    return render(request, 'bills/form.html', {
        'form': form,
        'formset': formset,
        'customers_dict': _customers_dict(),
        'title': 'Create New Bill',
        'button_text': 'Generate Bill',
    })


def bill_detail(request, pk):
    bill = get_object_or_404(Bill.objects.prefetch_related('items'), pk=pk)
    return render(request, 'bills/detail.html', {
        'bill': bill,
        'amount_words': _amount_words(bill.total),
    })


def bill_delete(request, pk):
    if request.method == 'POST':
        bill = get_object_or_404(Bill, pk=pk)
        bill_num = bill.bill_number
        bill.delete()
        messages.success(request, f'Bill #{bill_num} deleted successfully!')
    return redirect('bill_list')


def customer_phone_lookup(request):
    """Return customer data for a given phone number (used by bill form JS)."""
    phone = request.GET.get('phone', '').strip()
    if not phone:
        return JsonResponse({'found': False})
    try:
        customer = Customer.objects.get(phone_number=phone)
        return JsonResponse({
            'found': True,
            'id': customer.pk,
            'name': customer.name,
            'city': customer.city,
        })
    except Customer.DoesNotExist:
        return JsonResponse({'found': False})


def bill_edit(request, pk):
    """Edit an existing bill"""
    bill = get_object_or_404(Bill, pk=pk)
    if request.method == 'POST':
        form = BillForm(request.POST, instance=bill)
        formset = BillItemFormSet(request.POST, instance=bill)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, f'Bill #{bill.bill_number} updated successfully!')
            return redirect('bill_detail', pk=bill.pk)
        messages.error(request, 'Please correct the errors highlighted below.')
    else:
        form = BillForm(instance=bill)
        formset = BillItemFormSet(instance=bill)

    return render(request, 'bills/form.html', {
        'form': form,
        'formset': formset,
        'bill': bill,
        'customers_dict': _customers_dict(),
        'title': f'Edit Bill #{bill.bill_number}',
        'button_text': 'Update Bill',
        'is_edit': True,
    })


def unpaid_bills(request):
    """List all unpaid bills sorted by due amount and date"""
    # Get all bills with prefetch_related for efficiency
    all_bills = Bill.objects.prefetch_related('items').all()
    
    # Filter bills where due_amount > 0
    bills = [b for b in all_bills if b.due_amount > 0]
    
    # Sort by due amount (highest first) then by date
    bills = sorted(bills, key=lambda b: (-float(b.due_amount), b.created_at))
    
    total_due = sum(b.due_amount for b in bills)

    return render(request, 'bills/unpaid.html', {
        'bills': bills,
        'total_due': total_due,
    })


def monthly_revenue(request):
    """Display monthly revenue breakdown"""
    all_bills = Bill.objects.prefetch_related('items').order_by('-created_at')
    
    # Group bills by month
    monthly_data = {}
    total_revenue = 0
    
    for bill in all_bills:
        month_key = bill.created_at.strftime('%Y-%m')
        month_display = bill.created_at.strftime('%B %Y')
        
        if month_key not in monthly_data:
            monthly_data[month_key] = {
                'display': month_display,
                'total': 0,
                'bills': []
            }
        
        monthly_data[month_key]['total'] += float(bill.total)
        monthly_data[month_key]['bills'].append(bill)
        total_revenue += float(bill.total)
    
    # Sort by month descending
    monthly_list = sorted(monthly_data.items(), reverse=True)

    return render(request, 'bills/monthly_revenue.html', {
        'monthly_data': monthly_list,
        'total_revenue': total_revenue,
    })


def bill_pdf(request, pk):
    """Generate PDF bill using Playwright + Chromium"""
    bill = get_object_or_404(Bill.objects.prefetch_related('items'), pk=pk)

    try:
        from playwright.sync_api import sync_playwright

        html_string = render_to_string('bills/print.html', {
            'bill': bill,
            'amount_words': _amount_words(bill.total),
            'is_preview': True,
            'logo_b64': _image_b64('images/logo.jpeg'),
            'qr_b64': _image_b64('images/qr_code.jpeg'),
        }, request=request)

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html_string, wait_until='load')
            pdf_bytes = page.pdf(
                format='A4',
                print_background=True,
                margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'},
            )
            browser.close()

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Bill-{bill.bill_number}.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f'Error generating PDF: {e}', status=500)


def bill_print(request, pk):
    """Display printable bill template"""
    bill = get_object_or_404(Bill.objects.prefetch_related('items'), pk=pk)
    is_preview = request.GET.get('preview') == '1'
    return render(request, 'bills/print.html', {
        'bill': bill,
        'amount_words': _amount_words(bill.total),
        'is_preview': is_preview,
    })


def live_search_bills(request):
    """Live search for bills (AJAX)"""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})
    
    bills = Bill.objects.prefetch_related('items').filter(
        db_models.Q(customer_name__icontains=query)
        | db_models.Q(customer_phone__icontains=query)
    )
    
    if query.isdigit():
        bills = bills | Bill.objects.filter(bill_number=int(query))
    
    results = [{
        'id': bill.id,
        'bill_number': bill.bill_number,
        'customer_name': bill.customer_name,
        'customer_phone': bill.customer_phone,
        'total': float(bill.total),
        'status': bill.payment_status,
    } for bill in bills[:20]]
    
    return JsonResponse({'results': results})


def live_search_customers(request):
    """Live search for customers (AJAX)"""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})
    
    customers = Customer.objects.filter(
        db_models.Q(name__icontains=query)
        | db_models.Q(phone_number__icontains=query)
    )
    
    results = [{
        'id': customer.id,
        'name': customer.name,
        'phone': customer.phone_number,
        'city': customer.city,
    } for customer in customers[:20]]
    
    return JsonResponse({'results': results})
