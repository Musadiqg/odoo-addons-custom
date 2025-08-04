# -*- coding: utf-8 -*-

from odoo import models, fields, api



class StockQuantityHistory(models.TransientModel):
    _inherit = 'stock.quantity.history'

    # location_id = fields.Many2one('stock.location')
    # include_child_locations = fields.Boolean('Child Locations')

class avg_cost_report(models.Model):
    _name = 'avg_cost_report.avg_cost_report'
    _description = 'avg_cost_report.avg_cost_report'


#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

class FiscalPosition(models.Model):
    _inherit = 'account.account'

    def set_tax_(self):
        fiscal_postions = self.env['account.fiscal.position.tax'].search([])
        for f in fiscal_postions:
            f.x_studio_field_NJLfU = f.tax_dest_id.amount
        # fiscal_postions = fiscal_postions.filtered(
        #     lambda f: f.tax_ids.id in [64, 67, 74, 75, 76, 77, 121, 122, 123, 136, 150, 324, 340])
        # for f in fiscal_postions:
        #     # x = f.tax_ids.filtered(lambda t: t.tax_dest_id.id == 85 or t.tax_dest_id.id == 238)
        #     x = f.tax_ids.filtered(lambda t: t.tax_dest_id.id in [64])
        #     # taxes = self.env['account.tax'].browse([399])
        #     if x:
        #         a = self.env['account.fiscal.position.tax'].create({
        #             'tax_src_id': 95 ,
        #             'tax_dest_id': 399,
        #             'position_id': f.id,
        #         })
        #     # f.tax_ids.filtered(lambda t: t.tax_dest_id.id == 85 or t.tax_dest_id.id == 238).unlink()
        #     f.tax_ids.filtered(lambda t: t.tax_dest_id.id in [64]).unlink()
        #     f.x_is_updated = True

        fiscal_postions = self.env['account.fiscal.position'].search([])
        # fiscal_postions = self.env['account.fiscal.position'].browse(2518)
        for f in fiscal_postions:
            # x = f.tax_ids.filtered(lambda t: t.tax_dest_id.id in [64])
            y = self.env['account.fiscal.position.tax'].search([('position_id', '=', f.id), ('tax_dest_id', '=', 64)])
            if y:
                old_income_tax_list_ids = [(2, 64)]
                new_income_tax_list_ids = [(4, 384)]
                f.write({'tax_ids': old_income_tax_list_ids})
                f.write({'tax_ids': new_income_tax_list_ids})
                print()
                # a = self.env['account.fiscal.position.tax'].create({
                #     'tax_src_id': 95,
                #     'tax_dest_id': 399,
                #     'position_id': f.id,
                # })
                # f.tax_ids.filtered(lambda t: t.tax_dest_id.id in [64]).unlink()
