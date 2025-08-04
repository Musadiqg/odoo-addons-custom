# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero


class LandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    clearing_code = fields.Many2one('clearing.code', "Clearing Code", required=True)
    vendor_bill_ids = fields.Many2many('account.move', string='Vendor Bill', copy=False,
                                       domain="[('move_type', '=', 'in_invoice'),('clearing_code', '=', clearing_code)]")

    @api.onchange('clearing_code')
    def fetch_grn_bill(self):
        if self.clearing_code:
            picking_ids = self.env['stock.picking'].search([("clearing_code.id", '=', self.clearing_code.id)])
            if picking_ids:
                self.picking_ids = picking_ids.ids

    @api.onchange('picking_ids')
    def check_picking_status(self):
        if self.picking_ids:
            for picking_ids in self.picking_ids:
                if 'Return' in picking_ids.origin:
                    raise ValidationError("Return GRNs are not applicable for LC")

    @api.model
    def create(self, vals_list):
        res = super(LandedCost, self).create(vals_list)
        if res.company_id.id == 1:
            res.name = self.env['ir.sequence'].next_by_code('cost.landed.sequence.hud')
            res.name = res.name + "/" + res.clearing_code.name + "/" + str(res.date.year)
        else:
            res.name = self.env['ir.sequence'].next_by_code('cost.landed.sequence.inn')
            res.name = res.name + "/" + res.clearing_code.name + "/" + str(res.date.year)
        for bill_id in res.vendor_bill_ids:
            for line in bill_id.invoice_line_ids:
                vals = {'product_id': line.product_id.id, 'account_id': line.account_id.id,
                        'price_unit': line.price_unit, 'split_method': 'equal', 'cost_id': res.id}
                self.env['stock.landed.cost.lines'].create(vals)
        return res

    def button_validate(self):
        self._check_can_validate()
        cost_without_adjusment_lines = self.filtered(lambda c: not c.valuation_adjustment_lines)
        if cost_without_adjusment_lines:
            cost_without_adjusment_lines.compute_landed_cost()
        if not self._check_sum():
            raise UserError(_('Cost and adjustments lines do not match. You should maybe recompute the landed costs.'))

        for cost in self:
            cost = cost.with_company(cost.company_id)
            move = self.env['account.move']
            move_vals = {
                'journal_id': cost.account_journal_id.id,
                'date': cost.date,
                'ref': cost.name,
                'line_ids': [],
                'move_type': 'entry',
            }
            valuation_layer_ids = []
            cost_to_add_byproduct = defaultdict(lambda: 0.0)
            location_ids = [136, 242, 12]
            for line in cost.valuation_adjustment_lines.filtered(
                    lambda line: line.move_id.location_dest_id.id in location_ids):
                remaining_qty = sum(line.move_id.stock_valuation_layer_ids.mapped('remaining_qty'))
                linked_layer = line.move_id.stock_valuation_layer_ids[:1]

                # Prorate the value at what's still in stock
                quant = self.env['stock.quant'].search(
                    [('lot_id', '=', line.move_id.lot_ids.id),
                     ('location_id', 'in', location_ids)])
                if not quant:
                    line_move_id_product_qty = line.move_id.product_qty
                    raise ValidationError("Quantity not valid for LC or Lot not found")
                else:
                    line_move_id_product_qty = 0
                    if quant.quantity >= 0:
                        line_move_id_product_qty = quant.quantity
                    elif quant.quantity == 0:
                        line_move_id_product_qty = line.move_id.product_qty
                    print()
                    cost_to_add = (remaining_qty / line_move_id_product_qty) * line.additional_landed_cost
                    if not cost.company_id.currency_id.is_zero(cost_to_add):
                        valuation_layer = self.env['stock.valuation.layer'].create({
                            'value': cost_to_add,
                            'unit_cost': 0,
                            'quantity': 0,
                            'remaining_qty': 0,
                            'stock_valuation_layer_id': linked_layer.id,
                            'description': cost.name,
                            'stock_move_id': line.move_id.id,
                            'product_id': line.move_id.product_id.id,
                            'stock_landed_cost_id': cost.id,
                            'company_id': cost.company_id.id,
                        })
                        linked_layer.remaining_value += cost_to_add
                        valuation_layer_ids.append(valuation_layer.id)
                    # Update the AVCO
                    product = line.move_id.product_id
                    if product.cost_method == 'average':
                        cost_to_add_byproduct[product] += cost_to_add
                    # Products with manual inventory valuation are ignored because they do not need to create journal entries.
                    if product.valuation != "real_time":
                        continue
                    # `remaining_qty` is negative if the move is out and delivered proudcts that were not
                    # in stock.
                    qty_out = 0
                    # if not line.move_id._is_in() and not line.move_id._is_out and not "PO" in line.move_id.origin:
                    #     raise ValidationError("Something wrong in Transfer picking operation")
                    if line.move_id._is_in():
                        qty_out = line_move_id_product_qty - remaining_qty
                    elif line.move_id._is_out():
                        qty_out = line_move_id_product_qty
                    move_vals['line_ids'] += line._create_accounting_entries(move, qty_out)

                # batch standard price computation avoid recompute quantity_svl at each iteration
                products = self.env['product.product'].browse(p.id for p in cost_to_add_byproduct.keys())
                for product in products:  # iterate on recordset to prefetch efficiently quantity_svl
                    if not float_is_zero(product.quantity_svl, precision_rounding=product.uom_id.rounding):
                        product.with_company(cost.company_id).sudo().with_context(
                            disable_auto_svl=True).standard_price += cost_to_add_byproduct[
                                                                         product] / product.quantity_svl

                move_vals['stock_valuation_layer_ids'] = [(6, None, valuation_layer_ids)]
                # We will only create the accounting entry when there are defined lines (the lines will be those linked to products of real_time valuation category).
                cost_vals = {'state': 'done'}
                if move_vals.get("line_ids"):
                    move = move.create(move_vals)
                    cost_vals.update({'account_move_id': move.id})
                cost.write(cost_vals)
                if cost.account_move_id:
                    move._post()

                for bill_id in cost.vendor_bill_ids:
                    if bill_id and bill_id.state == 'posted' and cost.company_id.anglo_saxon_accounting:
                        all_amls = bill_id.line_ids | cost.account_move_id.line_ids
                        for product in cost.cost_lines.product_id:
                            accounts = product.product_tmpl_id.get_product_accounts()
                            input_account = accounts['stock_input']
                            all_amls.filtered(
                                lambda aml: aml.account_id == input_account and not aml.reconciled).reconcile()
                for picking in self.picking_ids:
                    account_move_line = self.env['account.move.line'].search([('name', 'like', picking.name)])
                    for line in account_move_line:
                        line.name = self.name + "-" + line.name
            return True

    def compute_landed_cost(self):
        AdjustementLines = self.env['stock.valuation.adjustment.lines']
        AdjustementLines.search([('cost_id', 'in', self.ids)]).unlink()

        towrite_dict = {}
        for cost in self.filtered(lambda cost: cost._get_targeted_move_ids()):
            rounding = cost.currency_id.rounding
            total_qty = 0.0
            total_cost = 0.0
            total_weight = 0.0
            total_volume = 0.0
            total_line = 0.0
            all_val_line_values = cost.get_valuation_lines()
            for val_line_values in all_val_line_values:
                for cost_line in cost.cost_lines:
                    val_line_values.update({'cost_id': cost.id, 'cost_line_id': cost_line.id})
                    self.env['stock.valuation.adjustment.lines'].create(val_line_values)
                total_qty += val_line_values.get('quantity', 0.0)
                total_weight += val_line_values.get('weight', 0.0)
                total_volume += val_line_values.get('volume', 0.0)

                former_cost = val_line_values.get('former_cost', 0.0)
                # round this because former_cost on the valuation lines is also rounded
                total_cost += cost.currency_id.round(former_cost)

                total_line += 1

            for line in cost.cost_lines:
                value_split = 0.0
                for valuation in cost.valuation_adjustment_lines:
                    value = 0.0
                    if valuation.cost_line_id and valuation.cost_line_id.id == line.id:
                        if line.split_method == 'by_quantity' and total_qty:
                            per_unit = (line.price_unit / total_qty)
                            value = valuation.quantity * per_unit
                        elif line.split_method == 'by_weight' and total_weight:
                            per_unit = (line.price_unit / total_weight)
                            value = valuation.weight * per_unit
                        elif line.split_method == 'by_volume' and total_volume:
                            per_unit = (line.price_unit / total_volume)
                            value = valuation.volume * per_unit
                        elif line.split_method == 'equal':
                            value = (line.price_unit / total_line)
                        elif line.split_method == 'by_current_cost_price' and total_cost:
                            per_unit = (line.price_unit / total_cost)
                            value = valuation.former_cost * per_unit
                        else:
                            value = (line.price_unit / total_line)

                        if rounding:
                            value = tools.float_round(value, precision_rounding=rounding, rounding_method='UP')
                            fnc = min if line.price_unit > 0 else max
                            value = fnc(value, line.price_unit - value_split)
                            value_split += value

                        if valuation.id not in towrite_dict:
                            towrite_dict[valuation.id] = value
                        else:
                            towrite_dict[valuation.id] += value
        for key, value in towrite_dict.items():
            AdjustementLines.browse(key).write({'additional_landed_cost': value})
        return True

    def get_valuation_lines(self):
        self.ensure_one()
        lines = []

        for move in self._get_targeted_move_ids():
            # it doesn't make sense to make a landed cost for a product that isn't set as being valuated in real time at real cost
            if move.product_id.cost_method not in ('fifo', 'average') or move.state == 'cancel' or not move.product_qty:
                continue
            if move.location_dest_id.id in [12, 136, 242]:
                qty = self.get_qty(move)
                vals = {
                    'product_id': move.product_id.id,
                    'move_id': move.id,
                    'quantity': qty,
                    'former_cost': self.get_former_cost(move),
                    'weight': move.product_id.weight * qty,
                    'volume': move.product_id.volume * qty
                }
                lines.append(vals)

        if not lines:
            target_model_descriptions = dict(self._fields['target_model']._description_selection(self.env))
            raise UserError(
                _("You cannot apply landed costs on the chosen %s(s). Landed costs can only be applied for products with FIFO or average costing method.",
                  target_model_descriptions[self.target_model]))
        return lines

    def get_qty(self, move_id):
        location_ids = [12, 136, 242]
        quant = self.env['stock.quant'].search(
            [('lot_id', '=', move_id.lot_ids.id), ('location_id', 'in', location_ids)])
        if not quant:
            return move_id.product_qty
        return quant.quantity

    def get_former_cost(self, move):
        value = 0
        if move:
            value = sum(
                self.env['stock.move'].search([('origin', '=', move.origin), ('product_id', '=', move.product_id.id)],
                                              limit=1).account_move_ids.line_ids.mapped('debit'))
            account_move_id = self.env['stock.move'].search(
                [('origin', '=', move.origin), ('product_id', '=', move.product_id.id)], limit=1).account_move_ids
            if account_move_id:
                for line in account_move_id.line_ids:
                    line.landed_cost = self.name + "-" + move.reference
        return value


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    landed_cost = fields.Char("LC Reference", related='move_id.ref')
    release_num = fields.Char("Release Reference", compute='get_ref')

    def get_ref(self):
        for rec in self:
            rec.release_num = False
            if rec.move_id.stock_move_id.origin:
                if "PO" in rec.move_id.stock_move_id.origin:
                    release = self.env['stock.picking'].search(
                        [('origin', '=', rec.move_id.stock_move_id.origin), ('picking_type_code', '=', 'internal'),
                         ('product_id','=',rec.move_id.stock_move_id.product_id.id)],limit=1)
                    if release:
                        rec.release_num = release.name
