# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _get_tax_included_unit_price(self, company, currency, document_date, document_type,
                                     is_refund_document=False, product_uom=None, product_currency=None,
                                     product_price_unit=None, product_taxes=None, fiscal_position=None
                                     ):
        """ Helper to get the price unit from different models.
            This is needed to compute the same unit price in different models (sale order, account move, etc.) with same parameters.
        """

        product = self

        assert document_type

        if product_uom is None:
            product_uom = product.uom_id
        if not product_currency:
            if document_type == 'sale':
                product_currency = product.currency_id
            elif document_type == 'purchase':
                product_currency = company.currency_id
        if product_price_unit is None:
            if document_type == 'sale':
                product_price_unit = product.with_company(company).lst_price
            elif document_type == 'purchase':
                product_price_unit = product.with_company(company).standard_price
            else:
                return 0.0
        if product_taxes is None:
            if document_type == 'sale':
                product_taxes = product.taxes_id.filtered(lambda x: x.company_id == company)
            elif document_type == 'purchase':
                product_taxes = product.supplier_taxes_id.filtered(lambda x: x.company_id == company)
        # Apply unit of measure.
        if product_uom and product.uom_id != product_uom:
            product_price_unit = product.uom_id._compute_price(product_price_unit, product_uom)

        # Apply fiscal position.
        if product_taxes and fiscal_position:
            product_taxes_after_fp = False
            ctx = self.env.context
            if ctx.get('default_move_type') == 'out_invoice' and self.company_id.id == 1:
                if self.company_id.id == 1:
                    vals = {'partner_id': ctx.get('default_partner_id'), 'product_id': self.id}
                    product_taxes_after_fp = fiscal_position.x_map_tax(product_taxes, vals)
            else:
                product_taxes_after_fp = fiscal_position.map_tax(product_taxes)
            flattened_taxes_after_fp = product_taxes_after_fp._origin.flatten_taxes_hierarchy() if product_taxes_after_fp else False
            flattened_taxes_before_fp = product_taxes._origin.flatten_taxes_hierarchy()
            taxes_before_included = all(tax.price_include for tax in flattened_taxes_before_fp)

            if product_taxes_after_fp:
                if set(product_taxes.ids) != set(product_taxes_after_fp.ids) and taxes_before_included:
                    taxes_res = flattened_taxes_before_fp.compute_all(
                        product_price_unit,
                        quantity=1.0,
                        currency=currency,
                        product=product,
                        is_refund=is_refund_document,
                    )
                    product_price_unit = taxes_res['total_excluded']

                    if any(tax.price_include for tax in flattened_taxes_after_fp):
                        taxes_res = flattened_taxes_after_fp.compute_all(
                            product_price_unit,
                            quantity=1.0,
                            currency=currency,
                            product=product,
                            is_refund=is_refund_document,
                            handle_price_include=False,
                        )
                        for tax_res in taxes_res['taxes']:
                            tax = self.env['account.tax'].browse(tax_res['id'])
                            if tax.price_include:
                                product_price_unit += tax_res['amount']

        # Apply currency rate.
        if currency != product_currency:
            product_price_unit = product_currency._convert(product_price_unit, currency, company, document_date)

        return product_price_unit


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue

            line.name = line._get_computed_name()
            line.account_id = line._get_computed_account()
            taxes = line._get_computed_taxes()
            if taxes and line.move_id.fiscal_position_id:
                if self.company_id.id != 1:
                    taxes = line.move_id.fiscal_position_id.map_tax(taxes)
                else:
                    taxes = line.move_id.fiscal_position_id.x_map_tax(taxes, line)
            line.tax_ids = taxes
            line.product_uom_id = line._get_computed_uom()
            line.price_unit = line._get_computed_price_unit()

    @api.onchange('product_uom_id')
    def _onchange_uom_id(self):
        ''' Recompute the 'price_unit' depending of the unit of measure. '''
        if self.display_type in ('line_section', 'line_note'):
            return
        taxes = self._get_computed_taxes()
        if taxes and self.move_id.fiscal_position_id:
            if self.company_id.id != 1:
                taxes = self.move_id.fiscal_position_id.map_tax(taxes)
            else:
                taxes = self.move_id.fiscal_position_id.x_map_tax(taxes, self)
        self.tax_ids = taxes
        self.price_unit = self._get_computed_price_unit()

    @api.onchange('account_id')
    def _onchange_account_id(self):
        ''' Recompute 'tax_ids' based on 'account_id'.
        /!\ Don't remove existing taxes if there is no explicit taxes set on the account.
        '''
        for line in self:
            if not line.display_type and (line.account_id.tax_ids or not line.tax_ids):
                taxes = line._get_computed_taxes()

                if taxes and line.move_id.fiscal_position_id:
                    if self.company_id.id != 1:
                        taxes = line.move_id.fiscal_position_id.map_tax(taxes)
                    else:
                        taxes = line.move_id.fiscal_position_id.x_map_tax(taxes, line)

                line.tax_ids = taxes


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('partner_id')
    def check_nature(self):
        if self.company_id == 1:
            if self.partner_id and not self.partner_id.x_status:
                raise ValidationError("Please define Customer nature. Hint: Registered or Un-Registered")


class Partner(models.Model):
    _inherit = 'res.partner'

    x_status = fields.Selection([('filer', 'Yes'), ('non_filer', 'No')], default='filer',string="Applicable for further tax")


class Product(models.Model):
    _inherit = 'product.template'

    x_status = fields.Selection([('pharma', 'Pharma'), ('cosmo', 'Cosmo'), ('otc', 'OTC Eye'), ('otc-pharma', 'OTC Pharma')], default='pharma', string="Product Status")


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _compute_tax_id(self):
        for line in self:
            line = line.with_company(line.company_id)
            fpos = line.order_id.fiscal_position_id or line.order_id.fiscal_position_id.get_fiscal_position(
                line.order_partner_id.id)
            # If company_id is set, always filter taxes by the company
            taxes = line.product_id.taxes_id.filtered(lambda t: t.company_id == line.env.company)
            if self.company_id.id != 1:
                line.tax_id = fpos.map_tax(taxes)
            else:
                if not line.product_id.x_status:
                    line = False
                    raise ValidationError("Please define product nature. Hint: Pharma or Cosmo")
                elif not line.order_id.partner_id.x_status:
                    line.order_id.partner_id = False
                    raise ValidationError("Please define Customer nature. Hint: Registered or Un-Registered")
                else:
                    line.tax_id = fpos.x_map_tax(taxes, line)


class Fiscal(models.Model):
    _inherit = 'account.fiscal.position'

    def x_map_tax(self, taxes, line):
        if not self:
            return taxes
        result = self.env['account.tax']
        for tax in taxes:
            taxes_correspondance = self.tax_ids.filtered(lambda t: t.tax_src_id == tax._origin)
            result |= taxes_correspondance.tax_dest_id if taxes_correspondance else tax

        list1 = ['Sales Tax - Pharma (1%)', 'Sales Tax - Pharma (Minus 1%)']

        list2 = ['Sales Tax - Pharma (1%)', 'Further Tax - Pharma (3%)','Further Tax - Pharma (3%) (Sales)', 'Sales Tax - Pharma (Minus 1%)',
                 'Further Tax - Pharma (Minus 3%)','Further Tax - Pharma (Minus 3%) (Sales)']

        if type(line) != dict:
            if line._table == 'account_move_line':
                partner_id = line.partner_id
            elif line._table == "sale_order_line":
                partner_id = line.order_id.partner_id
            product_status = line.product_id.x_status
        else:
            product_status = self.env['product.product'].browse(line.get('product_id')).x_status
            partner_id = self.env['res.partner'].browse(line.get('partner_id'))

        if type(line) != dict:
            if product_status == 'pharma' and partner_id.x_status == 'filer':
                result = result.filtered(lambda tax: tax.name in list1) + result.filtered(lambda tax: tax.is_income_tax)
                self.update_sequences_1(result, list1)

            if product_status == 'pharma' and partner_id.x_status == 'non_filer':
                result = result.filtered(lambda tax: tax.name in list2) + result.filtered(lambda tax: tax.is_income_tax)
                self.update_sequences_2(result, list2)
            if product_status == 'cosmo' and partner_id.x_status == 'filer':
                result = result.filtered(lambda tax: tax.is_cosmo_income_tax) + line.product_id.taxes_id.filtered(
                    lambda t: t.amount_type == 'fixed')
                self.update_sequences_3(result)
            if product_status == 'cosmo' and partner_id.x_status == 'non_filer':
                result = result.filtered(lambda tax: tax.is_cosmo_income_tax) + line.product_id.taxes_id.filtered(
                    lambda t: t.amount_type == 'fixed')
                self.update_sequences_4(result)
            if product_status == 'otc' and partner_id.x_status == 'filer':
                result = result.filtered(lambda tax: tax.is_cosmo_income_tax) + line.product_id.taxes_id.filtered(lambda t: t.is_otc)
                self.update_sequences_4(result)
            if product_status == 'otc' and partner_id.x_status == 'non_filer':
                result = result.filtered(lambda tax: tax.is_cosmo_income_tax) + line.product_id.taxes_id.filtered(lambda t: t.is_otc)
                self.update_sequences_4(result)

            if product_status == 'otc-pharma' and partner_id.x_status == 'filer':
                result = result.filtered(lambda tax: tax.name in list1) + result.filtered(lambda tax: tax.is_otc)
                self.update_sequences_5(result, list1)

            if product_status == 'otc-pharma' and partner_id.x_status == 'non_filer':
                result = result.filtered(lambda tax: tax.name in list1) + result.filtered(lambda tax: tax.is_otc)
                self.update_sequences_5(result, list1)


            return result

    def update_sequences_1(self, result, list1):
        sales_tax_1 = result.filtered(lambda l: l.name == list1[0])
        sales_tax_1.write({'sequence': 1})
        adv_0_1 = result.filtered(lambda l: l.is_income_tax)
        adv_0_1.write({'sequence': 2})
        sales_tax_minus_1 = result.filtered(lambda l: l.name == list1[1])
        sales_tax_minus_1.write({'sequence': 3})

    def update_sequences_2(self, result, list2):
        sales_tax_1 = result.filtered(lambda l: l.name == list2[0])
        sales_tax_1.write({'sequence': 1})
        further_3 = result.filtered(lambda l: l.name == list2[1])
        further_3.write({'sequence': 2})
        adv_0_1 = result.filtered(lambda l: l.is_income_tax)
        adv_0_1.write({'sequence': 3})
        sales_tax_minus_1 = result.filtered(lambda l: l.name == list2[2])
        sales_tax_minus_1.write({'sequence': 4})
        further_minus_3 = result.filtered(lambda l: l.name == list2[3])
        further_minus_3.write({'sequence': 4})

    def update_sequences_3(self, result):
        gst_18 = result.filtered(lambda l: l.is_cosmo_income_tax)
        gst_18.write({'sequence': 2})
        product_tax = result.filtered(lambda l: l.amount_type == 'fixed')
        product_tax.write({'sequence': 1})

    def update_sequences_4(self, result):
        gst_18 = result.filtered(lambda l: l.is_cosmo_income_tax)
        gst_18.write({'sequence': 2})
        product_tax = result.filtered(lambda l: l.amount_type == 'fixed')
        product_tax.write({'sequence': 1})

    def update_sequences_5(self, result, list1):
        tax_1 = result.filtered(lambda l: l.name == list1[0])
        tax_1.write({'sequence': 1})
        tax_2 = result.filtered(lambda l: l.name == list1[1])
        tax_2.write({'sequence': 2})
        otc_taxes = result.filtered(lambda l: l.is_otc)
        for idx, tax in enumerate(otc_taxes, start=3):  # Fixed: Start at 3
            tax.write({'sequence': idx})


class AccountTax(models.Model):
    _inherit = 'account.tax'

    is_income_tax = fields.Boolean("Adv Income Tax 236G&H (Pharma)", default=False)
    is_cosmo_income_tax = fields.Boolean("Adv Income Tax 236G&H (Cosmo)", default=False)
    is_otc = fields.Boolean("Applicable for OTC Eye Invoices", default=False)

    def set_new_taxes(self):
        customers = self.env['res.partner'].search([('x_studio_partner_type', '=', 'Customer')])
        taxes = ['Sales Tax - Pharma (1%)', 'Further Tax - Pharma (3%)',
                 'Sales Tax - Pharma (Minus 1%)', 'Further Tax - Pharma (Minus 3%)','Further Tax - Pharma (Minus 3%) (Sales)','Further Tax - Pharma (3%) (Sales)']
        taxes_ids = self.env['account.tax'].search([('name', 'in', taxes)])
        for f in customers.property_account_position_id:
            for tax in taxes_ids:
                if tax:
                    x_f = self.env['account.fiscal.position.tax'].create({
                        'tax_src_id': 99,
                        'tax_dest_id': tax.id,
                        'position_id': f.id,
                    })


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def create(self, vals_list):
        res = super(AccountMove, self).create(vals_list)
        tags = res.line_ids.filtered(lambda l: l.analytic_tag_ids).analytic_tag_ids
        for line in res.line_ids.filtered(lambda i:i.account_id.id == 4202 and not i.analytic_tag_ids):
            for tag in tags:
                line.write({'analytic_tag_ids': [(4, tag.id)]})
        return res