from django.test import TestCase, Client
from django.urls import reverse
from django.db import connection
from django.test.utils import CaptureQueriesContext
from accounts.models import User, Company
from vendors.models import Vendor

class PerformanceWizardTests(TestCase):
    def setUp(self):
        # Create Client Company and User
        self.client_company = Company.objects.create(
            name="ClientCo",
            company_type='client',
            is_active=True
        )
        self.user = User.objects.create_user(
            username='client_user',
            password='password',
            company=self.client_company
        )

        # Create 5 Vendor Companies and Profiles, contracted to the Client
        for i in range(5):
            v_company = Company.objects.create(
                name=f"Vendor{i}",
                company_type='vendor',
                is_active=True
            )
            vendor = Vendor.objects.create(
                company=v_company,
                contact_name=f"Contact{i}",
                contact_phone="1234567890",
                is_active=True
            )
            vendor.clients.add(self.client_company)
            # IMPORTANT: Do NOT create any workers for these vendors.
            # This triggers the `if workers_test.count() == 0:` block in the view.

        self.client = Client()
        self.client.force_login(self.user)
        self.url = reverse('requests:create_wizard')

    def test_create_wizard_performance_no_workers(self):
        """
        Test the performance of the create wizard view when no workers are found.
        This triggers the debug code path which executes N+1 queries (or crashes).
        """
        # We expect a crash initially due to `v.worker_set` AttributeError.
        # If it doesn't crash, we expect high query count.

        try:
            with CaptureQueriesContext(connection) as ctx:
                response = self.client.get(self.url)

            # If we reach here, no crash occurred. Let's count queries.
            query_count = len(ctx.captured_queries)
            print(f"\n[BENCHMARK] Total Queries: {query_count}")
            for i, q in enumerate(ctx.captured_queries, 1):
                print(f"{i}. {q['sql']}")

            # Expected base queries:
            # 1. Session/User
            # 2. Company lookup
            # 3. RequestTypes
            # 4. Form/Template iteration over workers (which is empty query)
            # Approx 4-6 queries.

            # The debug code adds:
            # 1. workers_test.count()
            # 2. contracted_vendors query
            # 3. Loop over 5 vendors -> 5 queries (v.worker_set.count())
            # Total extra: 7 queries.

            # So if debug code is present, count > 10.
            # If optimized, count < 8.

            # Enforce strict query limit
            if query_count > 8:
                self.fail(f"Performance Regression: Too many queries ({query_count}). limit is 8.")

            # Also assert success
            self.assertEqual(response.status_code, 200)

        except AttributeError as e:
            if "'Vendor' object has no attribute 'worker_set'" in str(e):
                print("\n[CONFIRMED] Crash reproduced: AttributeError: 'Vendor' object has no attribute 'worker_set'")
                # We catch this to allow the test to 'pass' as a reproduction step,
                # but we fail the test to indicate the code is broken.
                self.fail("Code crashed with AttributeError as expected (reproduction successful). Fix required.")
            else:
                raise e
