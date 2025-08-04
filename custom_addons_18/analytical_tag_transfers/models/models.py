# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_tag_trasnfer = fields.Boolean("Tag Transfer", compute="_compute_is_tag_trasnfer")
    analytic_tags = fields.Many2one(
        'account.analytic.account',
        string="Analytic Tag",
        domain="[('plan_id', '=', 2)]",
        help="Select one analytic tag for this picking",
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string="Analytic Account",
        domain="[('plan_id', '=', 1)]",  # plan id one is accountds, plan id 2 is tags 
        help="Select an analytic account for this picking",
    )

    @api.depends('location_dest_id')
    def _compute_is_tag_trasnfer(self):
        for rec in self:
            rec.is_tag_trasnfer = rec.location_dest_id.id in [40, 38, 18, 50]


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def create(self, vals):
        res = super(AccountMove, self).create(vals)
        if res.stock_move_id.picking_id and res.stock_move_id.picking_id.is_tag_trasnfer:
            for line in res.line_ids:
                distribution = {}
                # Assigning  100% to analytic_account_id as per current practice, including tags only for reference
                if res.stock_move_id.picking_id.analytic_account_id:
                    distribution[str(res.stock_move_id.picking_id.analytic_account_id.id)] = 100.0
                
                if res.stock_move_id.picking_id.analytic_tags:
                    line.distribution_analytic_account_ids = [(4, res.stock_move_id.picking_id.analytic_tags.id)]
                if distribution:
                    line.analytic_distribution = distribution
                elif res.stock_move_id.picking_id.analytic_account_id:
                    line.analytic_account_id = res.stock_move_id.picking_id.analytic_account_id
        return res