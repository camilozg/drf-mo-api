from django.db import models
from django.core.validators import MinValueValidator


class Customer(models.Model):
    """
    Represents a customer with their status, score, and other metadata.

    Fields:
    - created_at: Timestamp when the customer was created.
    - updated_at: Timestamp when the customer was last updated.
    - external_id: Unique identifier for the customer.
    - status: Current status of the customer (e.g., active, inactive).
    - score: Credit score of the customer.
    - preapproved_at: Timestamp when the customer was preapproved.
    """

    STATUS_CHOICES = (
        (1, 'activo'),
        (2, 'inactivo'),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    external_id = models.CharField(max_length=60, unique=True)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=1)
    score = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    preapproved_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.external_id


class Loan(models.Model):
    """
    Represents a loan associated with a customer.

    Fields:
    - created_at: Timestamp when the loan was created.
    - updated_at: Timestamp when the loan was last updated.
    - external_id: Unique identifier for the loan.
    - amount: Total amount of the loan.
    - status: Current status of the loan (e.g., pending, active, rejected, paid).
    - contract_version: Version of the loan contract.
    - maximum_payment_date: Latest date for loan repayment.
    - taken_at: Timestamp when the loan was taken.
    - outstanding: Outstanding amount of the loan.
    - customer: Foreign key linking the loan to a customer.
    """

    STATUS_CHOICES = (
        (1, 'pending'),
        (2, 'active'),
        (3, 'rejected'),
        (4, 'paid'),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    external_id = models.CharField(max_length=60, unique=True)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=1)
    contract_version = models.CharField(max_length=30, null=True, blank=True)
    maximum_payment_date = models.DateTimeField(null=True, blank=True)
    taken_at = models.DateTimeField(null=True, blank=True)
    outstanding = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)

    def __str__(self):
        return self.external_id


class Payment(models.Model):
    """
    Represents a payment made by a customer.

    Fields:
    - created_at: Timestamp when the payment was created.
    - updated_at: Timestamp when the payment was last updated.
    - external_id: Unique identifier for the payment.
    - total_amount: Total amount of the payment.
    - status: Current status of the payment (e.g., completed, rejected).
    - paid_at: Timestamp when the payment was made.
    - customer: Foreign key linking the payment to a customer.
    """

    STATUS_CHOICES = (
        (1, 'completed'),
        (2, 'rejected'),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    external_id = models.CharField(max_length=60, unique=True)
    total_amount = models.DecimalField(
        max_digits=20, decimal_places=10, validators=[MinValueValidator(0)]
    )
    status = models.SmallIntegerField(choices=STATUS_CHOICES)
    paid_at = models.DateTimeField(auto_now_add=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)

    def __str__(self):
        return self.external_id


class PaymentDetail(models.Model):
    """
    Represents the details of a payment applied to a loan.

    Fields:
    - created_at: Timestamp when the payment detail was created.
    - updated_at: Timestamp when the payment detail was last updated.
    - amount: Amount applied to the loan.
    - loan: Foreign key linking the payment detail to a loan.
    - payment: Foreign key linking the payment detail to a payment.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    amount = models.DecimalField(
        max_digits=20, decimal_places=10, validators=[MinValueValidator(0)]
    )
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.payment.customer.external_id} - {self.payment.external_id} - {self.loan.external_id}"
