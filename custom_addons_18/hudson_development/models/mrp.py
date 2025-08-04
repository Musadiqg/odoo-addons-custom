from odoo import SUPERUSER_ID, _, api, fields, models
import requests


class Lot(models.Model):
    _inherit = 'stock.lot'

    x_SalePrice = fields.Float('X Saleprice',store=True,readonly=False)


class ManufacturingProduction(models.Model):
    _inherit = 'mrp.production'

    x_product_price = fields.Float(compute="set_batch_price")

    @api.depends('product_id')
    def set_batch_price(self):
        for record in self:
            if record._name == 'mrp.production':
                if record.product_id.categ_id.id in [20, 44] and record.state == 'done':
                    record.x_product_price = record.product_id.lst_price
                    if record.lot_producing_id:
                        if record.lot_producing_id.x_SalePrice == 0:
                            record.lot_producing_id.update({'x_SalePrice':record.x_product_price})
                else:
                    record.x_product_price = 0

    def button_plan(self):
        """ Create work orders. And probably do stuff, like things. """
        orders_to_plan = self.filtered(lambda order: not order.is_planned)
        orders_to_confirm = orders_to_plan.filtered(lambda mo: mo.state == 'draft')
        orders_to_confirm.action_confirm()
        for order in orders_to_plan:
            order._plan_workorders()
        self._notify()
        return True

    def _notify(self):
        title = "*Batch Manufacturing Notification*"
        product = self.product_id.name
        batch = str(self.x_prod_batch.x_name)
        msg = "*Company*:" + self.company_id.name+"\n <!subteam^SPM83PL66|@fg> Following Batch has been received in Production for Manufacturing:"+"\n *Batch No. *: " + batch + "\n*Product*: " + product
        URL = "https://portal.hudsonpharma.com/SlackService.svc/PostMessageToSlack?title=" + title + "&message=" + msg + "&channel=CR7QS4VCN"
        response = requests.request("GET", URL)
        print("---------------------------", response)