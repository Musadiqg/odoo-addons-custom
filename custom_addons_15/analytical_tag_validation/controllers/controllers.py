# -*- coding: utf-8 -*-
# from odoo import http


# class AnalyticalTagValidation(http.Controller):
#     @http.route('/analytical_tag_validation/analytical_tag_validation', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/analytical_tag_validation/analytical_tag_validation/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('analytical_tag_validation.listing', {
#             'root': '/analytical_tag_validation/analytical_tag_validation',
#             'objects': http.request.env['analytical_tag_validation.analytical_tag_validation'].search([]),
#         })

#     @http.route('/analytical_tag_validation/analytical_tag_validation/objects/<model("analytical_tag_validation.analytical_tag_validation"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('analytical_tag_validation.object', {
#             'object': obj
#         })
