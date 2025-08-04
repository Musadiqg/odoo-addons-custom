from odoo import models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        """
        Overrides _action_done to handle lot assignment in WH/Quality Control (ID=14).

        If a move line requires a new lot (i.e., lot_id is set but doesn't exist in QC),
        we split the existing unassigned quant (lot_id=False) so that part of it
        becomes the specified lot. This prevents negative stock errors, since Odoo then
        sees an actual quant with that lot in QC.
        """
        qc_location_id = 14  # ID of WH/Quality Control location

        for move in self:
            picking = move.picking_id

            # Only process if this picking is from QC and the product is lot-tracked
            if (
                picking
                and picking.location_id.id == qc_location_id
                and move.product_id.tracking == 'lot'
            ):
                # Loop over each move line 
                for move_line in move.move_line_ids:
                    # Only handle lines that have a new lot and a done quantity
                    if move_line.lot_id and move_line.qty_done > 0:
                        # Find an 'unassigned' quant in QC with enough stock
                        unassigned_quant = self.env['stock.quant'].search([
                            ('location_id', '=', qc_location_id),
                            ('product_id', '=', move.product_id.id),
                            ('lot_id', '=', False),
                            ('quantity', '>=', move_line.qty_done),
                        ], limit=1, order='in_date')

                        if not unassigned_quant:
                            # If we can't find enough unassigned stock, raise an error
                            raise UserError(_(
                                "Insufficient unassigned stock in QC for product '%s' "
                                "to assign %s units to lot '%s'."
                            ) % (
                                move.product_id.display_name,
                                move_line.qty_done,
                                move_line.lot_id.name
                            ))

                        leftover_qty = unassigned_quant.quantity - move_line.qty_done
                        if leftover_qty < 0:
                            raise UserError(_(
                                "Logic error: leftover quantity went negative. "
                                "Tried to assign %s units from a quant of %s."
                            ) % (move_line.qty_done, unassigned_quant.quantity))

                        # 1) Reduce the unassigned quant by the needed qty
                        unassigned_quant.write({'quantity': leftover_qty})

                        # 2) Create a new quant in QC for the specified lot
                        self.env['stock.quant'].create({
                            'product_id': move.product_id.id,
                            'location_id': qc_location_id,
                            'quantity': move_line.qty_done,
                            'lot_id': move_line.lot_id.id,
                            'owner_id': unassigned_quant.owner_id.id or False,
                            'package_id': unassigned_quant.package_id.id or False,
                        })
        
        return super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
