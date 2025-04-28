from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from .serializer import (
    CustomerSerializer,
    LoanSerializer,
    PaymentSerializer,
    PaymentsByCustomerSerializer,
)
from .models import Customer, Loan, Payment, PaymentDetail

from decimal import Decimal
from drf_spectacular.utils import extend_schema


@extend_schema(tags=['Customers'])
class CustomerViewSet(viewsets.ModelViewSet):
    """
    Customer ViewSet

    Endpoints:
    - Retrieve customer details
    - Create new customers
    """

    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    lookup_field = 'external_id'
    http_method_names = ['get', 'post']

    @action(detail=True, methods=['get'], url_path='balance')
    def balance(self, request, external_id=None):
        """
        Retrieve Customer Balance

        Args:
        - request: HTTP request object.
        - external_id: Customer's external ID.

        Returns:
        - JSON response with balance details.
        """
        customer = self.get_object()
        total_debt = (
            Loan.objects.filter(customer=customer, status__in=[1, 2])
            .aggregate(total=Sum('outstanding'))
            .get('total')
            or 0.0
        )

        available_amount = Decimal(customer.score) - Decimal(total_debt)

        return Response(
            {
                "external_id": customer.external_id,
                "score": customer.score,
                "available_amount": available_amount,
                "total_debt": total_debt,
            }
        )


@extend_schema(tags=['Loans'])
class LoanViewSet(viewsets.ModelViewSet):
    """
    Loan ViewSet

    Endpoints:
    - Retrieve loan details
    - Create new loans
    """

    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    lookup_field = 'external_id'
    http_method_names = ['get', 'post']

    @action(
        detail=False,
        methods=['get'],
        url_path='by-customer/(?P<external_id>[a-zA-Z0-9_-]+)',
    )
    def get_loans_by_customer(self, request, external_id=None):
        """
        Fetches all loans for a specific customer.

        Args:
        - request: HTTP request object.
        - external_id: Customer's external ID.

        Returns:
        - JSON response with a list of loans.
        """
        loans = Loan.objects.filter(customer__external_id=external_id)
        serializer = self.get_serializer(loans, many=True)

        return Response(serializer.data)

    @extend_schema(request=None)
    @action(
        detail=True,
        methods=['post'],
        url_path='activate',
    )
    def activate(self, request, external_id=None):
        """
        Marks a loan as active and sets the 'taken_at' timestamp.

        Args:
        - request: HTTP request object.
        - external_id: Loan's external ID.

        Returns:
        - JSON response with updated loan details.
        """
        loan = self.get_object()
        loan.status = 2  # active
        loan.taken_at = timezone.now()
        loan.save()
        serializer = self.get_serializer(loan)

        return Response(serializer.data)


@extend_schema(tags=['Payments'])
class PaymentViewSet(viewsets.ModelViewSet):
    """
    Payment ViewSet

    Endpoints:
    - Retrieve payment details
    - Create new payments
    """

    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    lookup_field = 'external_id'
    http_method_names = ['get', 'post']

    @action(
        detail=False,
        methods=['get'],
        url_path='by-customer/(?P<external_id>[a-zA-Z0-9_-]+)',
    )
    def get_payments_by_customer(self, request, external_id=None):
        """
        Retrieve Payments by Customer

        Fetches all payment details for a specific customer.

        Args:
        - request: HTTP request object.
        - external_id: Customer's external ID.

        Returns:
        - JSON response with a list of payment details.
        """
        payment_details = PaymentDetail.objects.filter(
            payment__customer__external_id=external_id
        )

        serializer = PaymentsByCustomerSerializer(payment_details, many=True)
        return Response(serializer.data)
