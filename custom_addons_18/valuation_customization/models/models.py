# -*- coding: utf-8 -*-
from collections import defaultdict
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero
import logging
_logger = logging.getLogger(__name__)

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

    x_value = fields.Float('Total Value', readonly=False, compute='get_eval')

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
        std_price_update = {}
        for move in self.filtered(lambda m: m._is_in()):
            if move.product_id.with_company(move.company_id).cost_method != 'average':
                _logger.info(f"Skipping move for product {move.product_id.name}: Cost method is {move.product_id.cost_method}, not 'average'")
                continue

            _logger.info(f"Processing move for product: {move.product_id.name}, Company ID: {move.company_id.id}")
            tax_id = move.purchase_line_id.taxes_id
            _logger.info(f"tax_id: {tax_id} (amount: {tax_id.amount if tax_id else 'None'})")

            product_tot_qty_available = move.product_id.sudo().with_company(move.company_id).quantity_svl + tmpl_dict[move.product_id.id]
            _logger.info(f"product_tot_qty_available: {product_tot_qty_available}")
            rounding = move.product_id.uom_id.rounding

            valued_move_lines = move._get_in_move_lines()
            qty_done = 0
            for valued_move_line in valued_move_lines:
                line_qty_kg = valued_move_line.product_uom_id._compute_quantity(
                    valued_move_line.quantity, move.product_id.uom_id
                )
                qty_done += line_qty_kg
            _logger.info(f"qty_done: {qty_done}")

            if len(tax_id) > 1:
                raise ValidationError("Multiple Taxes found! Please contact Finance Dept")

            qty = forced_qty or qty_done

            price_unit_dict = move._get_price_unit()
            _logger.info(f"price_unit from _get_price_unit: {price_unit_dict} (Type: {type(price_unit_dict)})")
            _logger.info(f"price_unit_dict keys: {list(price_unit_dict.keys()) if isinstance(price_unit_dict, dict) else 'N/A'}")
            _logger.info(f"price_unit_dict values: {list(price_unit_dict.values()) if isinstance(price_unit_dict, dict) else 'N/A'}")
            if isinstance(price_unit_dict, dict):
                try:
                    price_unit = next(iter(price_unit_dict.values()), move.product_id.standard_price or 0.0)
                except Exception as e:
                    _logger.error(f"Error extracting price from dict: {e}")
                    price_unit = move.product_id.standard_price or 0.0
            else:
                price_unit = price_unit_dict
            _logger.info(f"final price_unit: {price_unit}")

            if move.company_id.id == 1 and tax_id:
                tax_incl_price_unit = price_unit * (1 + (tax_id.amount / 100))
            elif move.company_id.id != 1 and tax_id and tax_id.is_import:
                tax_incl_price_unit = price_unit * (1 + (tax_id.amount / 100))
            else:
                tax_incl_price_unit = price_unit
            _logger.info(f"tax_incl_price_unit: {tax_incl_price_unit}")

            if float_is_zero(product_tot_qty_available, precision_rounding=rounding):
                new_std_price = tax_incl_price_unit
            elif float_is_zero(product_tot_qty_available + qty, precision_rounding=rounding):
                new_std_price = tax_incl_price_unit
            else:
                amount_unit = (std_price_update.get((move.company_id.id, move.product_id.id))
                               or move.product_id.with_company(move.company_id).standard_price)
                _logger.info(f"amount_unit (current standard_price): {amount_unit}")
                new_std_price = (
                    (amount_unit * product_tot_qty_available) +
                    (tax_incl_price_unit * qty)
                ) / (product_tot_qty_available + qty)
            _logger.info(f"new_std_price: {new_std_price}")

            tmpl_dict[move.product_id.id] += qty_done
            move.product_id.with_company(move.company_id.id).with_context(disable_auto_svl=True).sudo().write(
                {'standard_price': new_std_price}
            )
            std_price_update[move.company_id.id, move.product_id.id] = new_std_price
            _logger.info(f"Updated standard_price to {new_std_price}")

    # Original product_price_update_before_done method (commented out)
    # def product_price_update_before_done(self, forced_qty=None):
    #     tmpl_dict = defaultdict(lambda: 0.0)
    #     std_price_update = {}
    #     for move in self.filtered(lambda m: m._is_in()):
    #         if move.product_id.with_company(move.company_id).cost_method != 'average':
    #             _logger.info(f"Skipping move for product {move.product_id.name}: Cost method is {move.product_id.cost_method}, not 'average'")
    #             continue
    #         _logger.info(f"Processing move for product: {move.product_id.name}, Company ID: {move.company_id.id}")
    #         tax_id = move.purchase_line_id.taxes_id
    #         _logger.info(f"tax_id: {tax_id} (amount: {tax_id.amount if tax_id else 'None'})")
    #         product_tot_qty_available = move.product_id.sudo().with_company(move.company_id).quantity_svl + tmpl_dict[move.product_id.id]
    #         _logger.info(f"product_tot_qty_available: {product_tot_qty_available}")
    #         rounding = move.product_id.uom_id.rounding
    #         valued_move_lines = move._get_in_move_lines()
    #         qty_done = 0
    #         for valued_move_line in valued_move_lines:
    #             line_qty_kg = valued_move_line.product_uom_id._compute_quantity(
    #                 valued_move_line.quantity, move.product_id.uom_id
    #             )
    #             qty_done += line_qty_kg
    #         _logger.info(f"qty_done: {qty_done}")
    #         if len(tax_id) > 1:
    #             raise ValidationError("Multiple Taxes found! Please contact Finance Dept")
    #         qty = forced_qty or qty_done
    #         price_unit = move._get_price_unit()
    #         _logger.info(f"price_unit from _get_price_unit: {price_unit}")
    #         if isinstance(price_unit, dict):
    #             price_unit = price_unit.get('price_unit', move.product_id.standard_price or 0.0)
    #         _logger.info(f"final price_unit: {price_unit}")
    #         if move.company_id.id == 1 and tax_id:
    #             tax_incl_price_unit = price_unit * (1 + (tax_id.amount / 100))
    #         elif move.company_id.id != 1 and tax_id.is_import:
    #             tax_incl_price_unit = price_unit * (1 + (tax_id.amount / 100))
    #         else:
    #             tax_incl_price_unit = price_unit
    #         _logger.info(f"tax_incl_price_unit: {tax_incl_price_unit}")
    #         if float_is_zero(product_tot_qty_available, precision_rounding=rounding):
    #             new_std_price = tax_incl_price_unit
    #         elif float_is_zero(product_tot_qty_available + qty, precision_rounding=rounding):
    #             new_std_price = tax_incl_price_unit
    #         else:
    #             amount_unit = (std_price_update.get((move.company_id.id, move.product_id.id))
    #                            or move.product_id.with_company(move.company_id).standard_price)
    #             _logger.info(f"amount_unit (current standard_price): {amount_unit}")
    #             new_std_price = (
    #                 (amount_unit * product_tot_qty_available) +
    #                 (tax_incl_price_unit * qty)
    #             ) / (product_tot_qty_available + qty)
    #         _logger.info(f"new_std_price: {new_std_price}")
    #         tmpl_dict[move.product_id.id] += qty_done
    #         move.product_id.with_company(move.company_id.id).with_context(disable_auto_svl=True).sudo().write(
    #             {'standard_price': new_std_price}
    #         )
    #         std_price_update[move.company_id.id, move.product_id.id] = new_std_price
    #         _logger.info(f"Updated standard_price to {new_std_price}")

    def product_price_update_before_return(self, forced_qty=None):
        tmpl_dict = defaultdict(lambda: 0.0)
        std_price_update = {}
        tax_id = self.purchase_line_id.taxes_id

        if len(tax_id) > 1:
            raise ValidationError("Multiple Taxes found ! Please contact Finance Dept")

        for move in self.filtered(lambda m: m._is_out() and
                                  m.with_company(m.company_id).product_id.cost_method == 'average'):
            product_tot_qty_available = (move.product_id.sudo()
                                         .with_company(move.company_id)
                                         .quantity_svl
                                         + tmpl_dict[move.product_id.id])
            rounding = move.product_id.uom_id.rounding

            valued_move_lines = move._get_in_move_lines()
            qty_done = 0
            for valued_move_line in valued_move_lines:
                line_qty_kg = valued_move_line.product_uom_id._compute_quantity(
                    valued_move_line.quantity, move.product_id.uom_id
                )
                qty_done += line_qty_kg

            qty = -(move.quantity_done)

            price_unit = move._get_price_unit()
            if isinstance(price_unit, dict):
                price_unit = price_unit.get('price_unit', move.product_id.standard_price or 0.0)

            if move.company_id.id == 1 and tax_id:
                tax_incl_price_unit = price_unit * (1 + (tax_id.amount / 100))
            elif move.company_id.id != 1 and tax_id.is_import:
                tax_incl_price_unit = price_unit * (1 + (tax_id.amount / 100))
            else:
                tax_incl_price_unit = price_unit

            if float_is_zero(product_tot_qty_available, precision_rounding=rounding):
                new_std_price = tax_incl_price_unit
            elif float_is_zero(product_tot_qty_available + move.product_qty, precision_rounding=rounding) or \
                    float_is_zero(product_tot_qty_available + qty, precision_rounding=rounding):
                new_std_price = tax_incl_price_unit
            else:
                amount_unit = (std_price_update.get((move.company_id.id, move.product_id.id))
                               or move.product_id.with_company(move.company_id).standard_price)
                new_std_price = (
                    (amount_unit * product_tot_qty_available) +
                    (tax_incl_price_unit * qty)
                ) / (product_tot_qty_available + qty)

            tmpl_dict[move.product_id.id] += qty_done
            move.product_id.with_company(move.company_id.id).with_context(disable_auto_svl=True).sudo().write(
                {'standard_price': new_std_price}
            )
            std_price_update[move.company_id.id, move.product_id.id] = new_std_price

        for move in self.filtered(lambda m:
                                  m.with_company(m.company_id).product_id.cost_method == 'fifo'
                                  and float_is_zero(m.product_id.sudo().quantity_svl,
                                                    precision_rounding=m.product_id.uom_id.rounding)):
            price_unit = move._get_price_unit()
            if isinstance(price_unit, dict):
                price_unit = price_unit.get('price_unit', move.product_id.standard_price or 0.0)
            move.product_id.with_company(move.company_id.id).sudo().write({'standard_price': price_unit})