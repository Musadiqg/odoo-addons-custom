from odoo import api, models, fields
from datetime import datetime
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

class TwilioCallsLog(models.Model):
    _name = 'tw.call.logs'

    name = fields.Char("name")
    call_start_time = fields.Datetime("Call Start DateTime")
    call_end_time = fields.Datetime("Call End DateTime")
    call_duraation = fields.Float("Call Duration")
    call_price = fields.Float("Call Price")
    call_direction = fields.Selection([('outbound-dial','Outbound'),('inbound','Incoming')], string="Call Direction")
    recording_url = fields.Text("Call Recording")
    call_from = fields.Char("Call From")
    call_to = fields.Char("Call To")
    call_details_json = fields.Text("Twilio Details Json")
    recording_json = fields.Text("Recording Details Json")
    caller_from_name = fields.Many2one("res.partner", string="Call From")
    caller_to_name = fields.Many2one("res.partner", string="Call To")