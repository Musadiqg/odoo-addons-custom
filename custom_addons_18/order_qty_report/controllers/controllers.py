# -*- coding: utf-8 -*-
# from odoo import http


# class OrderQtyReport(http.Controller):
#     @http.route('/order_qty_report/order_qty_report', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/order_qty_report/order_qty_report/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('order_qty_report.listing', {
#             'root': '/order_qty_report/order_qty_report',
#             'objects': http.request.env['order_qty_report.order_qty_report'].search([]),
#         })

#     @http.route('/order_qty_report/order_qty_report/objects/<model("order_qty_report.order_qty_report"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('order_qty_report.object', {
#             'object': obj
#         })
