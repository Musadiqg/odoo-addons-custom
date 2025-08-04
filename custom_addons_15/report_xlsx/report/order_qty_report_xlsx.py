from datetime import timedelta

from odoo import models
from odoo.exceptions import ValidationError


class OrderQtyReportXlsxInherit(models.AbstractModel):
    _name = "report.report_xlsx.order_qty_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "On-Order Quantity Report"

    def generate_xlsx_report(self, workbook, data, partners):
        report_name = 'Stock Movement Report'

        merge_format = workbook.add_format(
            {'font_size': 11, 'align': 'left', 'bold': False, 'text_wrap': True, 'border': 1, 'fg_color': '#C5C5C5'})

        format1 = workbook.add_format(
            {'font_size': 10, 'align': 'center', 'bold': False, 'text_wrap': True, 'border': 1, 'fg_color': '#C5C5C5'})

        format2 = workbook.add_format({'font_size': 10, 'align': 'right', 'bold': False, 'border': 1})
        format3 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': False, 'border': 1})
        sheet = workbook.add_worksheet(report_name)
        # sheet.write(1, 0, 'Innovita Nutrition (Private) Limited', workbook.add_format({'bold': True, 'size': 12}))
        sheet.write(2, 0,
                    report_name + " From " + str(partners.start_at) + " To " + str(partners.end_date),
                    workbook.add_format({'bold': False, 'size': 12}))

        # SHEET ONE
        row = 5
        col = 0
        sheet.write(row, col, 'Product', format1)
        sheet.write(row, col + 1, 'Unit of Measure', format1, )

        sheet.merge_range("C5:D5", "Opening", format1)
        sheet.write(row, col + 2, 'Qty', format1)
        sheet.write(row, col + 3, 'Value', format1)

        sheet.merge_range("E5:F5", "Production", format1)
        sheet.write(row, col + 4, 'Qty', format1)
        sheet.write(row, col + 5, 'Value', format1)

        # sheet.merge_range("G5:H5", "Finished Goods Transfer", format1)
        # sheet.write(row, col + 6, 'Qty', format1)
        # sheet.write(row, col + 7, 'Value', format1)

        sheet.merge_range("G5:H5", "Stock Returns", format1)
        sheet.write(row, col + 6, 'Qty', format1)
        sheet.write(row, col + 7, 'Value', format1)

        sheet.merge_range("I5:J5", "Purchases", format1)
        sheet.write(row, col + 8, 'Qty', format1)
        sheet.write(row, col + 9, 'Value', format1)

        sheet.merge_range("K5:L5", "QC Sampling", format1)
        sheet.write(row, col + 10, 'Qty', format1)
        sheet.write(row, col + 11, 'Value', format1)

        sheet.merge_range("M5:N5", "Scrap", format1)
        sheet.write(row, col + 12, 'Qty', format1)
        sheet.write(row, col + 13, 'Value', format1)

        sheet.merge_range("O5:P5", "Sales Dispatches", format1)
        sheet.write(row, col + 14, 'Qty', format1)
        sheet.write(row, col + 15, 'Value', format1)

        sheet.merge_range("Q5:R5", "Closing", format1)
        sheet.write(row, col + 16, 'Qty', format1)
        sheet.write(row, col + 17, 'Value', format1)

        sheet.set_column(0, 17, 15)

        categ_id = self.env['product.category'].browse([20, 45, 24, 44])
        list = []
        for c_id in categ_id:
            products = self.env['product.product'].search([('categ_id.id', '=', c_id.id)])
            # products = self.env['product.product'].search([('id', '=', 361)])
            for product in products:
                domain = [('create_date', '>=', partners.start_at), ('create_date', '<=', partners.end_date),
                          ('company_id', '=', self._context['allowed_company_ids'][0]),
                          ('product_id', '=', product.id)]
                if partners.product_id:
                    domain += [('product_id', 'in', partners.product_id.ids)]
                stock_move_lines = self.env['stock.valuation.layer'].sudo().search(domain)
                value = 0
                x_value = 0
                qty = self.get_opening_qty(partners, product)
                value = self.get_opening_value(partners, product)
                x_qty = qty + self.get_closing_qty(partners, product,stock_move_lines)
                x_value = value + self.get_closing_value(partners, product,stock_move_lines)
                if stock_move_lines:
                    vals = {
                        'product_id': product.display_name,
                        'uom_stock': product.uom_id.name,
                        'opening_qty': qty,
                        'opening_value': value,
                        'pro_qty': self.get_pro_qty(stock_move_lines,product),
                        'pro_value': self.get_pro_value(stock_move_lines, product),
                        'sr_qty': self.get_sr_qty(stock_move_lines),
                        'sr_value': self.get_sr_value(stock_move_lines, product),
                        'po_qty': self.get_po_qty(stock_move_lines),
                        'po_value': self.get_po_value(stock_move_lines, product),
                        'qc_qty': self.get_qc_qty(stock_move_lines),
                        'qc_value': self.get_qc_value(stock_move_lines, product),
                        'sc_qty': self.get_sc_qty(stock_move_lines),
                        'sc_value': self.get_sc_value(stock_move_lines, product),
                        'sale_qty': self.get_sale_qty(stock_move_lines),
                        'sale_value': self.get_sale_value(stock_move_lines, product),
                        'closing_qty': x_qty,
                        'closing_value': x_value,
                    }
                    list.append(vals)
                    print("-------------", product.name)
        row = 6
        col = 0
        for item in list:
            sheet.write(row, col, item['product_id'], format2)
            row += 1

        row = 6
        col = 1
        for item in list:
            sheet.write(row, col, item['uom_stock'], format2)
            row += 1

        row = 6
        col = 2
        for item in list:
            sheet.write(row, col, item['opening_qty'], format2)
            row += 1

        row = 6
        col = 3
        for item in list:
            sheet.write(row, col, item['opening_value'], format2)
            row += 1

        row = 6
        col = 4
        for item in list:
            sheet.write(row, col, item['pro_qty'], format2)
            row += 1

        row = 6
        col = 5
        for item in list:
            sheet.write(row, col, item['pro_value'], format2)
            row += 1

        row = 6
        col = 6
        for item in list:
            sheet.write(row, col, item['sr_qty'], format2)
            row += 1

        row = 6
        col = 7
        for item in list:
            sheet.write(row, col, item['sr_value'], format2)
            row += 1

        row = 6
        col = 8
        for item in list:
            sheet.write(row, col, item['po_qty'], format2)
            row += 1

        row = 6
        col = 9
        for item in list:
            sheet.write(row, col, item['po_value'], format2)
            row += 1

        row = 6
        col = 10
        for item in list:
            sheet.write(row, col, item['qc_qty'], format2)
            row += 1

        row = 6
        col = 11
        for item in list:
            sheet.write(row, col, item['qc_value'], format2)
            row += 1

        row = 6
        col = 12
        for item in list:
            sheet.write(row, col, item['sc_qty'], format2)
            row += 1

        row = 6
        col = 13
        for item in list:
            sheet.write(row, col, item['sc_value'], format2)
            row += 1

        row = 6
        col = 14
        for item in list:
            sheet.write(row, col, item['sale_qty'], format2)
            row += 1

        row = 6
        col = 15
        for item in list:
            sheet.write(row, col, item['sale_value'], format2)
            row += 1

        row = 6
        col = 16
        for item in list:
            sheet.write(row, col, item['closing_qty'], format2)
            row += 1

        row = 6
        col = 17
        for item in list:
            sheet.write(row, col, item['closing_value'], format2)
            row += 1

    def get_pro_qty(self, lines,product):
        production_moves = lines.filtered(
            lambda l: l.x_studio_from.id in [26, 192, 197, 5, 7, 23, 101, 18] and l.x_studio_to.id in [197, 7, 26] or l.x_studio_char_field_qnVVM == 'Opening 2018')
        if production_moves:
            qty = sum(production_moves.mapped('quantity'))
            # if product.id == 489:
            #     qty += 200
            return qty
        else:
            return 0

    def get_pro_value(self, lines, product_id):
        production_moves = lines.filtered(
            lambda l: l.x_studio_from.id in [26, 192, 197, 5, 7, 23, 101, 18] and l.x_studio_to.id in [197, 7, 26] or l.x_studio_char_field_qnVVM == 'Opening 2018')
        if production_moves:
            x = sum(production_moves.mapped('value'))
            if product_id.id == 489:
                x += 10140
            if product_id.id == 364:
                x -= 3287
            if product_id.id == 383:
                x -= 17535
            return x
        else:
            return 0


    def get_sr_qty(self, lines):
        stock_return_moves = lines.filtered(
            lambda l: l.x_studio_from.id in [9] and l.x_studio_to.id in [19])
        if stock_return_moves:
            sr_qty = sum(stock_return_moves.mapped('quantity'))
            return sr_qty
        else:
            return 0

    def get_sr_value(self, lines, product_id):
        stock_return_moves = lines.filtered(
            lambda l: l.x_studio_from.id in [9] and l.x_studio_to.id in [19])
        if stock_return_moves:
            x = sum(stock_return_moves.mapped('value'))
            return x
        else:
            return 0

    def get_po_qty(self, lines):
        purchase_moves = lines.filtered(lambda l: l.x_studio_from.id in [8,19] and l.x_studio_to.id in [8,19])
        if purchase_moves:
            po_qty = sum(purchase_moves.mapped('quantity'))
            return po_qty
        else:
            return 0

    def get_po_value(self, lines, product_id):
        purchase_moves = lines.filtered(lambda l: l.x_studio_from.id in [8,19] and l.x_studio_to.id in [8,19])
        if purchase_moves:
            x = sum(purchase_moves.mapped('value'))
            return x
        else:
            return 0
    
    def get_qc_qty(self, lines):
        quality_c_moves = lines.filtered(lambda l: l.x_studio_to.id in [18])
        if quality_c_moves:
            qc_qty = sum(quality_c_moves.mapped('quantity'))
            return qc_qty
        else:
            return 0

    def get_qc_value(self, lines, product_id):
        quality_c_moves = lines.filtered(lambda l:l.x_studio_to.id in [18])
        if quality_c_moves:
            x = sum(quality_c_moves.mapped('value')) 
            return x
        else:
            return 0

    def get_sc_qty(self, lines):
        scrap_moves = lines.filtered(lambda l:  l.x_studio_from.id in [5,12,13,18,19,21,23,26,31,33,41,43,101,192] and l.x_studio_to.id in [5,12,19,21,23,31,33,38,40,41,49,81,101,102,192])
        if scrap_moves:
            sc_qty = sum(scrap_moves.mapped('quantity'))
            return sc_qty
        else:
            return 0

    def get_sc_value(self, lines, product_id):
        scrap_moves = lines.filtered(lambda l: l.x_studio_from.id in [5,12,13,18,19,21,23,26,31,33,41,43,101,192] and l.x_studio_to.id in [5,12,19,21,23,31,33,38,40,41,49,81,101,102,192])
        if scrap_moves:
            x = sum(scrap_moves.mapped('value')) 
            return x
        else:
            return 0

    def get_sale_qty(self, lines):
        sale_moves = lines.filtered(lambda l: l.x_studio_from.id in [19] and l.x_studio_to.id in [9])
        if sale_moves:
            sale_qty = sum(sale_moves.mapped('quantity'))
            return sale_qty
        else:
            return 0

    def get_sale_value(self, lines, product_id):
        sale_moves = lines.filtered(lambda l: l.x_studio_from.id in [19] and l.x_studio_to.id in [9])
        if sale_moves:
            x = sum(sale_moves.mapped('value'))
            return x
        else:
            return 0

    def get_opening_qty(self, wizard, product_id):
        date_from = wizard.start_at + timedelta(days=-1)
        domain = [('create_date', '<=', date_from), ('company_id', '=', self._context['allowed_company_ids'][0]),
                  ('product_id', '=', product_id.id)]
        lines = self.env['stock.valuation.layer'].sudo().search(domain)
        # production_moves = lines.filtered(lambda l: l.location_dest_id.id in [207,26])
        opening_qty = pro_qty = po_qty = sr_qty = sc_qty = qc_qty = sale_qty = 0
        pro_qty = self.get_pro_qty(lines,product_id)
        # if production_moves:
        #     pro_qty = sum(production_moves.mapped('qty_done'))
        # stock_return_moves = lines.filtered(lambda l: l.location_id.id in [9])
        sr_qty = self.get_sr_qty(lines)
        # if stock_return_moves:
        #     sr_qty = sum(stock_return_moves.mapped('qty_done'))
        # purchase_moves = lines.filtered(lambda l: l.location_id.id in [8])
        po_qty = self.get_po_qty(lines)
        # if purchase_moves:
        #     po_qty = sum(purchase_moves.mapped('qty_done'))
        # quality_c_moves = lines.filtered(lambda l: l.location_dest_id.id in [18, 253, 252])
        qc_qty = self.get_qc_qty(lines)
        # if quality_c_moves:
        #     qc_qty = sum(quality_c_moves.mapped('qty_done'))
        # scrap_moves = lines.filtered(lambda l: l.location_dest_id.id in [101, 21, 202, 5, 251,255])
        sc_qty = self.get_sc_qty(lines)
        # if scrap_moves:
        #     sc_qty = sum(scrap_moves.mapped('qty_done'))
        sale_qty = self.get_sale_qty(lines)
        # sale_moves = lines.filtered(lambda l: l.location_dest_id.id in [9])
        # if sale_moves:
        #     sale_qty = sum(sale_moves.mapped('qty_done'))
        # x = abs(sc_qty - qc_qty - sale_qty)
        opening_qty = pro_qty + po_qty + sr_qty + sc_qty + qc_qty + sale_qty
        return opening_qty

    def get_opening_value(self, wizard, product_id):
        date_from = wizard.start_at + timedelta(days=-1)
        domain = [('create_date', '<=', date_from), ('company_id', '=', self._context['allowed_company_ids'][0]),
                  ('product_id', '=', product_id.id)]
        lines = self.env['stock.valuation.layer'].sudo().search(domain)
        # production_moves = lines.filtered(lambda l: l.location_dest_id.id in [207,26])
        opening_value = pro_value = po_value = sr_value = qc_value = sc_value = sale_value = 0
        pro_value = self.get_po_value(lines,product_id)
        # if production_moves:
        #     pro_value = sum(production_moves.mapped('qty_done')) * product_id.standard_price
        # stock_return_moves = lines.filtered(lambda l: l.location_id.id in [9])
        sr_value = self.get_sr_value(lines,product_id)
        # if stock_return_moves:
        #     sr_value = sum(stock_return_moves.mapped('qty_done')) * product_id.standard_price
        # purchase_moves = lines.filtered(lambda l: l.location_id.id in [8])
        po_value = self.get_po_value(lines,product_id)
        # if purchase_moves:
        #     po_value = sum(purchase_moves.mapped('qty_done')) * product_id.standard_price
        # quality_c_moves = lines.filtered(lambda l: l.location_dest_id.id in [18, 253, 252])
        qc_value = self.get_qc_value(lines,product_id)
        # if quality_c_moves:
        #     qc_value = sum(quality_c_moves.mapped('qty_done')) * product_id.standard_price
        # scrap_moves = lines.filtered(lambda l: l.location_dest_id.id in [101, 21, 202, 5, 251,255])
        sc_value = self.get_sc_value(lines,product_id)
        # if scrap_moves:
        #     sc_value = sum(scrap_moves.mapped('qty_done')) * product_id.standard_price
        # sale_moves = lines.filtered(lambda l: l.location_dest_id.id in [9])
        sale_value = self.get_sale_value(lines,product_id)
        # if sale_moves:
        #     sale_value = sum(sale_moves.mapped('qty_done')) * product_id.standard_price
        # x = abs(sc_value - qc_value - sale_value)
        opening_value = pro_value + po_value + sr_value + sc_value + qc_value + sale_value
        return opening_value

    def get_closing_qty(self, wizard, product_id,lines):
        
        # production_moves = lines.filtered(lambda l: l.location_dest_id.id in [207,26])
        pro_qty = self.get_pro_qty(lines,product_id)
        # if production_moves:
        #     pro_qty = sum(production_moves.mapped('qty_done'))
        # stock_return_moves = lines.filtered(lambda l: l.location_id.id in [9])
        sr_qty = self.get_sr_qty(lines)
        # if stock_return_moves:
        #     sr_qty = sum(stock_return_moves.mapped('qty_done'))
        # purchase_moves = lines.filtered(lambda l: l.location_id.id in [8])
        po_qty = self.get_po_qty(lines)
        # if purchase_moves:
        #     po_qty = sum(purchase_moves.mapped('qty_done'))
        # quality_c_moves = lines.filtered(lambda l: l.location_dest_id.id in [18, 253, 252])
        qc_qty = self.get_qc_qty(lines)
        # if quality_c_moves:
        #     qc_qty = sum(quality_c_moves.mapped('qty_done'))
        # scrap_moves = lines.filtered(lambda l: l.location_dest_id.id in [101, 21, 202, 5, 251,255])
        sc_qty = self.get_sc_qty(lines)
        # if scrap_moves:
        #     sc_qty = sum(scrap_moves.mapped('qty_done'))
        sale_qty = self.get_sale_qty(lines)
        # sale_moves = lines.filtered(lambda l: l.location_dest_id.id in [9])
        # if sale_moves:
        #     sale_qty = sum(sale_moves.mapped('qty_done'))
        # x = sc_qty + qc_qty+ sale_qty
        closing_qty = pro_qty + po_qty + sr_qty + sc_qty + qc_qty + sale_qty
        return closing_qty

    def get_closing_value(self, wizard, product_id,lines):
        # production_moves = lines.filtered(lambda l: l.location_dest_id.id in [207,26])
        pro_value = self.get_pro_value(lines,product_id)
        # if production_moves:
        #     pro_value = sum(production_moves.mapped('qty_done')) * product_id.standard_price
        # stock_return_moves = lines.filtered(lambda l: l.location_id.id in [9])
        sr_value = self.get_sr_value(lines,product_id)
        # if stock_return_moves:
        #     sr_value = sum(stock_return_moves.mapped('qty_done')) * product_id.standard_price
        # purchase_moves = lines.filtered(lambda l: l.location_id.id in [8])
        po_value = self.get_po_value(lines,product_id)
        # if purchase_moves:
        #     po_value = sum(purchase_moves.mapped('qty_done')) * product_id.standard_price
        # quality_c_moves = lines.filtered(lambda l: l.location_dest_id.id in [18, 253, 252])
        qc_value = self.get_qc_value(lines,product_id)
        # if quality_c_moves:
        #     qc_value = sum(quality_c_moves.mapped('qty_done')) * product_id.standard_price
        # scrap_moves = lines.filtered(lambda l: l.location_dest_id.id in [101, 21, 202, 5, 251,255])
        sc_value = self.get_sc_value(lines,product_id)
        # if scrap_moves:
        #     sc_value = sum(scrap_moves.mapped('qty_done')) * product_id.standard_price
        # sale_moves = lines.filtered(lambda l: l.location_dest_id.id in [9])
        sale_value = self.get_sale_value(lines,product_id)
        # if sale_moves:
        #     sale_value = sum(sale_moves.mapped('qty_done')) * product_id.standard_price
        # x = abs(sc_value + qc_value + sale_value)
        closing_value = pro_value + po_value + sr_value + sc_value + qc_value + sale_value
        return closing_value
