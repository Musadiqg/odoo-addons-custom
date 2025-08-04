# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_tag_trasnfer = fields.Boolean("", compute="get_eval")
    analytic_tags = fields.Many2one('account.analytic.tag', string="Analytic Tag")
    analytic_account_id = fields.Many2one("account.analytic.account",string="Analytic Account")

    def get_eval(self):
        for rec in self:
            if rec.location_dest_id.id in [40, 38, 18, 50]:
                rec.is_tag_trasnfer = True
            else:
                rec.is_tag_trasnfer = False


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def create(self,vals):
        res = super(AccountMove, self).create(vals)
        if res.stock_move_id.picking_id and res.stock_move_id.picking_id.is_tag_trasnfer:
            for line in res.line_ids:
                line.analytic_tag_ids = res.stock_move_id.picking_id.analytic_tags
                line.analytic_account_id = res.stock_move_id.picking_id.analytic_account_id
        return res
