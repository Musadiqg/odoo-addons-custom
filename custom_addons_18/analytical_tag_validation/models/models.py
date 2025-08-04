# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        if self.order_line.filtered(lambda l: not l.analytic_distribution):
            raise ValidationError("Missing mandatory field in Order line: Analytic Distribution")
        return super().action_confirm()


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        if self.order_line.filtered(lambda x: not x.analytic_distribution):
            raise ValidationError("Missing mandatory field in Order line: Analytic Distribution")
        return super().button_confirm()


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        if not self.asset_id:
            # Lines requiring distribution (e.g., income, cost of goods sold)
            tag_lines = self.line_ids.filtered(lambda x: x.account_id.account_type in ('income', 'cost_of_goods_sold'))
            if tag_lines.filtered(lambda i: not i.analytic_distribution):
                raise ValidationError("Missing mandatory field in lines: Analytic Distribution")

            # Lines requiring distribution (e.g., expenses)
            tag_acc_lines = self.line_ids.filtered(lambda x: x.account_id.account_type == 'expense')
            if tag_acc_lines.filtered(lambda i: not i.analytic_distribution):
                raise ValidationError("Missing mandatory field in lines: Analytic Distribution")

            # Lines requiring distribution (e.g., depreciation)
            acc_lines = self.line_ids.filtered(lambda x: x.account_id.account_type == 'expense_depreciation')
            if acc_lines.filtered(lambda i: not i.analytic_distribution):
                raise ValidationError("Missing mandatory field in lines: Analytic Distribution")
        return super().action_post()