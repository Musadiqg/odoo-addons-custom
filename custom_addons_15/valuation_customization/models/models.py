from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import groupby, float_is_zero
from collections import defaultdict
from odoo.tools.misc import OrderedSet, format_date, groupby as tools_groupby

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.model
    def create(self, vals_list):
        res = super(PurchaseOrderLine, self).create(vals_list)
        if len(res.taxes_id) > 1:
            raise ValidationError("Multiple Taxes found")
        return res

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    x_value = fields.Float('Total Value', readonly=False,compute='get_eval')

    def get_eval(self):
        for rec in self:
            rec.x_value = rec.quantity * rec.unit_cost


class AccountTax(models.Model):
    _inherit = 'account.tax'

    is_import = fields.Boolean('Applicable on Valuation')


class StockMove(models.Model):
    _inherit = 'stock.move'

    def product_price_update_before_done(self, forced_qty=None):
        tmpl_dict = defaultdict(lambda: 0.0)
        # adapt standard price on incomming moves if the product cost_method is 'average'
        std_price_update = {}
        tax_id = self.purchase_line_id.taxes_id
        # if len(tax_id) > 1:
        #     raise ValidationError("Multiple Taxes Found on Purchase Line ! Please contact Finance")
        for move in self.filtered(
                lambda move: move._is_in() and move.with_company(move.company_id).product_id.cost_method == 'average'):
            product_tot_qty_available = move.product_id.sudo().with_company(move.company_id).quantity_svl + tmpl_dict[
                move.product_id.id]
            rounding = move.product_id.uom_id.rounding

            valued_move_lines = move._get_in_move_lines()
            qty_done = 0
            for valued_move_line in valued_move_lines:
                qty_done += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done,
                                                                              move.product_id.uom_id)

            if len(tax_id) > 1:
                raise ValidationError("Multiple Taxes found ! Please contact Finance Dept")
            qty = forced_qty or qty_done
            if float_is_zero(product_tot_qty_available, precision_rounding=rounding):
                if self.company_id.id == 1:
                    tax_incl_price_unit = move._get_price_unit() * (1 + (tax_id.amount / 100))
                elif self.company_id.id != 1 and tax_id.is_import:
                    tax_incl_price_unit = move._get_price_unit() * (1 + (tax_id.amount / 100))
                else:
                    tax_incl_price_unit = move._get_price_unit()
                new_std_price = tax_incl_price_unit
            elif float_is_zero(product_tot_qty_available + move.product_qty, precision_rounding=rounding) or \
                    float_is_zero(product_tot_qty_available + qty, precision_rounding=rounding):
                if self.company_id.id == 1:
                    tax_incl_price_unit = move._get_price_unit() * (1 + (tax_id.amount / 100))
                # elif self.company_id.id != 1 and tax_id.is_import:
                #     tax_incl_price_unit = move._get_price_unit() * (1 + (tax_id.amount / 100))
                else:
                    tax_incl_price_unit = move._get_price_unit()
                new_std_price = tax_incl_price_unit
            else:
                # Get the standard price
                amount_unit = (std_price_update.get(
                    (move.company_id.id, move.product_id.id)) or move.product_id.with_company(
                    move.company_id).standard_price)
                if self.company_id.id == 1:
                    tax_incl_price_unit = move._get_price_unit() * (1 + (tax_id.amount / 100))
                # elif self.company_id.id != 1 and tax_id.is_import:
                #     tax_incl_price_unit = move._get_price_unit() * (1 + (tax_id.amount / 100))
                else:
                    tax_incl_price_unit = move._get_price_unit()
                new_std_price = ((amount_unit * product_tot_qty_available) + (tax_incl_price_unit * qty)) / (
                            product_tot_qty_available + qty)

            tmpl_dict[move.product_id.id] += qty_done
            # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
            move.product_id.with_company(move.company_id.id).with_context(disable_auto_svl=True).sudo().write(
                {'standard_price': new_std_price})
            std_price_update[move.company_id.id, move.product_id.id] = new_std_price

        # adapt standard price on incomming moves if the product cost_method is 'fifo'
        for move in self.filtered(lambda move:
                                  move.with_company(move.company_id).product_id.cost_method == 'fifo'
                                  and float_is_zero(move.product_id.sudo().quantity_svl,
                                                    precision_rounding=move.product_id.uom_id.rounding)):
            move.product_id.with_company(move.company_id.id).sudo().write({'standard_price': move._get_price_unit()})

    def product_price_update_before_return(self, forced_qty=None):
        tmpl_dict = defaultdict(lambda: 0.0)
        # adapt standard price on incomming moves if the product cost_method is 'average'
        std_price_update = {}
        tax_id = self.purchase_line_id.taxes_id
        if len(tax_id) > 1:
                raise ValidationError("Multiple Taxes found ! Please contact Finance Dept")
        for move in self.filtered(
                lambda move: move._is_out() and move.with_company(move.company_id).product_id.cost_method == 'average'):
            product_tot_qty_available = move.product_id.sudo().with_company(move.company_id).quantity_svl + tmpl_dict[
                move.product_id.id]
            rounding = move.product_id.uom_id.rounding

            valued_move_lines = move._get_in_move_lines()
            qty_done = 0
            for valued_move_line in valued_move_lines:
                qty_done += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done,
                                                                              move.product_id.uom_id)

            qty = - self.quantity_done
            if float_is_zero(product_tot_qty_available, precision_rounding=rounding):
                if self.company_id.id == 1:
                    tax_incl_price_unit = move._get_price_unit() * (1 + (tax_id.amount / 100))
                # elif self.company_id.id != 1 and tax_id.is_import:
                #     tax_incl_price_unit = move._get_price_unit() * (1 + (tax_id.amount / 100))
                else:
                    tax_incl_price_unit = move._get_price_unit()
                new_std_price = tax_incl_price_unit
            elif float_is_zero(product_tot_qty_available + move.product_qty, precision_rounding=rounding) or \
                    float_is_zero(product_tot_qty_available + qty, precision_rounding=rounding):
                if self.company_id.id == 1:
                    tax_incl_price_unit = move._get_price_unit() * (1 + (tax_id.amount / 100))
                # elif self.company_id.id != 1 and tax_id.is_import:
                #     tax_incl_price_unit = move._get_price_unit() * (1 + (tax_id.amount / 100))
                else:
                    tax_incl_price_unit = move._get_price_unit()
                new_std_price = tax_incl_price_unit
            else:
                # Get the standard price
                amount_unit = (std_price_update.get(
                    (move.company_id.id, move.product_id.id)) or move.product_id.with_company(
                    move.company_id).standard_price)
                if self.company_id.id == 1:
                    tax_incl_price_unit = move._get_price_unit() * (1 + (tax_id.amount / 100))
                # elif self.company_id.id != 1 and tax_id.is_import:
                #     tax_incl_price_unit = move._get_price_unit() * (1 + (tax_id.amount / 100))
                else:
                    tax_incl_price_unit = move._get_price_unit()
                new_std_price = ((amount_unit * product_tot_qty_available) + (tax_incl_price_unit * qty)) / (
                            product_tot_qty_available + qty)

            tmpl_dict[move.product_id.id] += qty_done
            # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
            move.product_id.with_company(move.company_id.id).with_context(disable_auto_svl=True).sudo().write(
                {'standard_price': new_std_price})
            std_price_update[move.company_id.id, move.product_id.id] = new_std_price

        # adapt standard price on incomming moves if the product cost_method is 'fifo'
        for move in self.filtered(lambda move:
                                  move.with_company(move.company_id).product_id.cost_method == 'fifo'
                                  and float_is_zero(move.product_id.sudo().quantity_svl,
                                                    precision_rounding=move.product_id.uom_id.rounding)):
            move.product_id.with_company(move.company_id.id).sudo().write({'standard_price': move._get_price_unit()})