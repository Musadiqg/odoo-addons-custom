# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import groupby, float_is_zero
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    bills_count = fields.Integer('Bills', compute="get_bills_count")

    def get_bills_count(self):
        for rec in self:
            move = self.env['account.move'].search([('ref', 'like', rec.name)])
            rec.bills_count = len(move)

    def action_get_bill_view(self):
        self.ensure_one()
        move = self.env['account.move'].search([('ref', 'like', self.name)])
        result = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "domain": [('id', 'in', move.ids)],
            "context": {"create": False},
            "name": "Customer Invoices",
            'view_mode': 'tree,form',
        }
        return result

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if res == True and self.purchase_id.order_line.filtered(lambda l: l.product_id.detailed_type != 'product'):
            if not self.purchase_id.enable_grn:
                self.create_account_move()
        return res

    def create_account_move(self):
        vals = {'ref': self.name, 'date': self.date_done, 'journal_id': 221}
        if self.purchase_id.company_id.id == 1:
            vals.update({'journal_id':166})
        elif self.purchase_id.company_id.id == 7:
            vals.update({'journal_id':445})
        elif self.purchase_id.company_id.id == 8:
            vals.update({'journal_id':693})

        move = self.env['account.move'].create(vals)
        list = []
        credit = 0

        # Calculating Expense Lines
        for line in self.purchase_id.order_line.filtered(lambda l: l.product_id.detailed_type != 'product'):
            # qty = sum(self.move_line_ids.filtered(lambda l:l.product_id.id == line.product_id.id).mapped('qty_done'))
            # qty = line.qty_received if line.qty_received != 0 else line.product_qty
            qty = line.product_qty
            amount = (line.price_unit * qty) + line.price_tax if self.company_id.id == 1 else line.price_unit * qty
            expense_lines = {
                'account_id': line.product_id.property_account_expense_id.id,
                'product_id': line.product_id.id,
                'partner_id': self.partner_id.id,
                'move_id': move.id,
                'debit': amount if "Return" not in self.origin else 0,
                'analytic_tag_ids': line.analytic_tag_ids.ids,
                'analytic_account_id': line.account_analytic_id.id,
                'credit': 0 if "Return" not in self.origin else amount}
            credit += line.price_unit * qty
            list.append(expense_lines)

        # Taxlines for Hudson
        if self.company_id.id == 1:
            if not self.partner_id.property_account_position_id:
                raise ValidationError('Vendor Fiscal not found')

            for line in self.purchase_id.order_line.filtered(lambda l: l.product_id.detailed_type != 'product'):
                if len(line.taxes_id) > 1:
                    raise ValidationError('Multiple Taxes found ! Please contact Finance')
                account_id = line.taxes_id.invoice_repartition_line_ids.filtered(lambda l: l.account_id).account_id.id
                # qty = sum(self.move_line_ids.filtered(lambda l:l.product_id.id == line.product_id.id).mapped('qty_done'))
                # qty = line.qty_received if line.qty_received != 0 else line.product_qty
                qty = line.product_qty
                if not account_id:
                    raise ValidationError('Tax account not found')
                amount = (line.price_unit * qty)
                tax_amount = abs(amount * (line.taxes_id.amount / 100))
                tax_line = {
                    'account_id': account_id,
                    'product_id': line.product_id.id,
                    'partner_id': self.partner_id.id,
                    'analytic_tag_ids': line.analytic_tag_ids.ids,
                    'analytic_account_id': line.account_analytic_id.id,
                    'move_id': move.id,
                    'debit': 0,
                    'credit': tax_amount
                }
                list.append(tax_line)

        # GRIR

        for line in self.purchase_id.order_line.filtered(lambda l: l.product_id.detailed_type != 'product'):
            # qty = sum(self.move_line_ids.filtered(lambda l:l.product_id.id == line.product_id.id).mapped('qty_done'))
            # qty = line.qty_received if line.qty_received != 0 else line.product_qty
            qty = line.product_qty
            line.qty_received = qty
            if self.company_id.id == 1:
                amount = (line.price_unit * qty)
                account_id = 2343
            
            elif self.company_id.id == 7:
                account_id = 4782  # Updated account_id for innovita 7
                amount = (line.price_unit * qty)

            elif self.company_id.id == 8:
                account_id = 5149  # Updated account_id for innovita 7
                amount = (line.price_unit * qty)

            else:
                account_id = 3923
                amount = (line.price_unit * qty)
            tax_amount = abs(amount * (line.taxes_id.amount / 100))
            grir = {'account_id': account_id,
                    'product_id': line.product_id.id,
                    'partner_id': self.partner_id.id,
                    'analytic_tag_ids': line.analytic_tag_ids.ids,
                    'analytic_account_id': line.account_analytic_id.id,
                    'move_id': move.id,
                    'debit': 0 if "Return" not in self.origin else amount,
                    'credit': amount if "Return" not in self.origin else 0}
            list.append(grir)
        self.env['account.move.line'].create(list)
        # if self.purchase_id.order_line.filtered(lambda l: l.product_id.detailed_type != 'product'):
        #     for line in self.purchase_id.order_line:
        #         line.qty_received = qty
        move.action_post()


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('product_id')
    def _compute_qty_received_method(self):
        for line in self:
            if line.product_id and line.product_id.type in ['consu', 'service']:
                line.qty_received_method = 'manual'
            else:
                line.qty_received_method = False


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    enable_grn = fields.Boolean("Disable GRN for Non-Storable Items?")

    @api.depends('order_line.invoice_lines.move_id')
    def _compute_invoice(self):
        for order in self:
            invoices = order.mapped('order_line.invoice_lines.move_id') or self.env['account.move'].search(
                [('invoice_origin', '=', order.name)])
            order.invoice_ids = invoices
            order.invoice_count = len(invoices)

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        picking = self.env['stock.picking'].search([('purchase_id', '=', self.id)], limit=1, order='id desc')
        if picking:
            if len(self.order_line) != len(picking.move_line_ids_without_package):
                product_ids = picking.move_line_ids_without_package.mapped('product_id.id')
                exclude_line = self.order_line.filtered(
                    lambda l: l.product_id.id not in product_ids and l.product_id.detailed_type != 'product')
                if exclude_line:
                    stock_move_obj = self.env['stock.move']
                    for line in exclude_line:
                        move = {'name': picking.name, 'product_id': line.product_id.id,
                                'product_uom_qty': line.product_uom_qty, 'picking_id': picking.id,
                                'quantity_done': line.product_uom_qty, 'product_uom': line.product_id.uom_id.id,
                                'location_id': picking.location_id.id, 'location_dest_id': picking.location_dest_id.id}
                        stock_move_obj.create(move)
                    picking.state = 'assigned'
        return True

    def action_create_invoice(self):
        """Create the invoice associated to the PO.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        # 1) Prepare invoice vals and clean-up the section lines
        invoice_vals_list = []
        for order in self:
            if order.invoice_status != 'to invoice':
                continue

            order = order.with_company(order.company_id)
            pending_section = None
            # Invoice values.
            invoice_vals = order._prepare_invoice()
            # Invoice line values (keep only necessary sections).
            for line in order.order_line:
                if line.display_type == 'line_section':
                    pending_section = line
                    continue

                if line.product_id.detailed_type != 'product':
                    if not self.enable_grn:
                        line.qty_invoiced = line.qty_received
                        if line.product_id.purchase_method == 'purchase':
                            line.qty_to_invoice = line.product_qty - line.qty_invoiced
                        else:
                            line.qty_to_invoice = line.qty_received - line.qty_invoiced
                if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    if pending_section:
                        invoice_vals['invoice_line_ids'].append((0, 0, pending_section._prepare_account_move_line()))
                        pending_section = None
                    invoice_vals['invoice_line_ids'].append((0, 0, line._prepare_account_move_line()))
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise UserError(
                _('There is no invoiceable line. If a product has a control policy based on received quantity, please make sure that a quantity has been received.'))

        # 2) group by (company_id, partner_id, currency_id) for batch creation
        new_invoice_vals_list = []
        for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (
                x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
            origins = set()
            payment_refs = set()
            refs = set()
            ref_invoice_vals = None
            for invoice_vals in invoices:
                if not ref_invoice_vals:
                    ref_invoice_vals = invoice_vals
                else:
                    ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                origins.add(invoice_vals['invoice_origin'])
                payment_refs.add(invoice_vals['payment_reference'])
                refs.add(invoice_vals['ref'])
            ref_invoice_vals.update({
                'ref': ', '.join(refs)[:2000],
                'invoice_origin': ', '.join(origins),
                'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
            })
            new_invoice_vals_list.append(ref_invoice_vals)
        invoice_vals_list = new_invoice_vals_list

        # 3) Create invoices.
        moves = self.env['account.move']
        AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
        for vals in invoice_vals_list:
            moves |= AccountMove.with_company(vals['company_id']).create(vals)

        # 4) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
        moves.filtered(
            lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()

        if moves:
            if self._name == 'purchase.order':
                for move in moves:
                    move.clearing_code = self.clearing_code
        return self.action_view_invoice(moves)


class AccountMove(models.Model):
    _inherit = 'account.move'

    pass_entry = fields.Boolean("Pass")

    def modify_bill_lines(self,non_storable_lines,res):
        # unlink extra lines
        purchase_id = False
        if res.invoice_origin:
            purchase_id = self.env['purchase.order'].search([('name', '=', res.invoice_origin)])
        elif self.env.context.get('active_model') == 'purchase.order':
            purchase_id = self.env['purchase.order'].browse(self.env.context.get('active_id'))
        elif res.ref:
            origin = self.env['stock.picking'].search([('name', '=', res.ref)]).origin
            if origin:
                purchase_id = self.env['purchase.order'].search([('name', '=', origin)])
        if purchase_id and not purchase_id.enable_grn:
            if non_storable_lines:
                res.pass_entry = True
                non_storable_lines.unlink()
            list = []
            # creating GRIR for non-storable product lines
            for line in purchase_id.order_line.filtered(lambda l: l.product_id.detailed_type != 'product'):
                # qty = purchase_id.order_line.move_ids.filtered(lambda l:l.state == 'done').filtered(lambda l: l.product_id.id == line.product_id.id).quantity_done
                qty = line.qty_received
                amount = line.price_unit * qty
                tax_amount = abs(amount * (line.taxes_id.amount / 100))

                if purchase_id.company_id.id == 1:
                    grir_account = 2343
                elif purchase_id.company_id.id == 7:
                    grir_account = 4782
                elif purchase_id.company_id.id == 8:
                    grir_account = 5149
                else:
                    grir_account = 3923

                grir = {'account_id': grir_account,
                        'product_id': line.product_id.id,
                        'partner_id': purchase_id.partner_id.id,
                        'analytic_tag_ids': line.analytic_tag_ids.ids,
                        'analytic_account_id': line.account_analytic_id.id,
                        'tax_ids': line.taxes_id.ids,
                        'move_id': res.id,
                        'quantity':qty,
                        'tax_ids': line.taxes_id.ids,
                        'debit': amount,
                        'credit': 0}
                list.append(grir)
            # Taxlines for Hudson
            taxes = []
            total_minus_tax = 0
            if purchase_id.company_id.id == 1:
                if not purchase_id.partner_id.property_account_position_id:
                    raise ValidationError('Vendor Fiscal not found')

                for line in purchase_id.order_line.filtered(lambda l: l.product_id.detailed_type != 'product'):
                    account_id = line.taxes_id.invoice_repartition_line_ids.filtered(
                        lambda l: l.account_id).account_id.id
                    if not account_id:
                        raise ValidationError('Tax account not found')
                    amount = line.price_unit * qty
                    tax_amount = abs(amount * (line.taxes_id.amount / 100))
                    tax_line = {
                        'account_id': account_id,
                        'product_id': line.product_id.id,
                        'partner_id': purchase_id.partner_id.id,
                        'analytic_tag_ids': line.analytic_tag_ids.ids,
                        'analytic_account_id': line.account_analytic_id.id,
                        'tax_ids':line.taxes_id.ids,
                        'move_id': res.id,
                        'tax_ids':line.taxes_id.ids,
                        'quantity':qty,
                        'debit': 0,
                        'credit': tax_amount
                    }
                    taxes.append(tax_line)
                    total_minus_tax += tax_amount
            
            self.env['account.move.line'].create(list)
            for line in purchase_id.order_line:
                line.qty_to_invoice = line.product_qty - line.qty_received
                line.qty_invoiced = line.qty_received

    def _check_balanced(self):
        ''' Assert the move is fully balanced debit = credit.
        An error is raised if it's not the case.
        '''
        moves = self.filtered(lambda move: move.line_ids)
        if not moves:
            return

        # /!\ As this method is called in create / write, we can't make the assumption the computed stored fields
        # are already done. Then, this query MUST NOT depend of computed stored fields (e.g. balance).
        # It happens as the ORM makes the create with the 'no_recompute' statement.
        self.env['account.move.line'].flush(self.env['account.move.line']._fields)
        self.env['account.move'].flush(['journal_id'])
        self._cr.execute('''
            SELECT line.move_id, ROUND(SUM(line.debit - line.credit), currency.decimal_places)
            FROM account_move_line line
            JOIN account_move move ON move.id = line.move_id
            JOIN account_journal journal ON journal.id = move.journal_id
            JOIN res_company company ON company.id = journal.company_id
            JOIN res_currency currency ON currency.id = company.currency_id
            WHERE line.move_id IN %s
            GROUP BY line.move_id, currency.decimal_places
            HAVING ROUND(SUM(line.debit - line.credit), currency.decimal_places) != 0.0;
        ''', [tuple(self.ids)])


        query_res = self._cr.fetchall()
        if query_res:
            threshold = 0.01
            ids = []
            sums = []

            for res in query_res:
                move_id = res[0]
                difference = res[1]
                if abs(difference) > threshold:
                    ids.append(move_id)
                    sums.append(difference)

            # Only raise error if any move with large difference AND pass_entry is False
            moves_with_issue = self.filtered(lambda m: m.id in ids and not m.pass_entry)
            if moves_with_issue:
                raise UserError(_("Cannot create unbalanced journal entry. Ids: %s\nDifferences debit - credit: %s") % (ids, sums))

