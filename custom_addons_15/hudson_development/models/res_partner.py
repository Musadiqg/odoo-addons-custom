import requests
from datetime import date, datetime, time
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError, ValidationError, _logger
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class ResPartner(models.Model):
    _inherit = 'res.partner'

    exemption_date = fields.Date("Exemption Date", default=False)
