from django.db import models
from django.db.models import Max
from decimal import Decimal


class Customer(models.Model):
    name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=15, unique=True)
    city = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'

    def __str__(self):
        return f"{self.name} ({self.phone_number})"


class Bill(models.Model):
    bill_number = models.PositiveIntegerField(unique=True, editable=False, default=0)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bills',
    )
    # Snapshot of customer info at time of billing
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=15)
    customer_city = models.CharField(max_length=100)
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00')
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Bill'
        verbose_name_plural = 'Bills'

    def __str__(self):
        return f"Bill #{self.bill_number} — {self.customer_name}"

    def save(self, *args, **kwargs):
        if not self.pk:  # only on creation
            result = Bill.objects.aggregate(max_num=Max('bill_number'))
            self.bill_number = (result['max_num'] or 0) + 1
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return sum(item.amount for item in self.items.all())

    @property
    def tax_amount(self):
        return (self.subtotal * self.tax_rate / Decimal('100')).quantize(Decimal('0.01'))

    @property
    def total(self):
        return self.subtotal + self.tax_amount


class BillItem(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=200, blank=True)
    size = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Bill Item'
        verbose_name_plural = 'Bill Items'

    def __str__(self):
        return f"Size: {self.size} — ₹{self.amount}"
