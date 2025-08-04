# -*- coding: utf-8 -*-
# from odoo import http


# class DevImportLcRecordings(http.Controller):
#     @http.route('/dev_import_lc_recordings/dev_import_lc_recordings', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/dev_import_lc_recordings/dev_import_lc_recordings/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('dev_import_lc_recordings.listing', {
#             'root': '/dev_import_lc_recordings/dev_import_lc_recordings',
#             'objects': http.request.env['dev_import_lc_recordings.dev_import_lc_recordings'].search([]),
#         })

#     @http.route('/dev_import_lc_recordings/dev_import_lc_recordings/objects/<model("dev_import_lc_recordings.dev_import_lc_recordings"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('dev_import_lc_recordings.object', {
#             'object': obj
#         })
