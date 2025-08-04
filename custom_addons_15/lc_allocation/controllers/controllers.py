# -*- coding: utf-8 -*-
# from odoo import http


# class LcAllocation(http.Controller):
#     @http.route('/lc_allocation/lc_allocation', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/lc_allocation/lc_allocation/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('lc_allocation.listing', {
#             'root': '/lc_allocation/lc_allocation',
#             'objects': http.request.env['lc_allocation.lc_allocation'].search([]),
#         })

#     @http.route('/lc_allocation/lc_allocation/objects/<model("lc_allocation.lc_allocation"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('lc_allocation.object', {
#             'object': obj
#         })
