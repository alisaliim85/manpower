from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, Company, Role
from vendors.models import Vendor, Worker
from requests.models import RequestType
from django.utils import timezone

class CreateRequestWizardTest(TestCase):
    def setUp(self):
        # 1. Create Role (optional but good practice if required)
        self.role = Role.objects.create(name="Admin", code="admin")

        # 2. Create Client Company
        self.client_company = Company.objects.create(
            name="Client Co",
            company_type="client"
        )

        # 3. Create User linked to Client Company
        self.client_user = User.objects.create_user(
            username="client_user",
            password="password",
            company=self.client_company,
            role=self.role
        )

        # 4. Create Vendor Company and Vendor Profile
        self.vendor_company = Company.objects.create(
            name="Vendor Co",
            company_type="vendor"
        )
        self.vendor = Vendor.objects.create(
            company=self.vendor_company,
            contact_name="Vendor Contact",
            contact_phone="123456789"
        )

        # Link Vendor to Client (Many-to-Many)
        self.vendor.clients.add(self.client_company)

        # 5. Create Worker
        self.worker = Worker.objects.create(
            vendor=self.vendor,
            full_name="John Doe",
            iqama_number="1234567890",
            nationality="N/A",
            job_title="Worker",
            insurance_class="vip",
            iqama_expiry_date=timezone.now().date(),
            joined_at=timezone.now().date()
        )

        # 6. Create Request Type
        self.request_type = RequestType.objects.create(
            name="Type A",
            code="type_a"
        )

        self.client = Client()

    def test_create_request_wizard_view(self):
        # Login
        self.client.login(username="client_user", password="password")

        # Access the view
        url = reverse('requests:create_wizard')
        response = self.client.get(url)

        # Assert status code 200
        self.assertEqual(response.status_code, 200)

        # Assert one of the context variables is present
        self.assertIn('form', response.context)
        self.assertIn('workers', response.context)
