from odoo import api, models
from odoo.exceptions import ValidationError

# Constraint for Purchase Order (vendor check)
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.constrains('partner_id', 'company_id')
    def _check_vendor_company(self):
        for order in self:
            if order.partner_id.company_id and order.partner_id.company_id != order.company_id:
                raise ValidationError(
                    f"The vendor '{order.partner_id.name}' belongs to company "
                    f"'{order.partner_id.company_id.name}', which does not match "
                    f"the purchase order company '{order.company_id.name}'."
                )

# Constraints for Purchase Order Line (product and tax checks)
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.constrains('product_id', 'company_id')
    def _check_product_company(self):
        for line in self:
            if line.product_id.company_id and line.product_id.company_id != line.company_id:
                raise ValidationError(
                    f"The product '{line.product_id.name}' belongs to company "
                    f"'{line.product_id.company_id.name}', which does not match "
                    f"the purchase order company '{line.company_id.name}'."
                )

    @api.constrains('taxes_id', 'company_id')
    def _check_taxes_company(self):
        for line in self:
            for tax in line.taxes_id:
                if tax.company_id != line.company_id:
                    raise ValidationError(
                        f"The tax '{tax.name}' belongs to company '{tax.company_id.name}', "
                        f"which does not match the purchase order company '{line.company_id.name}'."
                    )

# Constraint for Stock Move (product check in receipts)
class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.constrains('product_id', 'company_id')
    def _check_product_company(self):
        for move in self:
            if move.product_id.company_id and move.product_id.company_id != move.company_id:
                raise ValidationError(
                    f"The product '{move.product_id.name}' belongs to company "
                    f"'{move.product_id.company_id.name}', which does not match "
                    f"the stock move company '{move.company_id.name}'."
                )