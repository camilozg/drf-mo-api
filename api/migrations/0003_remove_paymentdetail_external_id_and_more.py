# Generated by Django 5.2 on 2025-04-24 14:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_alter_customer_preapproved_at'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paymentdetail',
            name='external_id',
        ),
        migrations.AlterField(
            model_name='payment',
            name='paid_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
