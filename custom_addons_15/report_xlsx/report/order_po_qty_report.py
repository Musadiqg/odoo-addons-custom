from datetime import timedelta

from odoo import models
from odoo.exceptions import ValidationError


class OrderQtyReportXlsxInherit(models.AbstractModel):
    _name = "report.report_xlsx.order_po_qty_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Last Purchasing Report"

    def generate_xlsx_report(self, workbook, data, partners):
        report_name = 'Last Purchasing Report'

        merge_format = workbook.add_format(
            {'font_size': 11, 'align': 'left', 'bold': False, 'text_wrap': True, 'border': 1, 'fg_color': '#C5C5C5'})

        format1 = workbook.add_format(
            {'font_size': 10, 'align': 'center', 'bold': False, 'text_wrap': True, 'border': 1, 'fg_color': '#C5C5C5'})

        format2 = workbook.add_format({'font_size': 10, 'align': 'right', 'bold': False, 'border': 1})
        format3 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': False, 'border': 1})
        sheet = workbook.add_worksheet(report_name)
        # sheet.write(1, 0, 'Innovita Nutrition (Private) Limited', workbook.add_format({'bold': True, 'size': 12}))
        sheet.write(2, 0,
                    report_name, workbook.add_format({'bold': False, 'size': 12}))

        row = 5
        col = 0
        sheet.write(row, col, 'Date', format1)
        sheet.write(row, col + 1, 'Product', format1, )
        sheet.write(row, col + 2, 'Vendor', format1)
        sheet.write(row, col + 3, 'Qty', format1)
        sheet.write(row, col + 4, 'Unit Price', format1)
        sheet.write(row, col + 5, 'UOM', format1)
        sheet.write(row, col + 6, 'Currency', format1)
        sheet.set_column(0, 4, 18)

        products = self.env['product.product'].search([('categ_id', 'in', [4, 3])])
        list = []
        for p in products:
            domain = [('product_id', '=', p.id), ('company_id', '=', self.env.context.get('allowed_company_ids')[0])]
            po_line = self.env['purchase.order.line'].search(domain, order='id desc', limit=1)
            if po_line:
                vals = {
                    'date': str(po_line.date_order),
                    'product': po_line.product_id.display_name,
                    'vendor': po_line.order_id.partner_id.display_name,
                    'qty': po_line.product_qty,
                    'price': po_line.price_unit,
                    'uom': po_line.product_uom.name,
                    'currency': po_line.currency_id.name
                }
                list.append(vals)

        row = 6
        col = 0
        for item in list:
            sheet.write(row, col, item['date'], format2)
            row += 1

        row = 6
        col = 1
        for item in list:
            sheet.write(row, col, item['product'], format2)
            row += 1

        row = 6
        col = 2
        for item in list:
            sheet.write(row, col, item['vendor'], format2)
            row += 1

        row = 6
        col = 3
        for item in list:
            sheet.write(row, col, item['qty'], format2)
            row += 1

        row = 6
        col = 4
        for item in list:
            sheet.write(row, col, item['price'], format2)
            row += 1

        row = 6
        col = 5
        for item in list:
            sheet.write(row, col, item['uom'], format2)
            row += 1

        row = 6
        col = 6
        for item in list:
            sheet.write(row, col, item['currency'], format2)
            row += 1
