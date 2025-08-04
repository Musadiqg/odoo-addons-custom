from datetime import date
from odoo.tools import float_round
from odoo import api, fields, models
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)
from odoo.tools.misc import formatLang, format_date

INV_LINES_PER_STUB = 9

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    is_commercial = fields.Boolean('Is Commercial import', default=False)

    def action_create_payments(self):
        _logger.debug("Calling action_create_payments with context: %s", self._context)
        payments = self._create_payments()
        _logger.debug("action_create_payments completed, payments created: %s", payments.ids)

        if self._context.get('dont_redirect_to_payments'):
            return True

        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })
        return action

    def _create_payments(self):
        self.ensure_one()
        batches = self.batches
        edit_mode = self.can_edit_wizard and (len(batches[0]['lines']) == 1 or self.group_payment)
        to_process = []

        if edit_mode:
            payment_vals = self._create_payment_vals_from_wizard(batches[0])
            payment_vals['x_original_amount'] = self.source_amount
            payment_vals['x_bills_count'] = len(batches[0]['lines'])
            if self.is_commercial:
                payment_vals.update({'is_commercial': self.is_commercial})
            payment_vals.update({'amount': round(self.amount, 0)})
            to_process.append({
                'create_vals': payment_vals,
                'to_reconcile': batches[0]['lines'],
                'batch': batches[0],
            })
        else:
            if not self.group_payment:
                new_batches = []
                for batch_result in batches:
                    for line in batch_result['lines']:
                        new_batches.append({
                            **batch_result,
                            'lines': line,
                        })
                batches = new_batches

            for batch_result in batches:
                payment_vals = self._create_payment_vals_from_batch(batch_result)
                payment_vals['x_original_amount'] = sum(abs(line.balance) for line in batch_result['lines'])
                payment_vals['x_bills_count'] = len(batch_result['lines'])
                if self.is_commercial and batch_result == batches[0]:
                    payment_vals.update({'is_commercial': self.is_commercial})
                if batch_result == batches[0]:
                    payment_vals.update({'amount': round(self.amount, 0)})
                to_process.append({
                    'create_vals': payment_vals,
                    'to_reconcile': batch_result['lines'],
                    'batch': batch_result,
                })

        payments = self._init_payments(to_process, edit_mode=edit_mode)
        self._post_payments(to_process, edit_mode=edit_mode)
        self._reconcile_payments(to_process, edit_mode=edit_mode)
        return payments

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    label_ref = fields.Char('Label', compute="get_label")
    is_commercial = fields.Boolean('Is Commercial import', default=False)
    wht_tax_amount = fields.Monetary('WHT Tax Amount', default=0.0)
    tax_move_ids = fields.Many2many('account.move', string='Tax Journal Entries')
    x_original_amount = fields.Monetary('Original Amount', default=0.0)
    x_bills_count = fields.Integer('Bills Count', default=0)

    @api.depends('reconciled_statement_line_ids')
    def get_label(self):
        for record in self:
            if record.reconciled_statement_line_ids:
                record.label_ref = record.reconciled_statement_line_ids[0].payment_ref
            else:
                record.label_ref = False

    def _check_fill_line(self, amount_str):
        return amount_str and (amount_str + ' ').ljust(200, '*') or ''

    def _check_build_page_info(self, i, p):
        multi_stub = self.company_id.account_check_printing_multi_stub
        check_amount_in_words = self.compute_check_amount_in_words()
        return {
            'sequence_number': self.check_number,
            'manual_sequencing': self.journal_id.check_manual_sequencing,
            'date': format_date(self.env, self.date),
            'partner_id': self.partner_id,
            'partner_name': self.partner_id.name,
            'currency': self.currency_id,
            'state': self.state,
            'amount': formatLang(self.env, round(self.amount, 0), currency_obj=self.currency_id) if i == 0 else 'VOID',
            'amount_in_word': self._check_fill_line(check_amount_in_words) if i == 0 else 'VOID',
            'memo': self.memo or self.move_id.ref or self.payment_reference or self.name,
            'stub_cropped': not multi_stub and len(self.move_id._get_reconciled_invoices()) > INV_LINES_PER_STUB,
            'stub_lines': p,
        }

    def compute_check_amount_in_words(self):
        for pay in self:
            if pay.currency_id:
                amount = float_round(pay.amount, precision_rounding=1)
                amount_str = pay.currency_id.amount_to_text(amount)
            return amount_str

    @api.model
    def create(self, vals_list):
        # Ensure x_original_amount is set for direct payments
        if 'x_original_amount' not in vals_list:
            vals_list['x_original_amount'] = vals_list.get('amount', 0.0)
        if 'x_bills_count' not in vals_list:
            vals_list['x_bills_count'] = 0  # Consistent with Odoo 15 for direct payments (no invoices)
        res = super(AccountPayment, self).create(vals_list)
        exemption = False
        today = date.today()
        if res.partner_id.exemption_date and res.partner_id.exemption_date > today:
            exemption = True
        if not res.is_commercial and not exemption:
            total_tax = self._calculate_wht_tax(res)
            res.wht_tax_amount = total_tax
            res.amount = res.x_original_amount - total_tax
        return res

    def _calculate_wht_tax(self, record):
        partner = record.partner_id
        fiscal_position = partner.x_studio_wht_position
        if not fiscal_position:
            return 0.0
        tax_ids = [tax for tax in fiscal_position.tax_ids if tax.x_studio_field_NJLfU < 0]
        payment_amount = record.x_original_amount
        bills_count = record.x_bills_count
        total_tax = 0.0
        for tax in tax_ids:
            tax_percentage = tax.x_studio_field_NJLfU
            if tax.tax_dest_id.amount_type == 'percent':
                tax_amount = abs(payment_amount * (tax_percentage / 100))
            elif tax.tax_dest_id.amount_type == 'fixed':
                tax_amount = abs(tax_percentage) * bills_count
            total_tax += tax_amount
        return total_tax

    def action_post(self):
        res = super(AccountPayment, self).action_post()
        if self.wht_tax_amount > 0:
            self._create_tax_jes()
        return res

    def _create_tax_jes(self):
        partner = self.partner_id
        fiscal_position = partner.x_studio_wht_position
        tax_ids = [tax for tax in fiscal_position.tax_ids if tax.x_studio_field_NJLfU < 0]
        payment_amount = self.x_original_amount
        bills_count = self.x_bills_count
        local_payable_account_id = partner.property_account_payable_id.id
        tax_moves = self.env['account.move']

        for tax in tax_ids:
            tax_percentage = tax.x_studio_field_NJLfU
            if tax.tax_dest_id.amount_type == 'percent':
                tax_amount = abs(payment_amount * (tax_percentage / 100))
            elif tax.tax_dest_id.amount_type == 'fixed':
                tax_amount = abs(tax_percentage) * bills_count
            tax_name = tax.tax_dest_id.name
            tax_account = next((line.account_id for line in tax.tax_dest_id.invoice_repartition_line_ids if line.account_id), None)
            if not tax_account:
                raise UserError(_("No account configured for tax %s") % tax_name)

            account_move = self.env['account.move'].create({
                'partner_id': self.partner_id.id,
                'journal_id': self.journal_id.id,
                'origin_payment_id': self.id,
                'x_studio_system_note': 'SGE',
                'move_type': 'entry',
            })

            self.env['account.move.line'].create([
                {
                    'name': tax_name,
                    'debit': 0,
                    'credit': tax_amount,
                    'account_id': tax_account.id,
                    'journal_id': self.journal_id.id,
                    'date': self.date,
                    'company_id': self.company_id.id,
                    'partner_id': self.partner_id.id,
                    'move_id': account_move.id,
                    'internal_note': 'SGE',
                    'ref': self.memo or self.move_id.ref or self.payment_reference or self.name,
                },
                {
                    'name': self.name,
                    'debit': tax_amount,
                    'credit': 0,
                    'account_id': local_payable_account_id,
                    'journal_id': self.journal_id.id,
                    'date': self.date,
                    'move_id': account_move.id,
                    'company_id': self.company_id.id,
                    'partner_id': self.partner_id.id,
                    'internal_note': 'SGE',
                    'ref': self.memo or self.move_id.ref or self.payment_reference or self.name,
                }
            ])
            account_move.action_post()
            tax_moves |= account_move

        self.tax_move_ids = [(6, 0, tax_moves.ids)]