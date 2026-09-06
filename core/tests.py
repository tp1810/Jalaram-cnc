from pathlib import Path
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from jalaram_cnc import cli

from .models import Bill, BillItem


class UnpaidBillsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unpaid_bill = Bill.objects.create(
            customer_name='Search Customer',
            customer_phone='9876543210',
            customer_city='Kapadwanj',
            paid_amount=25,
        )
        BillItem.objects.create(
            bill=cls.unpaid_bill,
            description='Panel',
            size='12x12',
            quantity=1,
            amount=100,
        )
        cls.paid_bill = Bill.objects.create(
            customer_name='Paid Customer',
            customer_phone='9999999999',
            customer_city='Kapadwanj',
            paid_amount=100,
        )
        BillItem.objects.create(
            bill=cls.paid_bill,
            description='Frame',
            size='10x10',
            quantity=1,
            amount=100,
        )

    def test_page_contains_live_search_and_date_filter(self):
        response = self.client.get(reverse('unpaid_bills'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="unpaidLiveSearch"')
        self.assertContains(response, 'id="unpaidDateFilter"')
        self.assertContains(response, 'data-bill-date=')
        self.assertContains(response, 'Search Customer')
        self.assertNotContains(response, 'Paid Customer')

    def test_live_search_matches_name_phone_and_bill_number(self):
        search_url = reverse('live_search_unpaid_bills')

        for query in ('Search', '9876543210', str(self.unpaid_bill.bill_number)):
            with self.subTest(query=query):
                response = self.client.get(search_url, {'q': query})
                results = response.json()['results']
                self.assertEqual([result['id'] for result in results], [self.unpaid_bill.id])

    def test_live_search_excludes_fully_paid_bills(self):
        response = self.client.get(
            reverse('live_search_unpaid_bills'),
            {'q': 'Paid Customer'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['results'], [])


class ServiceStartupTests(TestCase):
    def test_serve_starts_backup_worker_before_waitress(self):
        events = []
        with (
            patch.object(cli, 'ensure_configuration'),
            patch.object(cli, 'start_backup_worker', side_effect=lambda: events.append('backup-worker')),
            patch('scripts.start_server.run_server', side_effect=lambda: events.append('waitress')),
        ):
            cli.serve()

        self.assertEqual(events, ['backup-worker', 'waitress'])

    def test_backup_if_needed_runs_only_without_recent_backup(self):
        with (
            patch.object(cli, 'DB_PATH', Path(__file__)),
            patch('scripts.backup.recent_valid_backup_exists', return_value=False),
            patch('scripts.backup.run_backup') as run_backup,
        ):
            self.assertTrue(cli.backup_if_needed())
            run_backup.assert_called_once_with()

        with (
            patch.object(cli, 'DB_PATH', Path(__file__)),
            patch('scripts.backup.recent_valid_backup_exists', return_value=True),
            patch('scripts.backup.run_backup') as run_backup,
        ):
            self.assertFalse(cli.backup_if_needed())
            run_backup.assert_not_called()