import requests
from datetime import date, datetime, time
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)
from odoo.tools.float_utils import float_compare, float_is_zero, float_round

class StockLot(models.Model):
    _inherit = 'stock.lot'     

    def send_expiry_notification(self):
        lots = self.env['stock.lot'].search(['&', ('product_id.categ_id', '=', 3), ('product_qty', '>', 0)])  # Updated model name

        for lot in lots:
            if lot.expiration_date and round(lot.product_qty, 2) > 0:
                lf_dt = str(lot.expiration_date).split(' ')[0].split('-')
                cur_dt = date.today()
                life_dt = date(int(lf_dt[0]), int(lf_dt[1]), int(lf_dt[2]))
                diff = life_dt - cur_dt
                diff_in_day = diff.days
                if diff.days >= 0:
                    if diff.days in (89, 90, 91):
                        dt_lf = str(lot.expiration_date).split(' ')[0]
                        msg = "2nd Reminder \nProduct: " + lot.product_id.name + "\nLot: " + lot.name + "\nQuantity: " + str(
                            lot.product_qty) + " " + lot.product_uom_id.name + "\n Expiry Date: " + dt_lf
                        self.request(msg)

                    if diff.days in (30, 31):
                        dt_lf = str(lot.expiration_date).split(' ')[0]
                        msg = "3rd Reminder \nProduct: " + lot.product_id.name + "\nLot: " + lot.name + "\nQuantity: " + str(
                            lot.product_qty) + " " + lot.product_uom_id.name + "\n Expiry Date: " + dt_lf
                        self.request(msg)

                    if diff.days in (180, 181, 182):
                        dt_lf = str(lot.expiration_date).split(' ')[0]
                        msg = "1st Reminder \nProduct: " + lot.product_id.name + "\nLot: " + lot.name + "\nQuantity: " + str(
                            lot.product_qty) + " " + lot.product_uom_id.name + "\n Expiry Date: " + dt_lf
                        self.request(msg)

    def request(self, msg):
        title = "*Product Expiry Alert*"
        URL = "https://portal.hudsonpharma.com/SlackService.svc/PostMessageToSlack?title=" + title + "&message=" + msg + "&channel=GL05BGZD4"
        response = requests.request("GET", URL)