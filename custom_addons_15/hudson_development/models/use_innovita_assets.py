from odoo import fields, models

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    use_innovita_assets = fields.Boolean(
        string="Use Innovita Assets",
        default=False,
        help="If checked, use Innovita's assets in the report instead of Hudson's."
    )

    use_hudson_assets = fields.Boolean(
        string="Use Hudson Assets",
        default=False,
        help="If checked, use Hudson's assets in the report instead of Innovita's."
    )
