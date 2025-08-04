from odoo import api, models, fields

class TWInheritCRMResPartner(models.Model):
    _inherit = "crm.lead"

    def compute_tw_phone(self):
        for rec in self:
            rec.tw_phone = (str(rec.user_id.id) if rec.user_id else "2") + "||" + rec.name+ "||" +(rec.phone if rec.phone else '')

    def compute_tw_mobile(self):
        for rec in self:

            rec.tw_modile = (str(rec.user_id.id) if rec.user_id else "2") + "||" +rec.name + "||" +(rec.mobile if rec.mobile else '')

    tw_phone = fields.Char("Phone", compute=compute_tw_phone)
    tw_modile = fields.Char("Phone", compute=compute_tw_mobile)