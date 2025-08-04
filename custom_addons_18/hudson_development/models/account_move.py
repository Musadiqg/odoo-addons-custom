import requests
from datetime import date, datetime, time
from odoo import SUPERUSER_ID, _, api, fields, models
import json
import logging
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_srb = fields.Boolean(compute='check_account_type')
    bill = fields.Many2one('account.move',domain=[('move_type','=','in_invoice')])

    def check_account_type(self):
        for rec in self:
            if rec.line_ids.filtered(lambda x:x.account_id.is_srb_account):
                rec.is_srb = True
            else:
                rec.is_srb = False

    @api.model
    def create(self, vals_list):
        # Log initial line_ids for stock-related moves
        if vals_list.get('stock_move_id'):
            _logger.info(f"Odoo 18: Creating account.move for stock_move_id {vals_list['stock_move_id']}, line_ids: {vals_list.get('line_ids')}")
        
        for vals in vals_list:
            if not self.env.context.get('create_bill'):
                if type(vals) != str:
                    if vals.get('journal_id') == 242:
                        print()
                        #self.set_batch_Ref(vals)
                else:
                    if vals == 'journal_id':
                        if vals_list.get('journal_id') == 242:
                            print()
                            #self.set_batch_Ref(vals_list)

        if vals_list.get('stock_move_id'):
            stock_move_id = self.env['stock.move'].browse(vals_list['stock_move_id'])
            if stock_move_id.purchase_line_id and stock_move_id.picking_code == 'incoming':
                self.round_off(vals_list, stock_move_id)
                if stock_move_id.company_id.id == 5:
                    self.set_sale_tax(vals_list, stock_move_id)
                    _logger.info(f"Odoo 18: After set_sale_tax for stock_move_id {stock_move_id.id}, line_ids: {vals_list.get('line_ids')}")

        res = super(AccountMove, self).create(vals_list)
        _logger.info(f"Odoo 18: Created account.move ID {res.id} for stock_move_id {vals_list.get('stock_move_id', 'N/A')}")
        
        non_storable_lines = \
            res.invoice_line_ids. \
                filtered(lambda l: l.product_id.type != 'product'
                                and l.account_id == l.product_id.property_account_expense_id)
        if non_storable_lines:
            self.modify_bill_lines(non_storable_lines, res)
        if res.state == 'draft':
            res.sequence_number -= 1
            res.name = '/'
        if res.move_type == 'in_invoice' and res.company_id.id == 1:
            self.split_journal_items(res)
        if res.stock_move_id and res.stock_move_id.sale_line_id:
            analytic_distribution = {}
            if res.stock_move_id.sale_line_id.analytic_distribution:
                for key, percentage in res.stock_move_id.sale_line_id.analytic_distribution.items():
                    account_ids = [int(id_str) for id_str in key.split(',')]
                    for account_id in account_ids:
                        account = self.env['account.analytic.account'].browse(account_id)
                        if account.plan_id.id == 2:  # Former tags
                            analytic_distribution[str(account_id)] = percentage / len(account_ids)
            if analytic_distribution:
                self.set_analytic_tag(res, analytic_distribution)
        return res

    def split_journal_items(self, res):
        if res.line_ids:
            is_expense_acc_lines = res.line_ids.filtered(lambda l: l.account_id.internal_group == 'expense')
            sale_tax_input_line = res.line_ids.filtered(lambda l: l.account_id.is_sti_account)
            if is_expense_acc_lines and sale_tax_input_line:
                for line in is_expense_acc_lines:
                    # Get analytic_distribution for sale_tax_input_line
                    sale_tax_distribution = {}
                    if sale_tax_input_line.sale_line_id and sale_tax_input_line.sale_line_id.analytic_distribution:
                        for key, percentage in sale_tax_input_line.sale_line_id.analytic_distribution.items():
                            account_ids = [int(id_str) for id_str in key.split(',')]
                            for account_id in account_ids:
                                account = self.env['account.analytic.account'].browse(account_id)
                                if account.plan_id.id == 2:  # Former tags
                                    sale_tax_distribution[str(account_id)] = percentage / len(account_ids)
                    # Get analytic_distribution for line
                    line_distribution = {}
                    if line.sale_line_id and line.sale_line_id.analytic_distribution:
                        for key, percentage in line.sale_line_id.analytic_distribution.items():
                            account_ids = [int(id_str) for id_str in key.split(',')]
                            for account_id in account_ids:
                                account = self.env['account.analytic.account'].browse(account_id)
                                if account.plan_id.id == 2:  # Former tags
                                    line_distribution[str(account_id)] = percentage / len(account_ids)
                    vals = [{
                        'name': line.name,
                        'move_id': line.move_id.id,
                        'account_id': sale_tax_input_line.account_id.id,
                        'product_id': sale_tax_input_line.product_id.id,
                        'analytic_distribution': sale_tax_distribution,
                        'debit': 0.0,
                        'credit': sale_tax_input_line.debit,
                    }, {
                        'name': line.name,
                        'move_id': line.move_id.id,
                        'account_id': line.account_id.id,
                        'product_id': line.product_id.id,
                        'analytic_distribution': line_distribution,
                        'debit': sale_tax_input_line.debit,
                        'credit': 0.0,
                    }]
                    self.env['account.move.line'].create(vals)

    def set_analytic_tag(self, res, analytic_distribution):
        for line in res.line_ids:
            if not line.analytic_distribution:
                line.update({'analytic_distribution': analytic_distribution})

    def set_sale_tax(self, res, stock_move):
        if stock_move:
            product_id = stock_move.purchase_line_id.product_id.id
            price_subtotal = stock_move.quantity * stock_move.purchase_line_id.price_unit
            po_ref = stock_move.origin
            for line in res['line_ids']:
                _logger.info(f"Odoo 18: Processing line for product_id {product_id}: {line}")
                if line[2]['product_id'] == product_id:
                    if 'credit' not in line[2]:
                        _logger.warning(f"Odoo 18: Line missing 'credit' key: {line[2]}")
                    if 'debit' not in line[2]:
                        _logger.warning(f"Odoo 18: Line missing 'debit' key: {line[2]}")
                    try:
                        if line[2]['credit'] != 0:
                            line[2]['credit'] = price_subtotal * self.get_currency_rate(line[2])
                        if line[2]['debit'] != 0:
                            line[2]['debit'] = price_subtotal * self.get_currency_rate(line[2])
                    except KeyError as e:
                        _logger.error(f"Odoo 18: KeyError in set_sale_tax: {e}, line: {line[2]}")
                if "Return" in stock_move.display_name:
                    if 'credit' in line[2] and line[2]['credit'] != 0:
                        line[2]['debit'] = line[2]['credit']
                        line[2]['credit'] = 0
                    elif 'debit' in line[2] and line[2]['debit'] != 0:
                        line[2]['credit'] = line[2]['debit']
                        line[2]['debit'] = 0
                stock_move.stock_valuation_layer_ids.value = stock_move.stock_valuation_layer_ids.value * -1
                line[2]['name'] = po_ref + "-" + line[2]['name']

    def get_currency_rate(self, line):
        if line.get('currency_id'):
            currency = self.env['res.currency'].browse(line.get('currency_id'))
            if currency.name != 'PKR':
                return round(currency.inverse_rate, 2)
        else:
            return 1

    def round_off(self, res, stock_move_id):
        for tax in stock_move_id.purchase_line_id.taxes_id:
            if tax.amount_type == 'fixed':
                tax.amount = round(tax.amount, 2)

    def set_batch_Ref(self, vals):
        if vals.get('stock_move_id'):
            stock_move = self.env['stock.move'].browse(vals['stock_move_id'])
            if stock_move.picking_id and not stock_move.production_id:
                vals['ref'] = stock_move.picking_id.origin + "-" + vals['ref']

    def _run_batch_price_cron(self):
        date_begin = datetime(2022, 11, 1, 0, 0, 0)
        date_end = datetime.today()
        domain = [('amount_total', '!=', 0), ('pricelist_id.id', '=', 1), ('state', '=', 'sale'),
                  ('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        SOs = self.env['sale.order'].search(domain)
        list = []
        res = []
        counter = 0
        for rec in SOs:
            if "PS" not in rec.name and rec.invoice_count == 1:
                for sale_line in rec.order_line:
                    for move_id in sale_line.move_ids:
                        line = self.env['stock.move.line'].search([('move_id', '=', move_id.id)])
                        if len(line) == 1:
                            if round(sale_line.price_unit, 2) != round(line.lot_id.x_SalePrice, 2):
                                D = rec.id
                                if D not in list:
                                    list.append(D)
                                    x_price = round(line.lot_id.x_SalePrice, 2)
                                    sale_line.price_unit = x_price
                                    move = sale_line.invoice_lines.move_id
                                    move.button_draft()
                                    if len(sale_line.invoice_lines) > 1:
                                        print()
                                    line_id = move.invoice_line_ids.filtered(
                                        lambda l: l.id == sale_line.invoice_lines.id).id
                                    move.write({'invoice_line_ids': [(1, line_id, {'price_unit': x_price})]})
                                    move.action_post()
                        else:
                            counter += 1
                            ID = str(rec.id)
                            if ID not in res:
                                res.append(ID)

    def _run_adjust_entries_cron(self):
        november = datetime.strptime('2022-09-30', '%Y-%m-%d').date()
        Moves = self.env['account.move'].search([('create_uid', '=', 2),('date','>',november),('state','=','posted')])
        inv_entries = Moves.filtered(lambda move: 'Quantity Updated' in move.ref if move.ref else False)
        for entry in inv_entries:
            entry.button_draft()

    @api.depends('line_ids.amount_currency', 'line_ids.tax_base_amount', 'line_ids.tax_line_id', 'partner_id',
                 'currency_id', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals_json(self):
        """ Computed field used for custom widget's rendering.
            Only set on invoices.
        """
        for move in self:
            if not move.is_invoice(include_receipts=True):
                # Non-invoice moves don't support that field (because of multicurrency: all lines of the invoice share the same currency)
                move.tax_totals_json = None
                continue

            tax_lines_data = move._prepare_tax_lines_data_for_totals_from_invoice()

            move.tax_totals_json = json.dumps({
                **self._get_tax_totals(move.partner_id, tax_lines_data, round(move.amount_total, 0),
                                       round(move.amount_untaxed, 0), move.currency_id),
                'allow_tax_edition': move.is_purchase_document(include_receipts=False) and move.state == 'draft',
            })

    # @api.depends(
    #     'line_ids.matched_debit_ids.debit_move_id.payment_id.is_matched',
    #     'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
    #     'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
    #     'line_ids.matched_credit_ids.credit_move_id.payment_id.is_matched',
    #     'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
    #     'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
    #     'line_ids.debit',
    #     'line_ids.credit',
    #     'line_ids.currency_id',
    #     'line_ids.amount_currency',
    #     'line_ids.amount_residual',
    #     'line_ids.amount_residual_currency',
    #     'line_ids.payment_id.state',
    #     'line_ids.full_reconcile_id')
    # def _compute_amount(self):
        
    #     for move in self:

    #         if move.payment_state == 'invoicing_legacy':
    #             # invoicing_legacy state is set via SQL when setting setting field
    #             # invoicing_switch_threshold (defined in account_accountant).
    #             # The only way of going out of this state is through this setting,
    #             # so we don't recompute it here.
    #             move.payment_state = move.payment_state
    #             continue

    #         total_untaxed = 0.0
    #         total_untaxed_currency = 0.0
    #         total_tax = 0.0
    #         total_tax_currency = 0.0
    #         total_to_pay = 0.0
    #         total_residual = 0.0
    #         total_residual_currency = 0.0
    #         total = 0.0
    #         total_currency = 0.0
    #         currencies = move._get_lines_onchange_currency().currency_id

    #         for line in move.line_ids:
    #             if move.is_invoice(include_receipts=True):
    #                 # === Invoices ===

    #                 if not line.exclude_from_invoice_tab:
    #                     # Untaxed amount.
    #                     total_untaxed += line.balance
    #                     total_untaxed_currency += line.amount_currency
    #                     total += line.balance
    #                     total_currency += line.amount_currency
    #                 elif line.tax_line_id:
    #                     # Tax amount.
    #                     total_tax += line.balance
    #                     total_tax_currency += line.amount_currency
    #                     total += line.balance
    #                     total_currency += line.amount_currency
    #                 elif line.account_id.user_type_id.type in ('receivable', 'payable'):
    #                     # Residual amount.
    #                     total_to_pay += line.balance
    #                     total_residual += line.amount_residual
    #                     total_residual_currency += line.amount_residual_currency
    #             else:
    #                 # === Miscellaneous journal entry ===
    #                 if line.debit:
    #                     total += line.balance
    #                     total_currency += line.amount_currency

    #         if move.move_type == 'entry' or move.is_outbound():
    #             sign = 1
    #         else:
    #             sign = -1
    #         move.amount_untaxed = round(sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed),0)
    #         move.amount_tax = round(sign * (total_tax_currency if len(currencies) == 1 else total_tax),0)
    #         move.amount_total = round(sign * (total_currency if len(currencies) == 1 else total),0)
    #         move.amount_residual = round(-sign * (total_residual_currency if len(currencies) == 1 else total_residual),0)
    #         move.amount_untaxed_signed = round(-total_untaxed,0)
    #         move.amount_tax_signed = round(-total_tax,0)
    #         move.amount_total_signed = round(abs(total),0) if move.move_type == 'entry' else -total
    #         move.amount_residual_signed = round(total_residual,0)
    #         move.amount_total_in_currency_signed = round(abs(move.amount_total),0) if move.move_type == 'entry' else -(
    #                     sign * move.amount_total)

    #         currency = currencies if len(currencies) == 1 else move.company_id.currency_id

    #         # Compute 'payment_state'.
    #         new_pmt_state = 'not_paid' if move.move_type != 'entry' else False

    #         if move.is_invoice(include_receipts=True) and move.state == 'posted':
    #             if currency.is_zero(move.amount_residual):
    #                 reconciled_payments = move._get_reconciled_payments()
    #                 if not reconciled_payments or all(payment.is_matched for payment in reconciled_payments):
    #                     new_pmt_state = 'paid'
    #                 else:
    #                     new_pmt_state = move._get_invoice_in_payment_state()
    #             elif currency.compare_amounts(total_to_pay, total_residual) != 0:
    #                 new_pmt_state = 'partial'

    #         if new_pmt_state == 'paid' and move.move_type in ('in_invoice', 'out_invoice', 'entry'):
    #             reverse_type = move.move_type == 'in_invoice' and 'in_refund' or move.move_type == 'out_invoice' and 'out_refund' or 'entry'
    #             reverse_moves = self.env['account.move'].search(
    #                 [('reversed_entry_id', '=', move.id), ('state', '=', 'posted'), ('move_type', '=', reverse_type)])

    #             # We only set 'reversed' state in cas of 1 to 1 full reconciliation with a reverse entry; otherwise, we use the regular 'paid' state
    #             reverse_moves_full_recs = reverse_moves.mapped('line_ids.full_reconcile_id')
    #             if reverse_moves_full_recs.mapped('reconciled_line_ids.move_id').filtered(lambda x: x not in (
    #                     reverse_moves + reverse_moves_full_recs.mapped('exchange_move_id'))) == move:
    #                 new_pmt_state = 'reversed'

    #         move.payment_state = new_pmt_state
