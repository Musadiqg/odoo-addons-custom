# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        if res:
            if self.order_line.filtered(lambda l: not l.analytic_tag_ids):
                raise ValidationError("Missing mandatory field in Order line: Analytic Tag")
        return res


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        if self.order_line.filtered(lambda x: not x.analytic_tag_ids):
            raise ValidationError("Missing mandatory field in line: Analytic Tag")
        if self.order_line.filtered(lambda x: not x.account_analytic_id):
            raise ValidationError("Missing mandatory field in Order line: Analytic Account")
        return res


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):

        if not self.asset_id:
            tag_lines = self.line_ids.filtered(lambda x: x.account_id.user_type_id.name == 'Income' or  x.account_id.user_type_id.name == 'Cost of Revenue')
            if tag_lines.filtered(lambda i: not i.analytic_tag_ids):
                raise ValidationError("Missing mandatory field in lines: Analytic Tag")

            tag_acc_lines = self.line_ids.filtered(lambda x: x.account_id.user_type_id.name == 'Expenses')
            if tag_acc_lines.filtered(lambda i: not i.analytic_tag_ids):
                raise ValidationError("Missing mandatory field in lines: Analytic Tag")
            if tag_acc_lines.filtered(lambda i: not i.analytic_account_id):
                raise ValidationError("Missing mandatory field in lines: Analytic Account")

            acc_lines = self.line_ids.filtered(lambda x: x.account_id.user_type_id.name == 'Depreciation')
            if acc_lines.filtered(lambda i: not i.analytic_account_id):
                raise ValidationError("Missing mandatory field in lines: Analytic Account")
        res = super(AccountMove, self).action_post()
        return res
