import json
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

def _customers_json():
    rows = Customer.objects.values('id', 'name', 'phone_number', 'city')
    return json.dumps({
        str(r['id']): {
            'name': r['name'],
            'phone': r['phone_number'],
            'city': r['city'],
        }
        for r in rows
    })


def bill_list(request):
    query = request.GET.get('q', '').strip()
    bills = Bill.objects.prefetch_related('items').order_by('-created_at')
    if query:
        bills = bills.filter(
            db_models.Q(bill_number__icontains=query)
            | db_models.Q(customer_name__icontains=query)
            | db_models.Q(customer_phone__icontains=query)
            | db_models.Q(customer_city__icontains=query)
        )
    return render(request, 'bills/list.html', {
        'bills': bills,
        'query': query,
    })


def bill_create(request):
    if request.method == 'POST':
        form = BillForm(request.POST)
        formset = BillItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            bill = form.save()
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
        'customers_json': _customers_json(),
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
