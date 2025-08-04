# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OrderPOQtyReport(models.TransientModel):
    _name = 'order.po.qty.report'

    def print_pdf_report(self):
        print()
        data = {

        }
        return self.env.ref('order_qty_report.order_po_qty_xlsx').report_action(self, data=data)


class OrderQtyReport(models.TransientModel):
    _name = 'order.qty.report'

    start_at = fields.Datetime("Start Date")
    end_date = fields.Datetime("End Date", required=True)
    product_id = fields.Many2many('product.product', string="Product Variant")

    def print_pdf_report(self):
        data = {
            'start_at': self.start_at,
            'end_at': self.end_date,
            'product_id': self.product_id.ids,
        }
        print()
        return self.env.ref('order_qty_report.order_qty_xlsx').report_action(self, data=data)