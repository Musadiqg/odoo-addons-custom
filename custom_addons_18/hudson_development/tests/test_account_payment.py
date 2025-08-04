from odoo.tests import common
from odoo import fields
from datetime import date

class TestAccountPayment(common.TransactionCase):
    def setUp(self):
        super().setUp()
        # Create test data
        self.account_payable = self.env['account.account'].search([('code', '=', '200000')], limit=1)
        if not self.account_payable:
            self.account_payable = self.env['account.account'].create({
                'name': 'Test Payable',
                'code': '200000',
                'account_type': 'liability_payable',
            })
        
        self.tax_account = self.env['account.account'].search([('code', '=', '300000')], limit=1)
        if not self.tax_account:
            self.tax_account = self.env['account.account'].create({
                'name': 'Test Tax Account',
                'code': '300000',
                'account_type': 'liability_current',
            })

        self.tax = self.env['account.tax'].create({
            'name': 'Test WHT 5%',
            'amount_type': 'percent',
            'amount': 5.0,
            'invoice_repartition_line_ids': [(0, 0, {
                'factor_percent': 100,
                'account_id': self.tax_account.id,
            })],
        })

        self.fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'Test WHT Position',
            'tax_ids': [(0, 0, {
                'x_studio_field_NJLfU': -5.0,
                'tax_dest_id': self.tax.id,
            })],
        })

        self.partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'property_account_payable_id': self.account_payable.id,
            'x_studio_wht_position': self.fiscal_position.id,
        })

        self.journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
        if not self.journal:
            self.journal = self.env['account.journal'].create({
                'name': 'Test Bank Journal',
                'code': 'BNK1',
                'type': 'bank',
            })

        self.payment_vals = {
            'partner_id': self.partner.id,
            'amount': 1250.0,
            'journal_id': self.journal.id,
            'payment_type': 'outbound',
            'date': fields.Date.today(),
            'x_original_amount': 1250.0,
            'x_bills_count': 1,
        }

    def test_wht_calculation(self):
        """Test WHT calculation and amount adjustment."""
        payment = self.env['account.payment'].create(self.payment_vals)
        self.assertEqual(payment.wht_tax_amount, 62.0, "WHT should be 5% of 1250")
        self.assertEqual(payment.amount, 1187.0, "Amount should be 1250 - 62")

    def test_tax_je_creation(self):
        """Test main and tax JE creation on posting."""
        payment = self.env['account.payment'].create(self.payment_vals)
        payment.action_post()
        self.assertTrue(payment.move_id, "Main JE should be created")
        self.assertEqual(payment.move_id.amount_total, 1187.0, "Main JE amount should be 1187")
        self.assertTrue(payment.tax_move_ids, "Tax JEs should be created")
        self.assertEqual(len(payment.tax_move_ids), 1, "One tax JE expected")
        tax_je = payment.tax_move_ids
        self.assertEqual(tax_je.amount_total, 62.0, "Tax JE amount should be 62")

    def test_no_wht_commercial(self):
        """Test payment with no WHT (commercial import)."""
        commercial_vals = self.payment_vals.copy()
        commercial_vals['is_commercial'] = True
        payment = self.env['account.payment'].create(commercial_vals)
        self.assertEqual(payment.wht_tax_amount, 0.0, "No WHT for commercial payment")
        self.assertEqual(payment.amount, 1250.0, "Amount should not be adjusted")

    def test_exempt_partner(self):
        """Test payment with exempt partner."""
        exempt_partner = self.partner.copy({
            'exemption_date': fields.Date.today() + fields.Date.timedelta(days=1),
        })
        exempt_vals = self.payment_vals.copy()
        exempt_vals['partner_id'] = exempt_partner.id
        payment = self.env['account.payment'].create(exempt_vals)
        self.assertEqual(payment.wht_tax_amount, 0.0, "No WHT for exempt partner")
        self.assertEqual(payment.amount, 1250.0, "Amount should not be adjusted")