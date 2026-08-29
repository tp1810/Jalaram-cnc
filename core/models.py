from django.db import models
from django.db.models import Max


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
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=15)
    customer_city = models.CharField(max_length=100)
    discount = models.IntegerField(default=0, help_text='Discount amount (Rs)')
    extra_charges = models.IntegerField(default=0, help_text='Additional charges (Rs)')
    paid_amount = models.IntegerField(default=0, help_text='Amount paid by customer (Rs)')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Bill'
        verbose_name_plural = 'Bills'

    def __str__(self):
        return f"Bill #{self.bill_number} - {self.customer_name}"

    def save(self, *args, **kwargs):
        if not self.pk:
            result = Bill.objects.aggregate(max_num=Max('bill_number'))
            self.bill_number = (result['max_num'] or 0) + 1
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return sum(item.amount for item in self.items.all())

    @property
    def total(self):
        return self.subtotal - self.discount + self.extra_charges

    @property
    def due_amount(self):
        return max(0, self.total - self.paid_amount)

    @property
    def is_paid(self):
        return self.due_amount == 0

    @property
    def payment_status(self):
        if self.paid_amount == 0:
            return 'Unpaid'
        elif self.is_paid:
            return 'Paid'
        else:
            return 'Partial'


class BillItem(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=200, blank=True)
    size = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)
    amount = models.IntegerField()

    class Meta:
        verbose_name = 'Bill Item'
        verbose_name_plural = 'Bill Items'

    def __str__(self):
        return f"Size: {self.size} x{self.quantity} - Rs{self.amount}"