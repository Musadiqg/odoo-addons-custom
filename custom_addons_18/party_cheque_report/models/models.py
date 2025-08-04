# -*- coding: utf-8 -*-

from odoo import models, fields, api


# class party_cheque_report(models.Model):
#     _name = 'party_cheque_report.party_cheque_report'
#     _description = 'party_cheque_report.party_cheque_report'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

class Account(models.Model):
    _inherit = 'account.account'

    is_srb_account_20 = fields.Boolean('Is SRB 20% Account', default=False)