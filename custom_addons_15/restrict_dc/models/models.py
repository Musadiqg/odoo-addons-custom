# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"
    _description = "Sales Advance Payment Invoice"

    def create_invoices(self):
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
        if self.advance_payment_method == 'delivered':
            sale_orders._create_invoices(final=self.deduct_down_payments)
        else:
            # Create deposit product if necessary
            if not self.product_id:
                vals = self._prepare_deposit_product()
                self.product_id = self.env['product.product'].create(vals)
                self.env['ir.config_parameter'].sudo().set_param('sale.default_deposit_product_id', self.product_id.id)

            sale_line_obj = self.env['sale.order.line']
            for order in sale_orders:
                amount, name = self._get_advance_details(order)

                if self.product_id.invoice_policy != 'order':
                    raise UserError(
                        _('The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.'))
                if self.product_id.type != 'service':
                    raise UserError(
                        _("The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product."))
                taxes = self.product_id.taxes_id.filtered(
                    lambda r: not order.company_id or r.company_id == order.company_id)
                tax_ids = order.fiscal_position_id.map_tax(taxes).ids
                analytic_tag_ids = []
                for line in order.order_line:
                    analytic_tag_ids = [(4, analytic_tag.id, None) for analytic_tag in line.analytic_tag_ids]

                so_line_values = self._prepare_so_line(order, analytic_tag_ids, tax_ids, amount)
                so_line = sale_line_obj.create(so_line_values)
                self._create_invoice(order, so_line, amount)
        print()
        if self._context.get('open_invoices', False):
            return sale_orders.action_view_invoice()
        return {'type': 'ir.actions.act_window_close'}


class AccountMove(models.Model):
    _inherit = 'account.move'

    stock_pickings = fields.Many2many('stock.picking', string="DCs", domain='[("picking_type_id", "in", [54,11,2])]')
    is_dist_inv = fields.Boolean('Distribute Invoice',compute='get_eval')

    def get_eval(self):
        for rec in self:
            rec.is_dist_inv = False
            if rec.invoice_origin:
                if 'SO' in rec.invoice_origin:
                    rec.is_dist_inv = True
                else:
                    rec.is_dist_inv = False

    def action_post(self):
        res = super(AccountMove, self).action_post()
        if self.stock_pickings:
            if self.invoice_origin:
                if "SO" in self.invoice_origin:
                    sale_order = self.env['sale.order'].search([('name','=',self.invoice_origin)],limit=1)
                    if sale_order:
                        for picking_id in self.stock_pickings:
                            if picking_id not in sale_order.picking_ids:
                                raise ValidationError("Invalid DC")
            if not self.env.user.has_group('restrict_dc.group_account_invoice'):
                for picking_id in self.stock_pickings:
                    if picking_id.state != 'done':
                        raise ValidationError("You cannot post invoice until DC is not Validated")
        return res
