from django.contrib import admin
from .models import Customer, Loan, Payment, PaymentDetail

admin.site.register(Customer)
admin.site.register(Loan)
admin.site.register(Payment)
admin.site.register(PaymentDetail)
