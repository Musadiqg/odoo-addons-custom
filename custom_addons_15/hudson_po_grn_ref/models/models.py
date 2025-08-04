# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    pname = fields.Char(compute='_compute_pname',string="PO Reference")

    def _compute_pname(self):
        for record in self:
            record.pname = False
            if record.ref:
                res = self.env['stock.picking'].search([('name', 'like', record.ref)], limit=1)
                if res:
                    if res.picking_type_code == 'incoming' and "PO" in res.origin:
                        record.pname = res.origin
