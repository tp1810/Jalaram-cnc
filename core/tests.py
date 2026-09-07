import datetime
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from jalaram_cnc import cli

from .models import Bill, BillItem, Expense


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


class ExpenseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.material = Expense.objects.create(
            title='Plywood material',
            amount=2500,
            notes='Workshop stock',
        )
        cls.electricity = Expense.objects.create(
            title='Electricity bill',
            amount=1200,
            notes='Monthly utility',
        )
        previous_month = timezone.now() - datetime.timedelta(days=35)
        Expense.objects.filter(pk=cls.electricity.pk).update(created_at=previous_month)
        cls.electricity.refresh_from_db()

    def test_create_expense_records_automatic_date(self):
        before = timezone.now()
        response = self.client.post(reverse('expense_create'), {
            'title': '  Tool repair  ',
            'amount': 750,
            'notes': 'Router service',
        })

        self.assertRedirects(response, reverse('expense_list'))
        expense = Expense.objects.get(title='Tool repair')
        self.assertEqual(expense.amount, 750)
        self.assertGreaterEqual(expense.created_at, before)

    def test_create_rejects_zero_amount(self):
        response = self.client.post(reverse('expense_create'), {
            'title': 'Invalid expense',
            'amount': 0,
        })

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'amount', 'Ensure this value is greater than or equal to 1.')

    def test_list_groups_expenses_by_month_and_calculates_total(self):
        response = self.client.get(reverse('expense_list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_expense'], 3700)
        self.assertEqual(response.context['expense_count'], 2)
        self.assertEqual(len(response.context['monthly_data']), 2)
        self.assertContains(response, 'Plywood material')
        self.assertContains(response, 'Electricity bill')

    def test_filters_by_search_amount_month_and_calendar_date(self):
        material_date = timezone.localtime(self.material.created_at)
        response = self.client.get(reverse('expense_list'), {
            'q': 'stock',
            'amount': '2500',
            'month': material_date.strftime('%Y-%m'),
            'date': material_date.strftime('%Y-%m-%d'),
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_expense'], 2500)
        self.assertEqual(response.context['expense_count'], 1)
        self.assertContains(response, 'Plywood material')
        self.assertNotContains(response, 'Electricity bill')

    def test_expense_delete_requires_post(self):
        delete_url = reverse('expense_delete', args=[self.material.pk])

        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Expense.objects.filter(pk=self.material.pk).exists())

        response = self.client.post(delete_url)
        self.assertRedirects(response, reverse('expense_list'))
        self.assertFalse(Expense.objects.filter(pk=self.material.pk).exists())


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