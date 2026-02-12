from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from accounts.models import Company
from vendors.models import Vendor, Worker
import datetime
from django.utils import timezone

User = get_user_model()

class VendorPerformanceTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Setup Client Company and User
        self.client_company = Company.objects.create(name="Client Co", company_type='client')
        self.user = User.objects.create_user(username='testclient', password='password', company=self.client_company)
        self.client.login(username='testclient', password='password')

    def create_vendors(self, count):
        for i in range(count):
            c = Company.objects.create(name=f"Vendor Co {i}", company_type='vendor')
            v = Vendor.objects.create(
                company=c,
                contact_name=f"Contact {i}",
                contact_phone=f"123{i}"
            )
            # Create a worker for each vendor
            Worker.objects.create(
                vendor=v,
                full_name=f"Worker {i}",
                iqama_number=f"1000{i}",
                nationality="KSA",
                job_title="Dev",
                insurance_class="vip",
                iqama_expiry_date=datetime.date.today() + datetime.timedelta(days=365),
                joined_at=datetime.date.today(),
                status='active'
            )

    def test_vendor_list_queries(self):
        # Create 10 vendors
        self.create_vendors(10)

        # Capture queries.
        # Expected with optimization: ~8 queries
        # 1-3: Auth/Session/Company
        # 4, 7: Pagination Counts
        # 5, 6: Notifications
        # 8: Main Vendor List (includes Company)

        with self.assertNumQueries(8):
            response = self.client.get(reverse('vendors:vendor_list'))
            self.assertEqual(response.status_code, 200)

    def test_worker_list_queries(self):
        # Create 10 workers (1 per vendor)
        self.create_vendors(10)

        # Capture queries.
        # Expected:
        # 1-3: Auth/Session/Company
        # 4: Total workers count (pagination)
        # 5: Active workers count
        # 6: Vacation workers count
        # 7-8: Notification context
        # 9: Worker List (select_related vendor__company)
        # Total: 9 queries.

        with self.assertNumQueries(9):
            response = self.client.get(reverse('vendors:worker_list'))
            self.assertEqual(response.status_code, 200)
