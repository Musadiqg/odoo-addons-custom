import requests
from datetime import date, datetime, time
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)  # Get the logger for this module
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    def set_fiscal_cron(self):
        fiscal_postions = self.env['account.fiscal.position'].search([])
        for fiscal in fiscal_postions:
            customers = self.env['res.partner'].search(
                [('x_studio_partner_type', '=', 'Customer'), ('property_account_position_id.id', '=', fiscal.id)])
            if customers:
                # _logger.info('Customers=====================')
                for customer in customers:
                    wht_fp = customer.property_account_position_id.name + " " + 'WHT'
                    wht_fiscal = self.env['account.fiscal.position'].search([('name', '=', wht_fp)])
                    # _logger.info('WHT Fiscals =====================')
                    for f in wht_fiscal:
                        if f.tax_ids:
                            for tax in f.tax_ids:
                                fiscal.write({'tax_ids': [(4, tax.id)]})
                                # _logger.info('Fiscal updated',fiscal.id,"customer::",customer.name)
                                if fiscal.tax_ids:
                                    _logger.info('Fiscal updated', fiscal.id, "customer::", customer.name)
                                    # print("Customer ::",customer.name,"Fiscal::",fiscal.id)

    def _run_fiscal_cron(self):
        fiscal_postions = self.env['account.fiscal.position'].search([])
        fiscal_postions = fiscal_postions.filtered(
            lambda f: f.tax_ids.ids in [64, 67, 74, 75, 76, 77, 121, 122, 123, 136, 150, 324, 340])
        for fiscal in fiscal_postions:
            for tax in fiscal.tax_ids:
                if tax.tax_dest_id:
                    # if 'Income' in tax.tax_dest_id.name:
                    old_income_tax_list_ids = [(2, tax.id)]
                    new_income_tax_list_ids = [(2, tax.id)]
                    # self.create_fiscal_income_tax(tax, fiscal)
                    fiscal.write({'tax_ids': old_income_tax_list_ids})

    def create_fiscal_income_tax(self, tax, fiscal):
        fiscal_position = self.env['account.fiscal.position'].create({
            'name': fiscal.name + " " + 'WHT',
            'company_id': fiscal.company_id.id,
            'tax_ids': [
                (0, None, {
                    'tax_src_id': tax.tax_src_id.id,
                    'tax_dest_id': tax.tax_dest_id.id,
                }),
            ],
        })
