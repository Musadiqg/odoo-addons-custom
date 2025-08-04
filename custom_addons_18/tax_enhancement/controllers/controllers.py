# -*- coding: utf-8 -*-
# from odoo import http


# class TaxEnhancement(http.Controller):
#     @http.route('/tax_enhancement/tax_enhancement', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tax_enhancement/tax_enhancement/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('tax_enhancement.listing', {
#             'root': '/tax_enhancement/tax_enhancement',
#             'objects': http.request.env['tax_enhancement.tax_enhancement'].search([]),
#         })

#     @http.route('/tax_enhancement/tax_enhancement/objects/<model("tax_enhancement.tax_enhancement"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tax_enhancement.object', {
#             'object': obj
#         })
