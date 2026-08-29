# Generated migration for adding payment fields to Bill and quantity to BillItem

from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        # Add new fields to Bill model
        migrations.AddField(
            model_name='bill',
            name='discount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Discount in amount (₹)', max_digits=10),
        ),
        migrations.AddField(
            model_name='bill',
            name='extra_charges',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Additional charges (travel, etc) in amount (₹)', max_digits=10),
        ),
        migrations.AddField(
            model_name='bill',
            name='paid_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Amount paid by customer (₹)', max_digits=10),
        ),
        migrations.AddField(
            model_name='bill',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        
        # Add quantity field to BillItem
        migrations.AddField(
            model_name='billitem',
            name='quantity',
            field=models.PositiveIntegerField(default=1),
        ),
    ]
