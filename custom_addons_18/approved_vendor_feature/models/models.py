# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from dateutil import relativedelta
class AccountMove(models.Model):
    _inherit = 'account.move'

    def _cron_post_assets(self):
        # Calculate the date range for filtering assets
        today = fields.Date.today()
        first_day_of_current_month = today.replace(day=1)
        last_day_of_last_month = (first_day_of_current_month - relativedelta.relativedelta(days=1))
        # Fetch draft asset entries with depreciation date matching the criteria
        draft_entries = self.env['account.move'].search([
            ('state', '=', 'draft'),
            ('asset_id', '!=', False),
            ('date', '=', last_day_of_last_month) 
        ])
        # raise ValidationError(len(draft_entries))
        # draft_entries = self.env['account.move'].browse(499654)
        for move in draft_entries:
            move.action_post()
            move.x_studio_asset_post = True
class ResPartner(models.Model):
    _inherit = 'res.partner'

    # is_approved_vendor = fields.Boolean('Approved Vendor',default=False)
    #
    # def write(self, vals):
    #     res = super(ResPartner, self).write(vals)
    #     can_approve = False
    #     if self.env.context.get('uid'):
    #         login_user = self.env['res.users'].browse(self.env.context.get('uid'))
    #         if login_user.has_group('approved_vendor_feature.group_account_approve_vendor'):
    #             can_approve = True
    #     if self.company_id.id == 5 and self.x_studio_partner_type == 'Supplier':
    #         if vals.get('is_approved_vendor') and not can_approve:
    #             raise ValidationError('You are not allowed to perform this operation')
    #     return res


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    approve_by = fields.Char('Approved By',compute="get_approver")

    @api.depends('state')
    def get_approver(self):
        for record in self:
            record.approve_by = False
            if record.state not in ['draft','cancel','sent']:
                group = self.env['res.groups'].browse(174)
                x = record.message_ids.filtered(lambda l:l.create_uid in group.users and l.subtype_id.name in ['RFQ Done','RFQ Purchase Order'])
                if len(x) == 1:
                    record.approve_by = x.author_id.name
                # else:
                #     x = record.message_ids.filtered(
                #         lambda l: l.record_name == record.name and l.subtype_id.name in ['RFQ Done'])
                #     if len(x) == 1:
                #         record.approve_by = x.author_id.name

    # @api.onchange('partner_id')
    # def check_approve_vendor(self):
    #     if self.partner_id and self.company_id.id == 5:
    #         if not self.partner_id.is_approved_vendor:
    #             raise ValidationError('You are selecting un approve vendor')