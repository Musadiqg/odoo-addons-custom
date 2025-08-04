# -*- coding: utf-8 -*-
# from odoo import http


# class RestrictDc(http.Controller):
#     @http.route('/restrict_dc/restrict_dc', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/restrict_dc/restrict_dc/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('restrict_dc.listing', {
#             'root': '/restrict_dc/restrict_dc',
#             'objects': http.request.env['restrict_dc.restrict_dc'].search([]),
#         })

#     @http.route('/restrict_dc/restrict_dc/objects/<model("restrict_dc.restrict_dc"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('restrict_dc.object', {
#             'object': obj
#         })
