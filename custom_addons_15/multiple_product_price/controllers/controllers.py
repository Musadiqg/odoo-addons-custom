# -*- coding: utf-8 -*-
# from odoo import http


# class MultipleProductPrice(http.Controller):
#     @http.route('/multiple_product_price/multiple_product_price', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/multiple_product_price/multiple_product_price/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('multiple_product_price.listing', {
#             'root': '/multiple_product_price/multiple_product_price',
#             'objects': http.request.env['multiple_product_price.multiple_product_price'].search([]),
#         })

#     @http.route('/multiple_product_price/multiple_product_price/objects/<model("multiple_product_price.multiple_product_price"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('multiple_product_price.object', {
#             'object': obj
#         })
