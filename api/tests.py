from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from .models import Customer, Loan, PaymentDetail
from decimal import Decimal
from rest_framework_api_key.models import APIKey


class BaseTest(APITestCase):
    """
    Base test class to set up common test data and configurations.
    Provides reusable setup for customers, loans, payments.
    """

    def setUp(self):
        """
        Set up test data for customers, loans, and payments.
        """
        self.api_key, self.key = APIKey.objects.create_key(name="test-key")

        self.customer = Customer.objects.create(
            external_id='external_c01',
            score=1000,
        )

        self.loan_1 = Loan.objects.create(
            external_id='external_l01',
            customer=self.customer,
            amount=300,
            outstanding=300,
            status=2,  # active status
            taken_at=timezone.now(),
        )

        self.loan_2 = Loan.objects.create(
            external_id='external_l02',
            customer=self.customer,
            amount=300,
            outstanding=300,
            status=1,  # pending status
        )

        self.loan_3 = Loan.objects.create(
            external_id='external_l03',
            customer=self.customer,
            amount=200,
            outstanding=300,
            status=2,  # active status
            taken_at=timezone.now(),
        )

        self.secondary_customer = Customer.objects.create(
            external_id='external_c02',
            score=1000,
        )

        self.secondary_loan = Loan.objects.create(
            external_id='external_l04',
            customer=self.secondary_customer,
            amount=200,
            outstanding=500,
            status=2,  # active status
            taken_at=timezone.now(),
        )

    def get_headers(self):
        """
        Helper method to return authentication headers for API requests.
        """
        return {'Authorization': f'Api-Key {self.key}'}


class CustomerTests(BaseTest):
    """
    Test cases for Customer endpoints.
    """

    def test_create_customer(self):
        """
        Test creating a new customer.
        Verifies that the customer is created with the correct data.
        """
        data = {
            "external_id": "external_c00",
            "score": 1000,
        }

        url = reverse('customer-list')
        response = self.client.post(
            url, data, format='json', headers=self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['external_id'], data['external_id'])
        self.assertEqual(response.data['status'], 1)

    def test_get_customer(self):
        """
        Test retrieving a specific customer by external_id.
        Verifies that the correct customer data is returned.
        """
        customer = self.customer

        url = reverse('customer-detail', args=[customer.external_id])
        response = self.client.get(url, headers=self.get_headers())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['external_id'], customer.external_id)
        self.assertEqual(Decimal(response.data['score']), Decimal(customer.score))
        self.assertEqual(response.data['status'], customer.status)

    def test_get_customer_balance(self):
        """
        Test retrieving the balance of a customer.
        Verifies the total debt and available credit calculations.
        """
        customer = self.customer

        url = reverse('customer-balance', args=[customer.external_id])
        response = self.client.get(url, headers=self.get_headers())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['external_id'], customer.external_id)
        self.assertEqual(Decimal(response.data['score']), Decimal(customer.score))
        self.assertEqual(Decimal(response.data['available_amount']), 100)
        self.assertEqual(Decimal(response.data['total_debt']), 900)


class LoanTests(BaseTest):
    """
    Test cases for Loan endpoints.
    """

    def test_create_loan(self):
        """
        Test creating a new loan for a customer.
        Verifies that the loan is created with the correct data.
        """
        customer = self.customer

        data = {
            "external_id": "external_l00",
            "customer_external_id": customer.external_id,
            "amount": 100,
        }

        url = reverse('loan-list')
        response = self.client.post(
            url, data, format='json', headers=self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['external_id'], data['external_id'])
        self.assertEqual(Decimal(response.data['amount']), Decimal(data['amount']))
        self.assertEqual(Decimal(response.data['outstanding']), Decimal(data['amount']))
        self.assertEqual(response.data['status'], 1)

    def test_create_loan_exceeds_credit_limit(self):
        """
        Test creating a loan that exceeds the customer's credit limit.
        Verifies that the request is rejected with an appropriate error message.
        """
        customer = self.customer

        url = reverse('loan-list')
        data = {
            "external_id": "external_l05",
            "customer_external_id": customer.external_id,
            "amount": 200,
        }

        response = self.client.post(
            url, data, format='json', headers=self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('outstanding', response.data)
        self.assertIn(
            "El préstamo excede el límite de crédito disponible para el cliente.",
            response.data['outstanding'],
        )

    def test_get_loans_by_customer(self):
        """
        Test retrieving all loans associated with a specific customer.
        Verifies that the correct list of loans is returned.
        """
        customer = self.customer
        url = reverse('loan-get-loans-by-customer', args=[customer.external_id])
        response = self.client.get(url, headers=self.get_headers())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_activate_loan(self):
        """
        Test activating a pending loan.
        Verifies that the loan status is updated to 'active' and the taken_at timestamp is set.
        """
        loan = self.loan_2

        self.assertEqual(loan.status, 1)  # pending status
        self.assertIsNone(loan.taken_at)  # taken_at not set

        url = reverse('loan-activate', args=[loan.external_id])
        response = self.client.post(url, format='json', headers=self.get_headers())

        loan.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['external_id'], loan.external_id)
        self.assertEqual(response.data['status'], 2)  # active status
        self.assertIsNotNone(loan.taken_at)  # taken_at should be set

    def create_loan_with_invalid_amount(self):
        """
        Test creating loans with invalid amounts (zero or negative).
        Verifies that the request is rejected with appropriate error messages.
        """
        customer = self.customer

        # Create a loan with zero amount

        data = {
            "external_id": "external_l00",
            "customer_external_id": customer.external_id,
            "amount": 0,
        }

        url = reverse('loan-list')
        response = self.client.post(
            url, data, format='json', headers=self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount', response.data)
        self.assertIn("El monto debe ser mayor a cero.", response.data['amount'])

        # Create a loan with negative amount

        data = {
            "external_id": "external_l01",
            "customer_external_id": customer.external_id,
            "amount": -100,
        }

        url = reverse('loan-list')
        response = self.client.post(
            url, data, format='json', headers=self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount', response.data)


class PaymentTests(BaseTest):
    """
    Test cases for Payment endpoints.
    """

    def test_create_completed_payment(self):
        """
        Test creating a payment that successfully completes.
        Verifies that the payment is applied to active loans and updates their statuses.
        """
        customer = self.customer
        loan_1 = self.loan_1
        loan_2 = self.loan_2
        loan_3 = self.loan_3

        data = {
            "external_id": "external_p00",
            "customer_external_id": customer.external_id,
            "total_amount": 350,
        }

        url = reverse('payment-list')
        response = self.client.post(
            url, data, format='json', headers=self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['external_id'], data['external_id'])
        self.assertEqual(response.data['customer_external_id'], customer.external_id)
        self.assertEqual(
            Decimal(response.data['total_amount']), Decimal(data['total_amount'])
        )
        self.assertEqual(response.data['status'], 1)  # payment completed

        loan_1.refresh_from_db()
        loan_2.refresh_from_db()
        loan_3.refresh_from_db()

        self.assertEqual(loan_1.outstanding, 0)  # 300 - 300 = 0
        self.assertEqual(loan_2.outstanding, 300)  # not paid because loan is not active
        self.assertEqual(loan_3.outstanding, 250)  # 300 - 50 = 250

        self.assertEqual(loan_1.status, 4)  # paid status
        self.assertEqual(loan_2.status, 1)  # pending status
        self.assertEqual(loan_3.status, 2)  # active status

        payment_detail_loan_1 = PaymentDetail.objects.filter(
            payment__external_id=response.data['external_id'],
            loan__external_id=loan_1.external_id,
        ).first()

        payment_detail_loan_2 = PaymentDetail.objects.filter(
            payment__external_id=response.data['external_id'],
            loan__external_id=loan_2.external_id,
        ).first()

        payment_detail_loan_3 = PaymentDetail.objects.filter(
            payment__external_id=response.data['external_id'],
            loan__external_id=loan_3.external_id,
        ).first()

        self.assertEqual(payment_detail_loan_1.amount, 300)
        self.assertIsNone(payment_detail_loan_2)  # not paid because loan is not active
        self.assertEqual(payment_detail_loan_3.amount, 50)

    def test_create_rejected_payment(self):
        """
        Test creating a payment that gets rejected.
        Verifies that no loans are updated and the payment status is set to 'rejected'.
        """
        customer = self.customer
        loan_1 = self.loan_1
        loan_2 = self.loan_2
        loan_3 = self.loan_3

        data = {
            "external_id": "external_p00",
            "customer_external_id": customer.external_id,
            "total_amount": 700,
        }

        url = reverse('payment-list')
        response = self.client.post(
            url, data, format='json', headers=self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['external_id'], data['external_id'])
        self.assertEqual(response.data['customer_external_id'], customer.external_id)
        self.assertEqual(
            Decimal(response.data['total_amount']), Decimal(data['total_amount'])
        )
        self.assertEqual(response.data['status'], 2)  # payment rejected

        loan_1.refresh_from_db()
        loan_2.refresh_from_db()
        loan_3.refresh_from_db()

        self.assertEqual(loan_1.outstanding, 300)  # not paid
        self.assertEqual(loan_2.outstanding, 300)  # not paid
        self.assertEqual(loan_3.outstanding, 300)  # not paid

        self.assertEqual(loan_1.status, 2)  # active status
        self.assertEqual(loan_2.status, 1)  # pending status
        self.assertEqual(loan_3.status, 2)  # active status

        payment_detail_loan_1 = PaymentDetail.objects.filter(
            payment__external_id=response.data['external_id'],
            loan__external_id=loan_1.external_id,
        ).first()

        payment_detail_loan_2 = PaymentDetail.objects.filter(
            payment__external_id=response.data['external_id'],
            loan__external_id=loan_2.external_id,
        ).first()

        payment_detail_loan_3 = PaymentDetail.objects.filter(
            payment__external_id=response.data['external_id'],
            loan__external_id=loan_3.external_id,
        ).first()

        self.assertIsNone(payment_detail_loan_1)  # no payment detail created
        self.assertIsNone(payment_detail_loan_2)  # no payment detail created
        self.assertIsNone(payment_detail_loan_3)  # no payment detail created

    def test_get_payments_by_customer(self):
        """
        Test retrieving all payments associated with a specific customer.
        Verifies that the correct list of payment details is returned.
        """
        customer = self.customer

        data_1 = {
            "external_id": "external_p00",
            "customer_external_id": customer.external_id,
            "total_amount": 200,
        }

        data_2 = {
            "external_id": "external_p01",
            "customer_external_id": customer.external_id,
            "total_amount": 200,
        }

        url = reverse('payment-list')

        # Create first payment
        response_1 = self.client.post(
            url, data_1, format='json', headers=self.get_headers()
        )

        # Create second payment
        response_2 = self.client.post(
            url, data_2, format='json', headers=self.get_headers()
        )

        self.assertEqual(response_1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response_2.status_code, status.HTTP_201_CREATED)

        # Retrieve payments
        url = reverse('payment-get-payments-by-customer', args=[customer.external_id])
        response = self.client.get(url, headers=self.get_headers())

        '''
        Expected payment details:

        Payment 1: external_p00
            - loan_1: 300 - 200 = 100
        Payment 2: external_p01
            - loan_1: 100 - 100 = 0
            - loan_3: 300 - 100 = 200

        Note: loan_2 is not affected because it is pending
        '''

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_create_payment_with_invalid_amount(self):
        """
        Test creating payments with invalid amounts (zero or negative).
        Verifies that the request is rejected with appropriate error messages.
        """
        customer = self.customer

        # Create a payment with zero amount

        data = {
            "external_id": "external_p00",
            "customer_external_id": customer.external_id,
            "total_amount": 0,
        }

        url = reverse('payment-list')
        response = self.client.post(
            url, data, format='json', headers=self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('total_amount', response.data)
        self.assertIn(
            "El monto debe ser mayor a cero.",
            response.data['total_amount'],
        )

        # Create a payment with negative amount

        data = {
            "external_id": "external_p01",
            "customer_external_id": customer.external_id,
            "total_amount": -100,
        }

        url = reverse('payment-list')
        response = self.client.post(
            url, data, format='json', headers=self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('total_amount', response.data)

    def test_create_payment_with_invalid_customer(self):
        """
        Test creating a payment for a non-existent customer.
        Verifies that the request is rejected with an appropriate error message.
        """
        data = {
            "external_id": "external_p00",
            "customer_external_id": "external_c99",
            "total_amount": 100,
        }

        url = reverse('payment-list')
        response = self.client.post(
            url, data, format='json', headers=self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('customer_external_id', response.data)

    def test_create_payment_with_no_active_loans(self):
        """
        Test creating a payment when the customer has no active loans.
        Verifies that the request is rejected with an appropriate error message.
        """
        customer = self.customer
        loan_1 = self.loan_1
        loan_2 = self.loan_2
        loan_3 = self.loan_3

        # Pay off all active loans

        data = {
            "external_id": "external_p00",
            "customer_external_id": customer.external_id,
            "total_amount": 600,
        }

        url = reverse('payment-list')
        response = self.client.post(
            url, data, format='json', headers=self.get_headers()
        )

        loan_1.refresh_from_db()
        loan_2.refresh_from_db()
        loan_3.refresh_from_db()

        self.assertEqual(response.data['status'], 1)  # payment completed

        self.assertEqual(loan_1.outstanding, 0)  # paid off
        self.assertEqual(loan_2.outstanding, 300)  # not paid because loan is pending
        self.assertEqual(loan_3.outstanding, 0)  # paid off

        self.assertEqual(loan_1.status, 4)  # paid status
        self.assertEqual(loan_2.status, 1)  # pending status
        self.assertEqual(loan_3.status, 4)  # paid status

        payment_detail_loan_1 = PaymentDetail.objects.filter(
            payment__external_id=response.data['external_id'],
            loan__external_id=loan_1.external_id,
        ).first()

        payment_detail_loan_2 = PaymentDetail.objects.filter(
            payment__external_id=response.data['external_id'],
            loan__external_id=loan_2.external_id,
        ).first()

        payment_detail_loan_3 = PaymentDetail.objects.filter(
            payment__external_id=response.data['external_id'],
            loan__external_id=loan_3.external_id,
        ).first()

        self.assertEqual(payment_detail_loan_1.amount, 300)
        self.assertIsNone(payment_detail_loan_2)  # pending loan
        self.assertEqual(payment_detail_loan_3.amount, 300)

        # Create a new payment with no active loans

        data = {
            "external_id": "external_p01",
            "customer_external_id": customer.external_id,
            "total_amount": 600,
        }

        url = reverse('payment-list')
        response = self.client.post(
            url, data, format='json', headers=self.get_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('customer_external_id', response.data)
        self.assertIn(
            "El cliente no tiene préstamos activos.",
            response.data['customer_external_id'],
        )
