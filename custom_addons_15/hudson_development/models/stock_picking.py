import requests
from datetime import date, datetime, time
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError, ValidationError, _logger
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class Picking(models.Model):
    _inherit = "stock.picking"

    def action_assign(self):
        """ Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        @return: True
        """
        for picking in self:
            _logger.debug(f"Picking {picking.id}: Checking type_code={picking.picking_type_id.code}, dest_usage={picking.location_dest_id.usage}, source_loc={picking.location_id.name}")
            if (picking.picking_type_id.code == 'outgoing'
                and picking.location_dest_id.usage == 'supplier'
                and picking.location_id.id != 14):  # Allow reservation for QC (ID 14)
                _logger.debug(f"Picking {picking.id}: Early return triggered for supplier return (not from QC)")
                return True
            
        _logger.debug(f"Picking {self.ids}: Proceeding with normal flow")
        self.revert_reserve()
        self.filtered(lambda picking: picking.state == 'draft').action_confirm()
        moves = self.mapped('move_lines').filtered(lambda move: move.state not in ('draft', 'cancel', 'done')).sorted(
            key=lambda move: (-int(move.priority), not bool(move.date_deadline), move.date_deadline, move.date, move.id)
        )
        if not moves:
            raise UserError(_('Nothing to check the availability for.'))
        package_level_done = self.mapped('package_level_ids').filtered(
            lambda pl: pl.is_done and pl.state == 'confirmed')
        package_level_done.write({'is_done': False})
        moves._action_assign()
        package_level_done.write({'is_done': True})
        _logger.debug(f"Picking {self.ids}: Completed action_assign for moves")
        return True

    def button_validate(self):
        # Clean-up the context key at validation to avoid forcing the creation of immediate
        # transfers.

        if self.env.context.get('active_model') == 'sale.order' or self.sale_id:
            if 'Return' not in self.origin: 
                self.update_lot_price()
        res = super(Picking, self).button_validate()
        if self.location_id.name in ['Input', 'Input OTC', 'Input Premix'] and self.location_dest_id.name in [
            'FinishedGoods', 'Finished Goods Stores OTC', 'Finished Goods Stores Premix']:
            self._notify()
        if self.location_id.location_id.name == 'Virtual Locations':
            self.post_msg()
        if self.location_id.id in [14, 214, 243,246] and self.location_dest_id.id in [12, 136, 242, 244]:
            self.handle_release()
        return res

    def handle_release(self):
        for line in self.move_line_ids_without_package:
            stock_move = self.env['stock.move'].search([('picking_id','=',self.id),('move_line_ids','in',line.id)],limit=1)
            if stock_move:
                if line.qty_done > stock_move.product_uom_qty or line.qty_done >stock_move.product_uom_qty:
                    err = _(
                        "You have chosen to avoid negative stock. %s pieces of %s are remaining in location %s"
                        "but you want to transfer %s pieces. "
                        "Please adjust your quantities or correct your stock with an inventory adjustment."
                    ) % (stock_move.product_qty or stock_move.product_uom_qty, line.product_id.name, line.location_id.name, line.qty_done)

                    raise ValidationError(err)

    def post_msg(self):
        raise ValidationError(_('Please contact Administrator'))

    def _notify(self):
        title = "*Batch Closing Notification*"
        product = self.product_id.name
        batch = self.move_line_ids.lot_id.name
        msg = "<!subteam^SPM83PL66|@fg> Following Batch has been received in Warehouse Finished Goods:" + "\n *Batch No. *: " + batch + "\n*Product*: " + product + "\n*Company*:" + self.company_id.name
        URL = "https://portal.hudsonpharma.com/SlackService.svc/PostMessageToSlack?title=" + title + "&message=" + msg + "&channel=CR7QS4VCN"
        response = requests.request("GET", URL)
        print("---------------------------", response)

    def update_lot_price(self):
        if self.sale_id.pricelist_id.name == 'Public Pricelist':
            product_ids = self.sale_id.order_line.mapped('product_id.id')
            counter = 0
            for product_id in product_ids:
                move_lines = self.move_line_ids.filtered(lambda x: x.product_id.id == product_id)
                sale_lines = self.sale_id.order_line.filtered(lambda x: x.product_id.id == product_id)
                if len(move_lines) != len(sale_lines):
                    if len(move_lines) > 1:
                        for line in move_lines:
                            if counter == 0:
                                x_price = line.lot_id.x_SalePrice
                                counter += 1
                            elif counter > 0:
                                if x_price != line.lot_id.x_SalePrice:
                                    raise ValidationError('Please contact Supply chain to break the product order line')
                else:
                    for move_line in move_lines:
                        if move_line.lot_id and move_line.lot_id.x_SalePrice > 0:
                            if move_line.move_id.sale_line_id.price_unit != move_line.lot_id.x_SalePrice:
                                move_line.move_id.sale_line_id.price_unit = move_line.lot_id.x_SalePrice

    def revert_reserve(self):
        for move_line in self.move_lines:
            QUANTS = self.env['stock.quant'].search(
                [('product_id', '=', move_line.product_id.id), ('reserved_quantity', '>', 0)])
            # QUANTS = self.env['stock.quant'].browse(127550)
            reserved_quants = QUANTS.filtered(lambda z: z.available_quantity <= 0 or z.available_quantity < z.reserved_quantity)
            for line in reserved_quants:
                domain = [('product_id', '=', line.product_id.id), ('state', 'not in', ['done', 'cancel']),
                          ('origin', '!=', False)]
                if self.x_studio_production_order:
                    lot = self.x_studio_production_order.split(" ")[0]
                    domain += [('lot_id.name','=',lot)]
                if move_line.location_id.id == 14:
                    domain += [('location_id','=',14)]
                product_moves = self.env['stock.move.line'].search(domain)
                is_reserved = product_moves.filtered(lambda l: l.product_uom_qty > 0 and 'PO' not in l.origin)
                if not is_reserved:
                    line.write({'reserved_quantity': 0})
