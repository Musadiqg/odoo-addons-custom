# -*- coding: utf-8 -*-
# from odoo import http


# class ImportJournalItems(http.Controller):
#     @http.route('/import_journal_items/import_journal_items', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/import_journal_items/import_journal_items/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('import_journal_items.listing', {
#             'root': '/import_journal_items/import_journal_items',
#             'objects': http.request.env['import_journal_items.import_journal_items'].search([]),
#         })

#     @http.route('/import_journal_items/import_journal_items/objects/<model("import_journal_items.import_journal_items"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('import_journal_items.object', {
#             'object': obj
#         })
