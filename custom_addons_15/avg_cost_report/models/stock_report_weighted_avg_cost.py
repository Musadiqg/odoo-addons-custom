import requests
from datetime import date, datetime, time
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError, ValidationError, _logger
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class WACStockReport(models.TransientModel):
    _name = 'stock.report.weighted'

    start_at = fields.Datetime("From")
    end_date = fields.Datetime("To",required=True)
    product_id = fields.Many2many('product.product',string="Product Variant")
    product_tmpl_id = fields.Many2one('product.template',"Product")
    categ_id = fields.Many2one('product.category',"Category",required=True)

    def print_pdf_report(self):
        data = {
            'start_at': self.start_at,
            'end_at': self.end_date,
            'product_id': self.product_id.ids,
            'product_tmpl_id': self.product_tmpl_id.id,
        }
        print()
        return self.env.ref('avg_cost_report.svls_xlsx').report_action(self, data=data)