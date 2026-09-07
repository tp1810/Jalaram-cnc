import datetime
import os
import platform
import shutil

from django.conf import settings as _settings
from django.contrib import messages
from django.db import models as db_models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import BillForm, BillItemFormSet, CustomerForm, ExpenseForm
from .models import Bill, BillItem, Customer, Expense


# ─────────────────────── HELPERS ─────────────────────────────────

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
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
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

            customer_fk = form.cleaned_data.get('customer')
            submitted_name = form.cleaned_data['customer_name']
            submitted_phone = form.cleaned_data['customer_phone']
            submitted_city = form.cleaned_data['customer_city']

            if customer_fk:
                original_phone = customer_fk.phone_number

                if submitted_phone != original_phone:
                    try:
                        target = Customer.objects.get(phone_number=submitted_phone)
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


# ────────────────────────── EXPENSES ────────────────────────────

def expense_list(request):
    expenses = Expense.objects.all()
    available_months = list(
        Expense.objects.dates('created_at', 'month', order='DESC')
    )
    query = request.GET.get('q', '').strip()
    amount = request.GET.get('amount', '').strip()
    month = request.GET.get('month', '').strip()
    expense_date = request.GET.get('date', '').strip()

    if query:
        expenses = expenses.filter(
            db_models.Q(title__icontains=query)
            | db_models.Q(notes__icontains=query)
        )
    if amount.isdigit():
        expenses = expenses.filter(amount=int(amount))
    if month:
        try:
            month_date = datetime.datetime.strptime(month, '%Y-%m').date()
            expenses = expenses.filter(
                created_at__year=month_date.year,
                created_at__month=month_date.month,
            )
        except ValueError:
            month = ''
    if expense_date:
        try:
            selected_date = datetime.date.fromisoformat(expense_date)
            expenses = expenses.filter(created_at__date=selected_date)
        except ValueError:
            expense_date = ''

    monthly_data = {}
    for expense in expenses:
        local_created_at = timezone.localtime(expense.created_at)
        month_key = local_created_at.strftime('%Y-%m')
        if month_key not in monthly_data:
            monthly_data[month_key] = {
                'display': local_created_at.strftime('%B %Y'),
                'total': 0,
                'expenses': [],
            }
        monthly_data[month_key]['total'] += expense.amount
        monthly_data[month_key]['expenses'].append(expense)

    monthly_list = sorted(monthly_data.items(), reverse=True)
    total_expense = sum(group['total'] for _, group in monthly_list)

    return render(request, 'expenses/list.html', {
        'monthly_data': monthly_list,
        'total_expense': total_expense,
        'expense_count': sum(len(group['expenses']) for _, group in monthly_list),
        'available_months': available_months,
        'filters': {
            'q': query,
            'amount': amount,
            'month': month,
            'date': expense_date,
        },
    })


def expense_create(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save()
            messages.success(request, f'Expense "{expense.title}" added successfully.')
            return redirect('expense_list')
        messages.error(request, 'Please correct the errors highlighted below.')
    else:
        form = ExpenseForm()

    return render(request, 'expenses/form.html', {'form': form})


@require_POST
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    title = expense.title
    expense.delete()
    messages.success(request, f'Expense "{title}" deleted successfully.')
    return redirect('expense_list')


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


def live_search_unpaid_bills(request):
    """Live search restricted to bills that still have an outstanding balance."""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})

    matching_bills = Bill.objects.prefetch_related('items').filter(
        db_models.Q(customer_name__icontains=query)
        | db_models.Q(customer_phone__icontains=query)
    )
    if query.isdigit():
        matching_bills = matching_bills | Bill.objects.prefetch_related('items').filter(
            bill_number=int(query)
        )

    unpaid_matches = [bill for bill in matching_bills if bill.due_amount > 0]
    unpaid_matches.sort(key=lambda bill: (-float(bill.due_amount), bill.created_at))
    results = [{
        'id': bill.id,
        'bill_number': bill.bill_number,
        'customer_name': bill.customer_name,
        'customer_phone': bill.customer_phone,
        'due_amount': float(bill.due_amount),
        'status': bill.payment_status,
    } for bill in unpaid_matches[:20]]

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

# ────────────────────────── SYSTEM HEALTH ───────────────────────────

def system_health(request):
    from jalaram_cnc.runtime_paths import DAILY_BACKUP_DIR, DATA_DIR, DB_PATH, LOG_DIR, MONTHLY_BACKUP_DIR

    # ─ Database
    db_ok = False
    db_size_kb = 0
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        db_ok = True
        if DB_PATH.exists():
            db_size_kb = DB_PATH.stat().st_size // 1024
    except Exception:
        pass

    # ─ Backups
    backup_daily_dir = DAILY_BACKUP_DIR
    backup_monthly_dir = MONTHLY_BACKUP_DIR
    daily_backups = sorted(backup_daily_dir.glob('db_*.sqlite3'), reverse=True) if backup_daily_dir.exists() else []
    monthly_backups = sorted(backup_monthly_dir.glob('db_*.sqlite3'), reverse=True) if backup_monthly_dir.exists() else []
    last_backup = None
    last_backup_size_kb = 0
    if daily_backups:
        last_backup = datetime.datetime.fromtimestamp(daily_backups[0].stat().st_mtime)
        last_backup_size_kb = daily_backups[0].stat().st_size // 1024

    # ─ Backup log last line
    last_backup_log = None
    log_path = LOG_DIR / 'backup.log'
    if log_path.exists():
        try:
            lines = [l for l in log_path.read_text(encoding='utf-8').splitlines() if l.strip()]
            last_backup_log = lines[-1] if lines else None
        except Exception:
            pass

    # ─ Disk
    disk_free_gb = disk_total_gb = None
    try:
        d = shutil.disk_usage(str(DATA_DIR))
        disk_free_gb = round(d.free / (1024 ** 3), 1)
        disk_total_gb = round(d.total / (1024 ** 3), 1)
    except Exception:
        pass

    # ─ OneDrive detection
    onedrive_path = os.environ.get('ONEDRIVE') or str(_settings.BASE_DIR.home() / 'OneDrive')
    onedrive_ok = os.path.isdir(onedrive_path)

    return render(request, 'system_health.html', {
        'db_ok': db_ok,
        'db_size_kb': db_size_kb,
        'last_backup': last_backup,
        'last_backup_size_kb': last_backup_size_kb,
        'daily_count': len(daily_backups),
        'monthly_count': len(monthly_backups),
        'last_backup_log': last_backup_log,
        'disk_free_gb': disk_free_gb,
        'disk_total_gb': disk_total_gb,
        'onedrive_ok': onedrive_ok,
        'debug_mode': _settings.DEBUG,
        'python_version': platform.python_version(),
        'platform_info': platform.platform(),
    })


def run_backup_now(request):
    """Trigger an on-demand backup from the System Health page (POST only)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        import contextlib
        import io

        from scripts.backup import run_backup

        output_stream = io.StringIO()
        with contextlib.redirect_stdout(output_stream):
            run_backup()
        return JsonResponse({'success': True, 'output': output_stream.getvalue().strip()})
    except Exception as exc:
        return JsonResponse({'success': False, 'output': str(exc)})