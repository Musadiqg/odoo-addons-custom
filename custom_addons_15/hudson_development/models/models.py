# -*- coding: utf-8 -*-
import re

import requests
from datetime import date, datetime, time
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError, ValidationError, _logger
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class hudson_development(models.Model):
    _name = 'hudson_development.hudson_development'
    _description = 'hudson_development.hudson_development'


class StockQuant(models.Model):
    _name = 'stock.quant.backup'
    _inherit = 'stock.quant'


class ConfirmationWizard(models.TransientModel):
    _name = 'confirmation.wizard'

    def _get_eval(self):
        if self.env.context.get('move'):
            IDS = self.env.context.get('move')
            var = ''
            for ID in IDS:
                move = self.env['stock.move'].browse(ID)
                if move.picking_id.state == 'assigned':
                    var += str(move.id)+"-"+move.picking_id.name+":" +move.product_id.name+","
            return var

    text = fields.Char(string="Message", readonly=True,
                       default="Below are the documents which have already reserved qty")
    name_move = fields.Char("Documents", default=_get_eval, readonly=True)

    def unreserve(self):
        list = self.name_move.split(',')
        IDs = []
        if list:
            for origin in list:
                if origin != '':
                    ID = origin.split("-")[0]
                    ID = int(ID)
                    IDs.append(ID)
            for id in IDs:
                picking = self.env['stock.picking'].search([('move_lines','in',id)])
                if picking.exists():
                    picking.do_unreserve()

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _prepare_invoice(self):
        res = super(PurchaseOrder, self)._prepare_invoice()
        if self.company_id.id == 8:
            res['journal_id'] = 693  # Purchase Register for Nutrition Division
        return res