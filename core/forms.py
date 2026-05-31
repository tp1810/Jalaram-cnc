from django import forms
from django.forms import inlineformset_factory
from .models import Customer, Bill, BillItem


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone_number', 'city']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Name',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 9876543210',
                'maxlength': '15',
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City',
            }),
        }
        labels = {
            'phone_number': 'Phone Number',
        }


class BillForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = [
            'customer', 'customer_name', 'customer_phone',
            'customer_city', 'tax_rate', 'notes',
        ]
        widgets = {
            'customer': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_customer',
            }),
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Customer Name',
                'id': 'id_customer_name',
            }),
            'customer_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone Number',
                'id': 'id_customer_phone',
            }),
            'customer_city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City',
                'id': 'id_customer_city',
            }),
            'tax_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'id': 'id_tax_rate',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Optional notes about this bill...',
            }),
        }
        labels = {
            'customer': 'Select Existing Customer (optional)',
            'customer_name': 'Customer Name',
            'customer_phone': 'Phone Number',
            'customer_city': 'City',
            'tax_rate': 'Tax / GST Rate (%)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].required = False
        self.fields['customer'].empty_label = '— Select existing customer (optional) —'
        # City is optional (name + phone are always required)
        self.fields['customer_city'].required = False

    def clean(self):
        cleaned = super().clean()
        name = (cleaned.get('customer_name') or '').strip()
        phone = (cleaned.get('customer_phone') or '').strip()
        city = (cleaned.get('customer_city') or '').strip()

        if not name:
            self.add_error('customer_name', 'Customer name is required.')
        if not phone:
            self.add_error('customer_phone', 'Phone number is required.')

        # Normalise stripped values back into cleaned data
        cleaned['customer_name'] = name
        cleaned['customer_phone'] = phone
        cleaned['customer_city'] = city
        return cleaned


class BillItemForm(forms.ModelForm):
    class Meta:
        model = BillItem
        fields = ['description', 'size', 'amount']
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Product description (optional)',
            }),
            'size': forms.TextInput(attrs={
                'class': 'form-control form-control-sm item-size',
                'placeholder': 'e.g. 12×18 inch',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm item-amount',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00',
            }),
        }


BillItemFormSet = inlineformset_factory(
    Bill,
    BillItem,
    form=BillItemForm,
    extra=1,
    min_num=1,
    validate_min=True,
    can_delete=True,
)
