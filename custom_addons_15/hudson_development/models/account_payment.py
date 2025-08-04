from datetime import date
from odoo.tools import float_round
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError, ValidationError, _logger
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.tools.misc import formatLang, format_date

from odoo.tools import float_round

INV_LINES_PER_STUB = 9

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    is_commercial = fields.Boolean('Is Commercial import', default=False)

    def action_create_payments(self):
        payments = self._create_payments()

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
        batches = self._get_batches()
        edit_mode = self.can_edit_wizard and (len(batches[0]['lines']) == 1 or self.group_payment)
        to_process = []

        if edit_mode:
            payment_vals = self._create_payment_vals_from_wizard()
            to_process.append({
                'create_vals': payment_vals,
                'to_reconcile': batches[0]['lines'],
                'batch': batches[0],
            })
        else:
            # Don't group payments: Create one batch per move.
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
                to_process.append({
                    'create_vals': self._create_payment_vals_from_batch(batch_result),
                    'to_reconcile': batch_result['lines'],
                    'batch': batch_result,
                })
        if self.is_commercial:
            to_process[0]['create_vals'].update({'is_commercial':self.is_commercial})
        to_process[0]['create_vals'].update({'amount': round(self.amount, 0)})
        payments = self._init_payments(to_process, edit_mode=edit_mode)
        self._post_payments(to_process, edit_mode=edit_mode)
        self._reconcile_payments(to_process, edit_mode=edit_mode)
        return payments


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    label_ref = fields.Char('Label', compute="get_label")
    is_commercial = fields.Boolean('Is Commercial import', default=False)

    def get_label(self):
        for record in self:
            if record.reconciled_statement_ids:
                record.label_ref = record.reconciled_statement_ids.line_ids.payment_ref
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
            'amount': formatLang(self.env, round(self.amount,0), currency_obj=self.currency_id) if i == 0 else 'VOID',
            'amount_in_word': self._check_fill_line(check_amount_in_words) if i == 0 else 'VOID',
            'memo': self.ref,
            'stub_cropped': not multi_stub and len(self.move_id._get_reconciled_invoices()) > INV_LINES_PER_STUB,
            # If the payment does not reference an invoice, there is no stub line to display
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
        res = super(AccountPayment, self).create(vals_list)
        # res.amount = round(res.amount,0)
        exemption = False
        today = date.today()
        if res.partner_id.exemption_date:
            if res.partner_id.exemption_date > today:
                exemption = True
        if not res.is_commercial:
            if not exemption:
                self.WHT_automated_action(res)
        return res

    def WHT_automated_action(self, record):
        try:

            partner = record.partner_id

            fiscal_position = partner.x_studio_wht_position

            tax_ids = list(filter(lambda x: x['x_studio_field_NJLfU'] < 0, fiscal_position.tax_ids))

            payment_amount = record.amount

            local_payable_account_id = partner.property_account_payable_id.id

            total_tax = 0
            ctx = record.env.context
            if ctx.get('active_ids'):
                bills_count = len(ctx.get('active_ids'))
            for tax in tax_ids:
                tax_percentage = tax['x_studio_field_NJLfU']
                if tax.tax_dest_id.amount_type == 'percent':
                    tax_amount = abs(payment_amount * (tax_percentage / 100))
                elif tax.tax_dest_id.amount_type == 'fixed':
                    tax_amount = abs(tax_percentage) * bills_count
                tax_name = tax.tax_dest_id.name
                tax_account = list(filter(lambda x: x['account_id'], tax.tax_dest_id.invoice_repartition_line_ids))[
                    0].account_id
                total_tax += tax_amount
                # raise UserError(record.currency_id.id)

                account_move = self.env['account.move'].create({
                    'partner_id': record.partner_id.id,
                    'journal_id': record.journal_id.id,
                    'payment_id': record.id,
                    'x_studio_system_note': 'SGE',
                })

                move = self.env['account.move.line']

                move.create([{
                    'name': tax_name,
                    'debit': 0,
                    'credit': tax_amount,
                    'amount_currency': record.currency_id.id,
                    'company_currency_id': record.company_currency_id.id,
                    'account_id': tax_account.id,
                    'journal_id': record.journal_id.id,
                    'date': record.date,
                    'company_id': record.company_id.id,
                    'partner_id': record.partner_id.id,
                    'move_id': account_move.id,
                    'internal_note': 'SGE',
                    'ref': record.ref
                },
                    {
                        'name': record.name,
                        'debit': tax_amount,
                        'credit': 0,
                        'amount_currency': record.currency_id.id,
                        'company_currency_id': record.company_currency_id.id,
                        'account_id': local_payable_account_id,
                        'journal_id': record.journal_id.id,
                        'date': record.date,
                        'move_id': account_move.id,
                        'company_id': record.company_id.id,
                        'partner_id': record.partner_id.id,
                        'internal_note': 'SGE',
                        'ref': record.ref
                    }])

            record['amount'] = record.amount - total_tax

        except Exception as e:

            raise UserError(e)
