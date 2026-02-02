from django.test import TestCase, Client
from django.test.utils import CaptureQueriesContext
from django.db import connection
from accounts.models import User, Company
from vendors.models import Vendor, Worker
from django.urls import reverse

class PerformanceBenchmark(TestCase):
    def setUp(self):
        # Create client company and user
        self.client_company = Company.objects.create(name="Client Co", company_type="client")
        self.user = User.objects.create_user(username="client", password="password", company=self.client_company)
        self.client = Client()
        self.client.force_login(self.user)

        # Create 20 vendors with 5 workers each
        for i in range(20):
            v_comp = Company.objects.create(name=f"Vendor {i}", company_type="vendor")
            vendor = Vendor.objects.create(company=v_comp, contact_name=f"C{i}", contact_phone="123")
            for j in range(5):
                Worker.objects.create(
                    vendor=vendor, full_name=f"W{i}-{j}", iqama_number=f"100{i}{j}",
                    nationality="N", job_title="J", insurance_class="c",
                    iqama_expiry_date="2025-01-01", joined_at="2024-01-01"
                )

    def test_dashboard_queries(self):
        url = reverse('client_dashboard')
        # Warmup request
        self.client.get(url)

        # Capture queries and assert count is low
        # We expect around 7 queries. Setting limit to 15 to be safe but catch N+1.
        with CaptureQueriesContext(connection) as ctx:
             response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertLess(len(ctx.captured_queries), 15, f"Expected < 15 queries, but got {len(ctx.captured_queries)}")
