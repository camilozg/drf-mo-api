from rest_framework import serializers
from .models import Customer, Loan, Payment, PaymentDetail
from django.db.models import Sum
from decimal import Decimal


class CustomerSerializer(serializers.ModelSerializer):
    """
    Serializer for the Customer model.
    Handles serialization and deserialization of Customer objects.
    """

    class Meta:
        model = Customer
        fields = ['external_id', 'status', 'score', 'preapproved_at']
        read_only_fields = ['status']


class LoanSerializer(serializers.ModelSerializer):
    """
    Serializer for the Loan model.
    Handles validation and serialization of Loan objects.
    """

    customer_external_id = serializers.SlugRelatedField(
        source='customer', slug_field='external_id', queryset=Customer.objects.all()
    )

    class Meta:
        model = Loan
        fields = [
            'external_id',
            'customer_external_id',
            'amount',
            'outstanding',
            'status',
        ]
        read_only_fields = ['outstanding', 'status']

    def validate(self, data):
        """
        Validates the loan data before saving.
        Ensures the loan amount is positive and does not exceed the customer's credit limit.
        """
        customer = data.get('customer')
        amount = data.get('amount')
        status = data.get('status')

        if self.instance:
            if self.instance.status != 1 and status == 3:
                raise serializers.ValidationError(
                    "Solo se puede rechazar el préstamo si está en estado pendiente."
                )

            if status == 4:
                raise serializers.ValidationError(
                    "El préstamo se marcará automáticamente como pagado cuando el monto pendiente sea 0."
                )
        else:
            data['outstanding'] = data['amount']

            if amount <= 0:
                raise serializers.ValidationError(
                    {"amount": "El monto debe ser mayor a cero."}
                )

            total_outstanding = (
                Loan.objects.filter(
                    customer=customer, status__in=[1, 2]
                )  # pending and active loans
                .aggregate(total=Sum('outstanding'))
                .get('total')
                or 0.0
            )

            if Decimal(total_outstanding) + Decimal(amount) > customer.score:
                raise serializers.ValidationError(
                    {
                        "outstanding": "El préstamo excede el límite de crédito disponible para el cliente."
                    }
                )

        return data


class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for the Payment model.
    Handles validation, creation, and serialization of Payment objects.
    """

    customer_external_id = serializers.SlugRelatedField(
        source='customer', slug_field='external_id', queryset=Customer.objects.all()
    )

    class Meta:
        model = Payment
        fields = ['external_id', 'customer_external_id', 'total_amount', 'status']
        read_only_fields = ['status']

    def validate(self, data):
        """
        Validates the payment data before saving.
        Ensures the payment amount is positive and checks for active loans.
        """
        customer = data.get('customer')
        total_amount = data.get('total_amount')

        if total_amount <= 0:
            raise serializers.ValidationError(
                {"total_amount": "El monto debe ser mayor a cero."}
            )

        loans = Loan.objects.filter(customer=customer, status__in=[2])  # active loans
        total_outstanding = (
            loans.aggregate(total=Sum('outstanding')).get('total') or 0.0
        )

        if not loans.exists():
            raise serializers.ValidationError(
                {"customer_external_id": "El cliente no tiene préstamos activos."}
            )

        if total_amount <= total_outstanding:
            data['status'] = 1  # completed status
        else:
            data['status'] = 2  # rejected status

        return data

    def create(self, validated_data):
        """
        Creates a Payment object and applies the payment to active loans.
        """
        status = validated_data.get('status')
        payment = Payment.objects.create(**validated_data)

        if status == 1:
            customer = validated_data.get('customer')
            total_amount = validated_data.get('total_amount')
            loans = Loan.objects.filter(customer=customer, status__in=[2]).order_by(
                'created_at'
            )  # active loans ordered by creation date

            for loan in loans:
                if total_amount <= 0:
                    break

                amount = min(loan.outstanding, total_amount)
                loan.outstanding = loan.outstanding - amount
                total_amount = total_amount - amount

                PaymentDetail.objects.create(payment=payment, loan=loan, amount=amount)

                if loan.outstanding == 0:
                    loan.status = 4  # paid status

                loan.save()

        return payment


class PaymentsByCustomerSerializer(serializers.ModelSerializer):
    """
    Serializer for retrieving payment details by customer.
    Combines data from Payment and PaymentDetail models.
    """

    payment_external_id = serializers.CharField(source='payment.external_id')
    customer_external_id = serializers.CharField(source='payment.customer.external_id')
    loan_external_id = serializers.CharField(source='loan.external_id')
    payment_date = serializers.DateTimeField(source='payment.paid_at')
    status = serializers.IntegerField(source='payment.status')
    total_amount = serializers.DecimalField(
        source='payment.total_amount', max_digits=20, decimal_places=10
    )
    payment_amount = serializers.DecimalField(
        source='amount', max_digits=20, decimal_places=10
    )

    class Meta:
        model = PaymentDetail
        fields = [
            'payment_external_id',
            'customer_external_id',
            'loan_external_id',
            'payment_date',
            'status',
            'total_amount',
            'payment_amount',
        ]
        read_only_fields = [
            'payment_external_id',
            'customer_external_id',
            'loan_external_id',
            'payment_date',
            'status',
            'total_amount',
            'payment_amount',
        ]
