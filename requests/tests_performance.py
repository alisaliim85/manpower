from django.test import TestCase, Client
from django.test.utils import CaptureQueriesContext
from django.db import connection
from accounts.models import Company, User, Role
from vendors.models import Vendor, Worker
from requests.models import Request, RequestType
import time

class RequestListPerformanceTest(TestCase):
    def setUp(self):
        # Create Role
        self.admin_role, _ = Role.objects.get_or_create(code='admin', defaults={'name': 'Admin'})

        # Create Companies
        self.client_company = Company.objects.create(name='Client Co', company_type='client')
        self.vendor_company = Company.objects.create(name='Vendor Co', company_type='vendor')

        # Create Vendor profile
        self.vendor = Vendor.objects.create(company=self.vendor_company, contact_name='Vendor Contact')
        self.vendor.clients.add(self.client_company)

        # Create Users
        self.client_user = User.objects.create_user(username='client_user', password='password', company=self.client_company, role=self.admin_role)
        self.vendor_user = User.objects.create_user(username='vendor_user', password='password', company=self.vendor_company, role=self.admin_role)

        # Create Request Type
        self.req_type = RequestType.objects.create(name='Test Request', code='test-request')

        # Create 20 Workers and 20 Requests (Pagination is 5, so we see the first page)
        for i in range(20):
            worker = Worker.objects.create(
                vendor=self.vendor,
                full_name=f'Worker {i}',
                iqama_number=f'100000000{i}',
                nationality='Test',
                job_title='Test Job',
                iqama_expiry_date='2025-01-01',
                joined_at='2023-01-01'
            )
            Request.objects.create(
                request_type=self.req_type,
                worker=worker,
                created_by=self.client_user,
                status='submitted',
                current_company=self.vendor_company
            )

    def test_request_list_performance_client(self):
        client = Client()
        client.force_login(self.client_user)

        # Warm up
        client.get('/requests/')

        start_time = time.time()
        with CaptureQueriesContext(connection) as queries:
            response = client.get('/requests/')
        end_time = time.time()

        print(f"\n[Client User] Number of queries: {len(queries)}")
        print(f"[Client User] Execution time: {end_time - start_time:.4f} seconds")

        # Assertions to ensure it's working as expected
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['requests']), 5) # Pagination

    def test_request_list_performance_vendor(self):
        client = Client()
        client.force_login(self.vendor_user)

        # Warm up
        client.get('/requests/')

        start_time = time.time()
        with CaptureQueriesContext(connection) as queries:
            response = client.get('/requests/')
        end_time = time.time()

        print(f"\n[Vendor User] Number of queries: {len(queries)}")
        print(f"[Vendor User] Execution time: {end_time - start_time:.4f} seconds")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['requests']), 5) # Pagination
