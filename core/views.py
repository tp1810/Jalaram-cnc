from io import BytesIO

from django.contrib import messages
from django.db import models as db_models
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from xhtml2pdf import pisa

from .forms import BillForm, BillItemFormSet, CustomerForm
from .models import Bill, BillItem, Customer


# ─────────────────────────── DASHBOARD ───────────────────────────

def dashboard(request):
    total_customers = Customer.objects.count()
    total_bills = Bill.objects.count()

    now = timezone.now()
    bills_this_month = list(
        Bill.objects.filter(
            created_at__year=now.year,
            created_at__month=now.month,
        ).prefetch_related('items')
    )
    monthly_revenue = sum(b.total for b in bills_this_month)

    all_bills = list(Bill.objects.prefetch_related('items'))
    total_revenue = sum(b.total for b in all_bills)

    recent_bills = Bill.objects.prefetch_related('items').order_by('-created_at')[:6]
    recent_customers = Customer.objects.order_by('-created_at')[:5]

    return render(request, 'dashboard.html', {
        'total_customers': total_customers,
        'total_bills': total_bills,
        'monthly_revenue': monthly_revenue,
        'total_revenue': total_revenue,
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
    return render(request, 'bills/detail.html', {'bill': bill})


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


def bill_pdf(request, pk):
    bill = get_object_or_404(Bill.objects.prefetch_related('items'), pk=pk)
    html = render_to_string('bills/pdf_template.html', {'bill': bill}, request=request)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Bill-{bill.bill_number}.pdf"'
    buffer = BytesIO()
    pdf = pisa.CreatePDF(BytesIO(html.encode('UTF-8')), dest=buffer)
    if pdf.err:
        return HttpResponse('Error generating PDF. Please try again.', status=500)
    response.write(buffer.getvalue())
    return response
