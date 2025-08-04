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

    @api.depends('product_id', 'move_id.ref', 'move_id.payment_reference')
    def _compute_name(self):
        """to keep odoo15 logic."""
        def get_name(line):
            values = []
            if line.partner_id.lang:
                product = line.product_id.with_context(lang=line.partner_id.lang)
            else:
                product = line.product_id
            if not product:
                return False
            # Use partner_ref like Odoo 15, instead of display_name
            if product.partner_ref:
                values.append(product.partner_ref)
            if line.move_id.journal_id.type == 'sale':
                if product.description_sale:
                    values.append(product.description_sale)
            elif line.move_id.journal_id.type == 'purchase':
                if product.description_purchase:
                    values.append(product.description_purchase)
            return '\n'.join(values) if values else False

        term_by_move = (self.move_id.line_ids | self).filtered(lambda l: l.display_type == 'payment_term').sorted(lambda l: l.date_maturity or date.max).grouped('move_id')
        for line in self.filtered(lambda l: l.move_id.inalterable_hash is False):
            if line.display_type == 'payment_term':
                # Keep Odoo 18's payment term logic
                term_lines = term_by_move.get(line.move_id, self.env['account.move.line'])
                n_terms = len(line.move_id.invoice_payment_term_id.line_ids)
                if line.move_id.payment_reference and line.move_id.ref and line.move_id.payment_reference != line.move_id.ref:
                    name = f'{line.move_id.ref} - {line.move_id.payment_reference}'
                else:
                    name = line.move_id.payment_reference or False
                if n_terms > 1:
                    index = term_lines._ids.index(line.id) if line in term_lines else len(term_lines)
                    name = _('%(name)s installment #%(number)s', name=name if name else '', number=index + 1).lstrip()
                if n_terms > 1 or not line.name or line._origin.name == line._origin.move_id.payment_reference or (
                    line._origin.move_id.payment_reference and line._origin.move_id.ref
                    and line._origin.name == f'{line._origin.move_id.ref} - {line._origin.move_id.payment_reference}'
                ):
                    line.name = name
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue
            if not line.name or line._origin.name == get_name(line._origin):
                line.name = get_name(line)

    def _get_computed_price_unit(self):
        ''' Helper to get the default price unit based on the product by taking care of the taxes
        set on the product and the fiscal position.
        :return: The price unit.
        '''
        self.ensure_one()

        if not self.product_id:
            return 0.0
        if self.move_id.is_sale_document(include_receipts=True):
            document_type = 'sale'
        elif self.move_id.is_purchase_document(include_receipts=True):
            document_type = 'purchase'
        else:
            document_type = 'other'

        return self.product_id._get_tax_included_unit_price(
            self.move_id.company_id or self.env.company,
            self.move_id.currency_id or self.env.company.currency_id,
            self.move_id.date or fields.Date.today(),
            document_type,
            fiscal_position=self.move_id.fiscal_position_id,
            product_uom=self.product_uom_id
        )

    def _get_computed_account(self):
            """Replicate _get_computed_account logic."""
            self.ensure_one()
            self = self.with_company(self.move_id.journal_id.company_id)
            if not self.product_id:
                return
            fiscal_position = self.move_id.fiscal_position_id
            accounts = self.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
            if self.move_id.is_sale_document(include_receipts=True):
                return accounts['income'] or self.account_id
            elif self.move_id.is_purchase_document(include_receipts=True):
                return accounts['expense'] or self.account_id

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue
            # Remove line.name assignment; let _compute_name handle it
            line.account_id = line._get_computed_account()
            taxes = line._get_computed_taxes()
            if taxes and line.move_id.fiscal_position_id:
                if self.company_id.id != 1:
                    taxes = line.move_id.fiscal_position_id.map_tax(taxes)
                else:
                    taxes = line.move_id.fiscal_position_id.x_map_tax(taxes, line)
            line.tax_ids = taxes
            #line.product_uom_id = line._get_computed_uom()
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
                taxes = line.product_id.taxes_id.filtered(lambda t: t.company_id == line.env.company)
                if self.company_id.id != 1:
                    line.tax_id = fpos.map_tax(taxes)
                else:
                    if line.product_id:  # Only validate if product is set
                        if not line.product_id.product_tmpl_id.x_status:
                            line = False
                            raise ValidationError("Please define product nature. Hint: Pharma or Cosmo")
                        elif not line.order_id.partner_id.x_status:
                            line.order_id.partner_id = False
                            raise ValidationError("Please define Customer nature. Hint: Registered or Un-Registered")
                        else:
                            line.tax_id = fpos.x_map_tax(taxes, line)
                    else:
                        line.tax_id = False


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
                # 1) Keep only taxes named in list1
                # 2) Plus any taxes that have is_otc=True
                result = result.filtered(lambda tax: tax.name in list1) + result.filtered(lambda tax: tax.is_otc)
                self.update_sequences_5(result, list1)

            # FIXED: remove the leading space, plus use list1 instead of list2
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
        lines_with_distribution = res.line_ids.filtered(lambda l: l.analytic_distribution)
        if lines_with_distribution:
            merged_distribution = {}
            default_plan = self.env['account.analytic.plan'].search([('name', '=', 'Default upg')], limit=1)
            if not default_plan:
                _logger.error("Default UPG plan not found")
                return res

            # Step 1: Collect distributions from all lines, keeping original percentages
            for line in lines_with_distribution:
                for account_key, percentage in line.analytic_distribution.items():
                    account_ids = [int(aid.strip()) for aid in account_key.split(',') if aid.strip()]
                    valid_accounts = self.env['account.analytic.account'].search([
                        ('id', 'in', account_ids),
                        ('plan_id', '=', default_plan.id)
                    ])
                    for account in valid_accounts:
                        if account.id not in merged_distribution:
                            merged_distribution[account.id] = float(percentage)
                        else:
                            merged_distribution[account.id] += float(percentage)

            # Step 2: Cap at 100% without normalizing ratios
            total = sum(merged_distribution.values())
            if total > 100:
                # Sort by percentage descending to prioritize higher values
                sorted_dist = sorted(merged_distribution.items(), key=lambda x: x[1], reverse=True)
                capped_dist = {}
                remaining = 100.0
                for acc_id, perc in sorted_dist:
                    if remaining >= perc:
                        capped_dist[acc_id] = perc  # Keep original percentage
                        remaining -= perc
                    elif remaining > 0:
                        capped_dist[acc_id] = remaining  # Take what’s left
                        remaining = 0
                    else:
                        break  # Stop once 100% is reached
                merged_distribution = capped_dist
            # Else: Keep unnormalized if total <= 100

            # Step 3: Apply to lines with account_id 4202
            for line in res.line_ids.filtered(lambda i: i.account_id.id == 4202 and not i.analytic_distribution):
                line.analytic_distribution = merged_distribution
        return res
    