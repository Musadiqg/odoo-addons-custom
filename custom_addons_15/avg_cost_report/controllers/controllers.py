# -*- coding: utf-8 -*-
# from odoo import http


# class AvgCostReport(http.Controller):
#     @http.route('/avg_cost_report/avg_cost_report', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/avg_cost_report/avg_cost_report/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('avg_cost_report.listing', {
#             'root': '/avg_cost_report/avg_cost_report',
#             'objects': http.request.env['avg_cost_report.avg_cost_report'].search([]),
#         })

#     @http.route('/avg_cost_report/avg_cost_report/objects/<model("avg_cost_report.avg_cost_report"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('avg_cost_report.object', {
#             'object': obj
#         })
