# -*- coding: utf-8 -*-
# from odoo import http


# class PartyChequeReport(http.Controller):
#     @http.route('/party_cheque_report/party_cheque_report', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/party_cheque_report/party_cheque_report/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('party_cheque_report.listing', {
#             'root': '/party_cheque_report/party_cheque_report',
#             'objects': http.request.env['party_cheque_report.party_cheque_report'].search([]),
#         })

#     @http.route('/party_cheque_report/party_cheque_report/objects/<model("party_cheque_report.party_cheque_report"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('party_cheque_report.object', {
#             'object': obj
#         })
