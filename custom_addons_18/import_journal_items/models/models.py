# -*- coding: utf-8 -*-
import urllib
import odoorpc
from odoo import models, fields, api

import tempfile
import binascii
from odoo import models, fields, api, _
import xlrd


class SurveyImportWizard(models.TransientModel):
    _name = 'so.import.wizard'

    data = fields.Binary('Upload File')

    def load_data(self):
        if not self.data:
            return {'type': 'ir.actions.act_window_close'}
        fp = tempfile.NamedTemporaryFile(suffix=".xlsx")
        fp.write(binascii.a2b_base64(self.data))
        fp.seek(0)
        workbook = xlrd.open_workbook(fp.name)
        sheet = workbook.sheet_by_index(0)
        count = 0
        reciept_no = ""
        sale_order = False
        counter = 0
        pwd_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        # pwd_mgr.add_password(None, "https://odoo.hudsonpharma.com", "admin", "SilentNightOdoo")
        auth_handler = urllib.request.HTTPBasicAuthHandler(pwd_mgr)
        opener = urllib.request.build_opener(auth_handler)
        odoo = odoorpc.ODOO('odoo.hudsonpharma.com', protocol='jsonrpc', opener=opener, port=443)
        print(odoo.db.list())
        odoo.login(odoo.db.list()[0], 'saad.mahmood@hudsonpharam.com', 'Sybr1d1234')

        for row_no in range(sheet.nrows):
            if row_no <= 0:
                fields = map(lambda row: row.value.encode('utf-8'), sheet.row(row_no))
            else:
                count += 1
                line = list(map(lambda row: isinstance(row.value, str) and row.value.encode('utf-8') or str(row.value),
                                sheet.row(row_no)))
                if line[0]:
                    ID = int(float(line[0]))
                    product = odoo.execute('product.product', 'read', ID,['standard_price'])
                    # product = self.env['product.product'].browse(ID)
                    product.x_studio_old_cost = product.standard_price
                    product.standard_price = int(float(line[1]))
                    product.x_studio_cost_updated = True

                    move_line = self.env['account.move.line'].browse(ID)
                    if move_line.exists():
                        if line[5] != "":
                            account_id = int(float(line[5]))
                            # acc = self.env['account.analytic.account'].browse(account_id)
                            # if acc.exists():
                            move_line.update({'analytic_account_id': account_id})
                            # print("=======",move_line.analytic_account_id.name)
                        if line[6] != "":
                            tag_id = int(float(line[6]))
                            # tag = self.env['account.analytic.tag'].browse(tag_id)
                            # if tag.exists():
                            move_line.update({'analytic_tag_ids': [(4, tag_id)]})
                            # print("=======",move_line.analytic_tag_ids.name)
                        counter += 1
