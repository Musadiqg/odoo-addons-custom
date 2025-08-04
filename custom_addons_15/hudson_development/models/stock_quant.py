import requests
from datetime import date, datetime, time
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError, ValidationError, _logger
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def _update_reserved_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None,
                                  strict=False):
        """ Increase the reserved quantity, i.e. increase `reserved_quantity` for the set of quants
        sharing the combination of `product_id, location_id` if `strict` is set to False or sharing
        the *exact same characteristics* otherwise. Typically, this method is called when reserving
        a move or updating a reserved move line. When reserving a chained move, the strict flag
        should be enabled (to reserve exactly what was brought). When the move is MTS,it could take
        anything from the stock, so we disable the flag. When editing a move line, we naturally
        enable the flag, to reflect the reservation according to the edition.

        :return: a list of tuples (quant, quantity_reserved) showing on which quant the reservation
            was done and how much the system was able to reserve on it
        """
        self = self.sudo()
        rounding = product_id.uom_id.rounding
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id,
                              strict=strict)
        reserved_quants = []

        if float_compare(quantity, 0, precision_rounding=rounding) > 0:
            # if we want to reserve
            available_quantity = self._get_available_quantity(product_id, location_id, lot_id=lot_id,
                                                              package_id=package_id, owner_id=owner_id, strict=strict)
            if float_compare(quantity, available_quantity, precision_rounding=rounding) > 0:
                raise UserError(_('It is not possible to reserve more products of %s than you have in stock.',
                                  product_id.display_name))
        elif float_compare(quantity, 0, precision_rounding=rounding) < 0:
            # if we want to unreserve
            available_quantity = sum(quants.mapped('reserved_quantity'))
            if float_compare(abs(quantity), available_quantity, precision_rounding=rounding) > 0:
                self.cron_set_reserve_qty(product_id.id)
                # raise UserError(_('It is not possible to unreserve more products of %s than you have in stock.',
                #                   product_id.display_name))
        else:
            return reserved_quants

        for quant in quants:
            if float_compare(quantity, 0, precision_rounding=rounding) > 0:
                max_quantity_on_quant = quant.quantity - quant.reserved_quantity
                if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                    continue
                max_quantity_on_quant = min(max_quantity_on_quant, quantity)
                quant.reserved_quantity += max_quantity_on_quant
                reserved_quants.append((quant, max_quantity_on_quant))
                quantity -= max_quantity_on_quant
                available_quantity -= max_quantity_on_quant
            else:
                max_quantity_on_quant = min(quant.reserved_quantity, abs(quantity))
                quant.reserved_quantity -= max_quantity_on_quant
                reserved_quants.append((quant, -max_quantity_on_quant))
                quantity += max_quantity_on_quant
                available_quantity += max_quantity_on_quant

            if float_is_zero(quantity, precision_rounding=rounding) or float_is_zero(available_quantity,
                                                                                     precision_rounding=rounding):
                break
        return reserved_quants

    def revert_reserve(self):

        coas = self.env['batch.closing.coa'].search([('x_studio_company_1','=',5)])
        for c in coas:
            if c.coas.company_id.id != 5:
                c.unlink()
        # vals={'company_id':1,'product_id':370,'quantity':0,'value':31320.85,'x_studio_char_field_qnVVM':'Opening 2018'}
        # self.env['stock.valuation.layer'].create(vals)
        
        # QUANTS = self.env['stock.quant'].search([('reserved_quantity','>',0)])
        # # QUANTS = self.env['stock.quant'].browse(127550)
        # reserved_quants = QUANTS.filtered(lambda z: z.available_quantity <= 0)
        # for line in reserved_quants:
        #     product_moves = self.env['stock.move.line'].search(
        #         [('product_id', '=', line.product_id.id),('state','!=','done'),('origin','!=',False)])
        #     is_reserved = product_moves.filtered(lambda l: l.product_uom_qty > 0 and 'PO' not in l.origin)
        #     if not is_reserved:
        #         line.update({'reserved_quantity': 0})

    def _run_cron(self):
        QUANTS = self.env['stock.quant'].search([])
        # zero_on_hand_quant = QUANTS.filtered(
        #     lambda z: z.available_quantity <= 0.0)
        # for line in zero_on_hand_quant:
        #     vals = {
        #         'product_id': line.product_id.id,
        #         'location_id': line.location_id.id,
        #         'product_categ_id': line.product_categ_id.id,
        #         'lot_id': line.lot_id.id,
        #         'owner_id': line.owner_id.id,
        #         'inventory_quantity_auto_apply': line.inventory_quantity_auto_apply,
        #         'available_quantity': line.available_quantity,
        #         'product_uom_id': line.product_uom_id.id,
        #         'value': line.value,
        #         'company_id': line.company_id.id
        #     }
        #     line_backup = self.env['stock.quant.backup'].create(vals)
            # line.unlink()

    def cron_set_reserve_qty(self,product_id):
        quants = self.env['stock.quant'].search([('product_id', '=', product_id)])

        move_line_ids = []

        warning = ""

        for quant in quants:

            move_lines = self.env['stock.move.line'].search(

                [

                    ('product_id', '=', quant.product_id.id),

                    ('location_id', '=', quant.location_id.id),

                    ('lot_id', '=', quant.lot_id.id),

                    ('package_id', '=', quant.package_id.id),

                    ('owner_id', '=', quant.owner_id.id),

                    ('product_qty', '!=', 0),

                ]

            )

            move_line_ids += move_lines.ids

            reserved_on_move_lines = sum(move_lines.mapped('product_qty'))

            move_line_str = str.join(

                ", ", [str(move_line_id) for move_line_id in move_lines.ids]

            )

            if quant.location_id.should_bypass_reservation():

                # If a quant is in a location that should bypass the reservation, its `reserved_quantity` field

                # should be 0.

                if quant.reserved_quantity != 0:
                    quant.write({'reserved_quantity': 0})

            else:

                # If a quant is in a reservable location, its `reserved_quantity` should be exactly the sum

                # of the `product_qty` of all the partially_available / assigned move lines with the same

                # characteristics.

                if quant.reserved_quantity == 0:

                    if move_lines:
                        move_lines.with_context(bypass_reservation_update=True).write(

                            {'product_uom_qty': 0}

                        )

                elif quant.reserved_quantity < 0:

                    quant.write({'reserved_quantity': 0})

                    if move_lines:
                        move_lines.with_context(bypass_reservation_update=True).write(

                            {'product_uom_qty': 0}

                        )

                else:

                    if reserved_on_move_lines != quant.reserved_quantity:

                        move_lines.with_context(bypass_reservation_update=True).write(

                            {'product_uom_qty': 0}

                        )

                        quant.write({'reserved_quantity': 0})

                    else:

                        if any(move_line.product_qty < 0 for move_line in move_lines):
                            move_lines.with_context(bypass_reservation_update=True).write(

                                {'product_uom_qty': 0}

                            )

                            quant.write({'reserved_quantity': 0})

        move_lines = self.env['stock.move.line'].search(

            [

                ('product_id.type', '=', 'product'),

                ('product_qty', '!=', 0),

                ('id', 'not in', move_line_ids),

            ]

        )

        move_lines_to_unreserve = []

        for move_line in move_lines:

            if not move_line.location_id.should_bypass_reservation():
                move_lines_to_unreserve.append(move_line.id)

        if len(move_lines_to_unreserve) > 1:

            self.env.cr.execute(

                """ 

                    UPDATE stock_move_line SET product_uom_qty = 0, product_qty = 0 WHERE id in %s ;

                """

                % (tuple(move_lines_to_unreserve),)

            )

        elif len(move_lines_to_unreserve) == 1:

            self.env.cr.execute(

                """ 

                UPDATE stock_move_line SET product_uom_qty = 0, product_qty = 0 WHERE id = %s ;

                """

                % (move_lines_to_unreserve[0])

            )
