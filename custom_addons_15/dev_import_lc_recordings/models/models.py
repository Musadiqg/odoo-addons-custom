# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import groupby, float_is_zero


class ClearingCode(models.Model):
    _name = 'clearing.code'

    name = fields.Char("Code")


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    clearing_code = fields.Many2one('clearing.code', "Clearing Code")
    clearing_code_many = fields.Many2many('clearing.code', string="Clearing Codes")
    many = fields.Boolean('Many', default=False)

    @api.model
    def create(self, vals_list):
        res = super(AccountPayment, self).create(vals_list)
        if self.env.context.get('active_ids'):
            if len(self.env.context.get('active_ids')) > 1:
                res.many = True
                moves = self.env['account.move'].browse(self.env.context.get('active_ids'))
                # for move in moves:
                #     res.clearing_code_many = [(4, move.clearing_code.id)]
                #     self.update_code_in_move(res,move)
        if res.ref and res.clearing_code:
            res.update({'ref': res.ref + "-" + res.clearing_code.name})
        elif res.ref and res.clearing_code_many:
            res.update({'ref': res.ref + "-" + str(res.clearing_code_many.mapped('name'))})
        return res

    def update_code_in_move(self,res,move):
        if res.move_id:
            res.many = True
            res.move_id.clearing_code_many = [(4, move.clearing_code.id)]

class AccountMove(models.Model):
    _inherit = 'account.move'

    sub_partner = fields.Many2one('res.partner', string="Sub-Partner")
    clearing_code = fields.Many2one('clearing.code', "Clearing Code")
    clearing_code_many = fields.Many2many('clearing.code', string="Clearing Codes")
    many = fields.Boolean('Many', default=False)

    @api.model
    def create(self, vals_list):
        res = super(AccountMove, self).create(vals_list)
        if res.stock_move_id and res.stock_move_id.origin:
            if res.stock_move_id.picking_code == 'incoming' and 'PO' in res.stock_move_id.origin:
                res.clearing_code = res.stock_move_id.picking_id.clearing_code
            if self.env.context.get('active_ids'):
                if len(self.env.context.get('active_ids')) > 1:
                    res.many = True
        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    sub_partner_line = fields.Many2one('res.partner', string="Sub-Partner", related="move_id.sub_partner")
    clearing_code = fields.Many2one('clearing.code', "Clearing Code", related="move_id.clearing_code", store=True)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    clearing_code = fields.Many2one('clearing.code', "Clearing Code")

    @api.model
    def create(self, vals_list):
        currency_id = vals_list.get('currency_id')
        company_id = vals_list.get('company_id')
        clearing_code_id = vals_list.get('clearing_code')

        if currency_id and currency_id != 166:
            if not clearing_code_id:
                if company_id == 1:
                    code = self.env['ir.sequence'].next_by_code('clearing.code.hudson')
                elif company_id == 7:
                    code = self.env['ir.sequence'].next_by_code('clearing.code.innovitalabs')
                elif company_id == 8:
                    code = self.env['ir.sequence'].next_by_code('clearing.code.nd')
                else:
                    code = self.env['ir.sequence'].next_by_code('clearing.code.innovita')
                
                clearing_code = self.env['clearing.code'].create({'name': code})
                vals_list['clearing_code'] = clearing_code.id
            else:
                # Skip check if the clearing_code already exists in a draft or cancelled order
                existing_po = self.env['purchase.order'].search([
                    ('clearing_code', '=', clearing_code_id),
                    ('state', 'not in', ['draft', 'cancel'])
                ], limit=1)
                if existing_po:
                    raise ValidationError("Clearing code already in use in another Purchase Order: " + existing_po.name)

        return super(PurchaseOrder, self).create(vals_list)

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


class Picking(models.Model):
    _inherit = 'stock.picking'

    clearing_code = fields.Many2one('clearing.code', "Clearing Code")

    @api.model
    def create(self, vals_list):
        res = super(Picking, self).create(vals_list)
        if res.picking_type_code == 'incoming' and "PO" in res.origin:
            po = self.env['purchase.order'].search([('name', '=', res.origin)])
            res.update({"clearing_code": po.clearing_code.id})
        return res
