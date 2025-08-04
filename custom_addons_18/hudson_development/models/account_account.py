from odoo import SUPERUSER_ID, _, api, fields, models


class Account(models.Model):
    _inherit = 'account.account'

    is_wht_account = fields.Boolean('Is WHT Account', default=False)
    is_sti_account = fields.Boolean('Is Sales Tax Account', default=False)
    is_srb_account = fields.Boolean('Is SRB 100 % Tax Account', default=False)
