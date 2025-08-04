from odoo import models, fields, _


class StockMove(models.Model):
    _inherit = 'stock.move.line'

    supp_batch = fields.Char('Supplier Batch No.')