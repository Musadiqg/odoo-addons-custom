# Copyright 2017 Creu Blanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models
from odoo.exceptions import ValidationError

class SVLXlsxInherit(models.AbstractModel):
    _name = "report.report_xlsx.svl_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Stock weighted average cost Report"

    def generate_xlsx_report(self, workbook, data, partners):
        report_name = 'AVG Cost Report Detail Summary'
        x_report_name = 'AVG Cost Report Compiled'

        format1 = workbook.add_format(
            {'font_size': 11, 'align': 'left', 'bold': False, 'text_wrap': True, 'border': 1, 'fg_color': '#C5C5C5'})

        format2 = workbook.add_format({'font_size': 10, 'align': 'right', 'bold': False, 'border': 1})
        format3 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': False, 'border': 1})

        sheet = workbook.add_worksheet(report_name)
        x_sheet = workbook.add_worksheet(x_report_name)

        sheet.write(1, 0, 'Innovita Nutrition (Private) Limited', workbook.add_format({'bold': True, 'size': 12}))
        sheet.write(2, 0,
                    report_name + " Till " + partners.end_date.strftime('%d %b %Y'),
                    workbook.add_format({'bold': False, 'size': 12}))

        x_sheet.write(1, 0, 'Innovita Nutrition (Private) Limited', workbook.add_format({'bold': True, 'size': 12}))
        x_sheet.write(2, 0,
                          x_report_name + " Till " + partners.end_date.strftime('%d %b %Y'),
                      workbook.add_format({'bold': False, 'size': 12}))

        # SHEET ONE
        row = 5
        col = 0
        sheet.write(row, col, 'Accounting Date', format1)
        sheet.write(row, col + 1, 'Product', format1, )
        sheet.write(row, col + 2, 'Vendor', format1)
        sheet.write(row, col + 3, 'In Qty', format1)
        sheet.write(row, col + 4, 'Out Qty', format1)
        sheet.write(row, col + 5, 'On Hand', format1)
        sheet.write(row, col + 6, 'Debit (USD)', format1)
        sheet.write(row, col + 7, 'Credit (USD)', format1)
        sheet.write(row, col + 8, 'Balance (USD)', format1)
        sheet.write(row, col + 9, 'Moving Balance (USD)', format1)
        sheet.write(row, col + 10, 'Debit (PKR)', format1)
        sheet.write(row, col + 11, 'Credit (PKR)', format1)
        sheet.write(row, col + 12, 'Balance (PKR)', format1)
        sheet.write(row, col + 13, 'Moving Balance (PKR)', format1)
        sheet.write(row, col + 14, 'AVG (USD)', format1)
        sheet.write(row, col + 15, 'AVG (PKR)', format1)
        sheet.write(row, col + 16, 'Exchange Rate', format1)
        sheet.write(row, col + 17, 'UOM', format1)
        sheet.set_column(0, 4, 18)
        sheet.set_column(5, 17, 19)
        sheet.set_column(0, 1, 28)

        # SHEET TWO
        x_row = 5
        x_col = 0
        x_sheet.write(x_row, x_col, 'Product', format1)
        x_sheet.write(x_row, x_col + 1, 'UOM', format1)
        x_sheet.write(x_row, x_col + 2, 'On Hand Qty', format1)
        x_sheet.write(x_row, x_col + 3, 'Last Purchase Qty', format1)
        x_sheet.write(x_row, x_col + 4, 'Last Purchase Price', format1)
        x_sheet.write(x_row, x_col + 5, 'AVG (USD)', format1)
        x_sheet.write(x_row, x_col + 6, 'AVG (PKR)', format1)
        x_sheet.write(x_row, x_col + 7, 'Avg. Exchange Rate', format1)
        x_sheet.set_column(0, 4, 18)
        x_sheet.set_column(5, 7, 19)
        x_sheet.set_column(0, 1, 28)

        svl_obj = self.env['stock.valuation.layer']
        domain = [('create_date', '<=', partners.end_date)]
        if partners.product_id and partners.categ_id:
            raise ValidationError("Invalid Filters")
        if partners.product_id:
            domain += [('product_id', 'in', partners.product_id.ids)]
        elif partners.categ_id:
            domain += [('product_id.categ_id', '=', partners.categ_id.id)]

        vals = {}
        group_by = []
        counter = 0
        product_ids = self.env['product.product'].search([('categ_id', '=', partners.categ_id.id)])

        for product in product_ids:
            onhand = 0
            mv_bal = 0
            mv_bal_pkr = 0
            average_pkr = 0
            average_usd = 0
            exchange_rate = 0
            svl_lines = svl_obj.search([('product_id', '=', product.id), ('create_date', '<=', partners.end_date)],
                                       order='create_date ASC')

            for line in svl_lines:
                if line.account_move_id and line.stock_move_id:
                    credit = 0
                    credit_pkr = 0
                    debit = 0
                    debit_pkr = 0
                    line_quantity = line.quantity
                    if line.uom_id.name not in ['kg','Liter']:
                        line_quantity = line.quantity / 1000
                    if line_quantity < 0:
                        credit = - average_usd * line_quantity
                        credit_pkr = - average_pkr * line_quantity
                    elif line_quantity > 0:
                        debit = self.get_purchase_price(line,line_quantity,average_usd)
                        if 'Inventory Adjustment' in line.stock_move_id.reference:
                            debit_pkr = line_quantity * average_pkr
                        else:
                            debit_pkr = sum(
                                line.account_move_id.line_ids.filtered(lambda l: l.account_id.id == 3837).mapped('debit'))

                    onhand += line_quantity
                    balance = debit - credit
                    balance_pkr = debit_pkr - credit_pkr
                    mv_bal_pkr += balance_pkr
                    mv_bal += balance
                    if line_quantity > 0:
                        average_pkr = mv_bal_pkr / onhand if mv_bal_pkr != 0 else 0
                        average_usd = mv_bal / onhand if mv_bal != 0 else 0
                    exchange_rate = self.get_ex_rate(line, average_pkr,
                                                     average_usd) if line_quantity > 0 else exchange_rate
                    if not line.product_id.name in vals:
                        group_by.append(line.product_id.name)
                        vals.update({line.product_id.name: [{
                            'date': str(line.account_move_id.date),
                            'vendor': self.get_vendor(line),
                            'in_qty': line_quantity if line_quantity > 0 else 0.0,
                            'out_qty': line_quantity if line_quantity < 0 else 0.0,
                            'on_hand': onhand,
                            'debit_usd': debit,
                            'credit_usd': credit,
                            'balance_usd': balance,
                            'mv_balance_usd': mv_bal,
                            'debit_pkr': debit_pkr,
                            'credit_pkr': credit_pkr,
                            'balance_pkr': balance_pkr,
                            'mv_balance_pkr': mv_bal_pkr,
                            'avg_usd': average_usd,
                            'avg_pkr': average_pkr,
                            'exchange_rate': exchange_rate,
                            'uom': 'kg' if line.product_id.uom_id.name == 'g' else 'Liter'
                        }]})
                        counter += 1
                    else:
                        new_dict = {
                            'date': str(line.account_move_id.date),
                            'vendor': self.get_vendor(line),
                            'in_qty': line_quantity if line_quantity > 0 else 0.0,
                            'out_qty': line_quantity if line_quantity < 0 else 0.0,
                            'on_hand': onhand,
                            'debit_usd': debit,
                            'credit_usd': credit,
                            'balance_usd': balance,
                            'mv_balance_usd': mv_bal,
                            'debit_pkr': debit_pkr,
                            'credit_pkr': credit_pkr,
                            'balance_pkr': balance_pkr,
                            'mv_balance_pkr': mv_bal_pkr,
                            'avg_usd': average_usd,
                            'avg_pkr': average_pkr,
                            'exchange_rate': exchange_rate,
                            'uom': 'kg' if line.product_id.uom_id.name == 'g' else 'Liter'
                        }
                        row = vals.get(line.product_id.name)
                        row.append(new_dict)

        row = 6
        col = 0
        for product in group_by:
            for svl in vals[product]:
                sheet.write(row, col, svl['date'], format2)
                row += 1

        row = 6
        col = 1
        for product in group_by:
            for svl in vals[product]:
                sheet.write(row, col, product, format3)
                row += 1

        row = 6
        col = 2
        for product in group_by:
            for svl in vals[product]:
                sheet.write(row, col, svl['vendor'], format3)
                row += 1

        row = 6
        col = 3
        for product in group_by:
            for svl in vals[product]:
                sheet.write(row, col, svl['in_qty'], format2)
                row += 1

        row = 6
        col = 4
        for product in group_by:
            for svl in vals[product]:
                sheet.write(row, col, svl['out_qty'], format2)
                row += 1

        row = 6
        col = 5
        for product in group_by:
            for svl in vals[product]:
                sheet.write(row, col, svl['on_hand'], format2)
                row += 1

        row = 6
        col = 6
        for product in group_by:
            for svl in vals[product]:
                sheet.write(row, col, svl['debit_usd'], format2)
                row += 1

        row = 6
        col = 7
        for product in group_by:
            for svl in vals[product]:
                sheet.write(row, col, svl['credit_usd'], format2)
                row += 1

        row = 6
        col = 8
        for product in group_by:
            for svl in vals[product]:
                sheet.write(row, col, svl['balance_usd'], format2)
                row += 1

        row = 6
        col = 9
        for product in group_by:
            for svl in vals[product]:
                sheet.write(row, col, svl['mv_balance_usd'], format2)
                row += 1

        row = 6
        col = 10
        for product in group_by:
            for svl in vals[product]:
                sheet.write(row, col, svl['debit_pkr'], format2)
                row += 1

        row = 6
        col = 11
        for product in group_by:
            for svl in vals[product]:
                sheet.write(row, col, svl['credit_pkr'], format2)
                row += 1

        row = 6
        col = 12
        for product in group_by:
            for svl in vals[product]:
                sheet.write(row, col, svl['balance_pkr'], format2)
                row += 1

        row = 6
        col = 13
        for product in group_by:
            for svl in vals[product]:
                sheet.write(row, col, svl['mv_balance_pkr'], format2)
                row += 1

        row = 6
        col = 14
        for product in group_by:
            for svl in vals[product]:
                sheet.write(row, col, svl['avg_usd'], format2)
                row += 1

        row = 6
        col = 15
        for product in group_by:
            for svl in vals[product]:
                sheet.write(row, col, svl['avg_pkr'], format2)
                row += 1

        row = 6
        col = 16
        for product in group_by:
            for svl in vals[product]:
                sheet.write(row, col, svl['exchange_rate'], format2)
                row += 1

        row = 6
        col = 17
        for product in group_by:
            for svl in vals[product]:
                sheet.write(row, col, svl['uom'], format2)
                row += 1

        x_list = []

        for product in group_by:
            avg_usd = vals[product][-1]['avg_usd']
            avg_pkr = vals[product][-1]['avg_pkr']
            on_hand = vals[product][-1]['on_hand']
            avg_ex_rate = avg_pkr / avg_usd if avg_pkr > 0 and avg_usd > 0 else 0
            uom = vals[product][-1]['uom']
            x_vals = {'product': product, 'uom': uom,
                      'onhand': on_hand, 'lp_qty': self.get_last_qty(vals, product),
                      'lp_price': self.get_last_price(vals, product), 'avg_usd': avg_usd,
                      'avg_pkr': avg_pkr, 'avg_ex_rate': avg_ex_rate}
            x_list.append(x_vals)

        x_row = 6
        x_col = 0
        for product in x_list:
            x_sheet.write(x_row, x_col, product['product'], format2)
            x_row += 1

        x_row = 6
        x_col = 1
        for product in x_list:
            x_sheet.write(x_row, x_col, product['uom'], format2)
            x_row += 1

        x_row = 6
        x_col = 2
        for product in x_list:
            x_sheet.write(x_row, x_col, product['onhand'], format2)
            x_row += 1

        x_row = 6
        x_col = 3
        for product in x_list:
            x_sheet.write(x_row, x_col, product['lp_qty'], format2)
            x_row += 1

        x_row = 6
        x_col = 4
        for product in x_list:
            x_sheet.write(x_row, x_col, product['lp_price'], format2)
            x_row += 1

        x_row = 6
        x_col = 5
        for product in x_list:
            x_sheet.write(x_row, x_col, product['avg_usd'], format2)
            x_row += 1

        x_row = 6
        x_col = 6
        for product in x_list:
            x_sheet.write(x_row, x_col, product['avg_pkr'], format2)
            x_row += 1


        x_row = 6
        x_col = 7
        for product in x_list:
            x_sheet.write(x_row, x_col, product['avg_ex_rate'], format2)
            x_row += 1
    def get_last_qty(self, vals, product):
        last_purchase_qty = 0
        for val in vals[product]:
            if val['in_qty'] > 0:
                last_purchase_qty = val['in_qty']
        return last_purchase_qty

    def get_last_price(self, vals, product):
        last_purchase_price = 0
        for val in vals[product]:
            if val['in_qty'] > 0:
                last_purchase_price = val['debit_usd']
        return last_purchase_price

    def get_purchase_price(self, line,line_quantity, average_usd):
        rate = 0
        if line.stock_move_id.origin:
            po = self.env['purchase.order'].search(
                [('name', '=', line.stock_move_id.origin), ('state', '!=', 'cancel')],
                limit=1)
            if po:
                if po.currency_id.name == "USD":
                    unit_price = po.order_line.filtered(lambda l: l.product_id == line.product_id).price_unit
                    rate = unit_price * line_quantity
                elif po.currency_id.name == "EUR":
                    currency_rate = self.env['res.currency.rate'].search([('currency_id', '=', 3),('name','<=',line.account_move_id.date)], limit=1,  order='id DESC')
                    debit_pkr = sum(
                        line.account_move_id.line_ids.filtered(lambda l: l.account_id.id == 3837).mapped('debit'))
                    rate = debit_pkr / currency_rate.inverse_company_rate
                else:
                    currency_rate = self.env['res.currency.rate'].search([('currency_id', '=', 3),
                    ('name','<=',line.account_move_id.date)], limit=1,order='id DESC')

                    unit_price = po.order_line.filtered(lambda l: l.product_id == line.product_id).price_unit
                    sub_total = unit_price * line_quantity
                    rate = sub_total / currency_rate.inverse_company_rate
        elif 'Inventory Adjustment' in line.stock_move_id.reference:
            rate = line_quantity * average_usd
        return rate

    def get_onhand(self, line, counter, vals, onhand):
        onhand += line.quantity
        return onhand

    def get_vendor(self, line):
        if line.stock_move_id.picking_id:
            vendor = self.env['purchase.order'].search(
                [('name', '=', line.stock_move_id.picking_id.origin)],limit=1).partner_id.name
            return vendor
        else:
            return "-"

    def get_avg(self, line, debit, credit, counter, vals, avg):
        if counter == 0:
            if debit > 0:
                avg = debit
            elif credit > 0:
                avg = credit
            return avg
        else:
            if debit > 0:
                avg += debit
            elif credit > 0:
                avg -= credit
            return avg

    def get_curr_rate(self, line):
        currency_id = self.env['res.currency'].browse(3)
        rate = currency_id.rate_ids[1].inverse_company_rate
        if not currency_id.rate_ids:
            print()
        if line.account_move_id:
            rate = currency_id.rate_ids.filtered(lambda r: r.name == line.account_move_id.date).inverse_company_rate
            if rate != 0.0:
                return rate
        return rate

    def get_ex_rate(self, line, average_pkr, average_usd):
        r = 0
        if line.stock_move_id.origin:
            currency_name = self.env['purchase.order'].search(
                [('name', '=', line.stock_move_id.origin)]).currency_id.name
            if currency_name == "USD":
                r = average_pkr / average_usd if average_usd != 0 else 0
            else:
                currency_rate = self.env['res.currency.rate'].search([('currency_id', '=', 3),('name','<=',line.account_move_id.date)], limit=1,
                                                                     order='id DESC')
                r = currency_rate.inverse_company_rate
        return r


class PartnerXlsxInherit(models.AbstractModel):
    _name = "report.report_xlsx.move_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "SRB JVs XLSX Report"

    def generate_xlsx_report(self, workbook, data, partners):
        moves = partners
        report_name = 'SRB 100 % Sales Tax (Unregistered)'
        format = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': False})
        format1 = workbook.add_format({'font_size': 12, 'align': 'center', 'bold': True})
        format2 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': False})
        sheet = workbook.add_worksheet(report_name)
        width = len("long text hidden test-1")
        sheet.write(0, 0, partners[0].company_id.name, format)
        sheet.write(1, 0, 'D93, North Western Industrial Zone, Port Qasim Authority', format)
        sheet.write(2, 0, 'Karachi 021 75020', format)
        sheet.write(3, 0, 'Pakistan', format)
        sheet.write(4, 0, '')
        row = 5
        col = 0
        sheet.write(row, col, 'Document No', format1)
        sheet.write(row, col + 1, 'Reference', format1)
        sheet.write(row, col + 2, 'Business Name', format1)
        sheet.write(row, col + 3, 'Tax Rate', format1)
        sheet.write(row, col + 4, 'Service/Goods', format1)
        sheet.write(row, col + 5, 'Filer/Non Filer', format1)
        sheet.write(row, col + 6, 'Code', format1)
        sheet.write(row, col + 7, 'Section', format1)
        sheet.write(row, col + 8, 'NTN', format1)
        sheet.write(row, col + 9, 'CNIC', format1)
        sheet.write(row, col + 10, 'Status', format1)
        sheet.write(row, col + 11, 'City', format1)
        sheet.write(row, col + 12, 'Address', format1)
        sheet.write(row, col + 13, 'Certificate / Provision', format1)
        sheet.write(row, col + 14, 'Exemption Date', format1)
        sheet.write(row, col + 15, 'Payment Date', format1)
        sheet.write(row, col + 16, 'Taxable Amount', format1)
        sheet.write(row, col + 17, 'Tax Amount', format1)
        sheet.write(row, col + 18, 'Tax Nature', format1)
        sheet.set_column(0, 0, 30)
        sheet.set_column(0, 1, 70)
        sheet.set_column(0, 2, 10)
        sheet.set_column(0, 3, 15)
        sheet.set_column(0, 4, 15)
        sheet.set_column(0, 5, 15)
        sheet.set_column(0, 6, 20)
        sheet.set_column(0, 7, 20)
        sheet.set_column(0, 8, 30)
        sheet.set_column(0, 9, 25)
        sheet.set_column(0, 10, 40)
        sheet.set_column(0, 11, 90)
        sheet.set_column(0, 12, 35)
        sheet.set_column(0, 13, 30)
        sheet.set_column(0, 14, 30)
        sheet.set_column(0, 15, 30)
        sheet.set_column(0, 16, 30)
        sheet.set_column(0, 17, 30)
        sheet.set_column(0, 17, 30)

        moves = moves.filtered(lambda move: move.bill)

        row = 6
        col = 0
        for move in moves:
            if move.line_ids.filtered(lambda x: x.account_id.is_srb_account):
                sheet.write(row, col, move.name, format2)
                row += 1
            sheet.write(row, col, 'Total', format1)

        row = 6
        col = 1
        for move in moves:
            if move:
                if move.line_ids.filtered(lambda x: x.account_id.is_srb_account):
                    refs = str(move.mapped('name'))
                    sheet.write(row, col, refs, format2)
                    row += 1

        row = 6
        col = 2
        for move in moves:
            if move.line_ids.filtered(lambda x: x.account_id.is_srb_account):
                sheet.write(row, col, move.bill.partner_id.name, format2)
                row += 1

        row = 6
        col = 3
        for move in moves:
            if move.line_ids.filtered(lambda x: x.account_id.is_srb_account):
                rate = move.bill.invoice_line_ids.filtered(lambda line: line.tax_ids).tax_ids.description
                sheet.write(row, col, rate, format2)
                row += 1

        row = 6
        col = 4
        for move in moves:
            goods_service = "-"
            if move.line_ids.filtered(lambda x: x.account_id.is_srb_account):
                if move.bill.invoice_line_ids.filtered(lambda line: line.tax_ids):
                    for tax in move.bill.invoice_line_ids.filtered(lambda line: line.tax_ids).tax_ids:
                        if "SRB" in tax.name:
                            goods_service = tax.x_Goods_Service
            sheet.write(row, col, goods_service, format2)
            row += 1

        row = 6
        col = 5
        for move in moves:
            filer_non_filer = "-"
            if move.line_ids.filtered(lambda x: x.account_id.is_srb_account):
                if move.bill.invoice_line_ids.filtered(lambda line: line.tax_ids):
                    for tax in move.bill.invoice_line_ids.filtered(lambda line: line.tax_ids).tax_ids:
                        if "SRB" in tax.name:
                            filer_non_filer = tax.x_Filer_NonFiler
            sheet.write(row, col, filer_non_filer, format2)
            row += 1

        row = 6
        col = 6
        for move in moves:
            code = "-"
            if move.line_ids.filtered(lambda x: x.account_id.is_srb_account):
                if move.bill.invoice_line_ids.filtered(lambda line: line.tax_ids):
                    for tax in move.bill.invoice_line_ids.filtered(lambda line: line.tax_ids).tax_ids:
                        if "SRB" in tax.name:
                            code = tax.x_SectionCode
            sheet.write(row, col, code, format2)
            row += 1

        row = 6
        col = 7
        for move in moves:
            section = "-"
            if move.line_ids.filtered(lambda x: x.account_id.is_srb_account):
                if move.bill.invoice_line_ids.filtered(lambda line: line.tax_ids):
                    for tax in move.partner_id.x_studio_wht_position.tax_ids:
                        if "SRB" in tax.name:
                            section = tax.x_SectionReference
            sheet.write(row, col, section, format2)
            row += 1

        row = 6
        col = 8
        for move in moves:
            if move.line_ids.filtered(lambda x: x.account_id.is_srb_account):
                if move.bill.partner_id.vat == 0:
                    vat = '-'
                else:
                    vat = move.partner_id.vat
                sheet.write(row, col, vat, format2)
                row += 1

        row = 6
        col = 9
        for move in moves:
            if move.line_ids.filtered(lambda x: x.account_id.is_srb_account):
                if move.bill.partner_id.x_cnic == 0:
                    nic = '-'
                else:
                    nic = move.bill.partner_id.x_cnic
                sheet.write(row, col, nic, format2)
                row += 1

        row = 6
        col = 10
        for move in moves:
            if move.line_ids.filtered(lambda x: x.account_id.is_srb_account):
                sheet.write(row, col,
                            move.bill.partner_id.x_business_status,
                            format2)
                row += 1

        row = 6
        col = 11
        for move in moves:
            if move.line_ids.filtered(lambda x: x.account_id.is_srb_account):
                if move.bill.partner_id.city == 0:
                    city = '-'
                else:
                    city = move.bill.partner_id.city
                sheet.write(row, col, city, format2)
                row += 1

        row = 6
        col = 12
        for move in moves:
            if move.line_ids.filtered(lambda x: x.account_id.is_srb_account):
                if move.bill.partner_id.street == 0:
                    address = '='
                else:
                    address = move.bill.partner_id.street
                sheet.write(row, col, address, format2)
                row += 1

        row = 6
        col = 13
        for move in moves:
            if move.line_ids.filtered(lambda x: x.account_id.is_srb_account):
                if move.bill.partner_id.x_Exemption_Certificate:
                    sheet.write(row, col,
                                move.bill.partner_id.x_Exemption_Certificate,
                                format2)
                    row += 1
                else:
                    sheet.write(row, col, "-", format2)

        row = 6
        col = 14
        for move in moves:
            if move.line_ids.filtered(lambda x: x.account_id.is_srb_account):
                if move.bill.partner_id.x_tax_exemption_date:
                    sheet.write(row, col,
                                str(move.bill.partner_id.x_tax_exemption_date),
                                format2)
                    row += 1
                else:
                    sheet.write(row, col, "-", format2)

        row = 6
        col = 15
        for move in moves:
            if move.line_ids.filtered(lambda x: x.account_id.is_srb_account):
                sheet.write(row, col,
                            str(move.date),
                            format2)
                row += 1

        row = 6
        col = 16
        total_taxable_amount = 0
        for move in moves:
            if move.line_ids.filtered(lambda x: x.account_id.is_srb_account):
                total_taxable = sum(move.bill.mapped('amount_total'))
                total_taxable_amount += total_taxable
                sheet.write(row, col, total_taxable, format2)
                row += 1
            sheet.write(row, col, total_taxable_amount, format1)

        row = 6
        col = 17
        total_tax_amount = 0
        for move in moves:
            if move.line_ids.filtered(lambda x: x.account_id.is_srb_account):
                if move:
                    tax_amount = move.amount_total
                    total_tax_amount += tax_amount
                    sheet.write(row, col, tax_amount, format2)
                    row += 1
                else:
                    sheet.write(row, col, 0, format2)
                    row += 1
            sheet.write(row, col, total_tax_amount, format1)

        row = 6
        col = 18
        for move in moves:
            if move.line_ids.filtered(lambda x: x.account_id.is_srb_account):
                if move.bill.invoice_line_ids.filtered(lambda line: line.tax_ids):
                    for tax in move.bill.invoice_line_ids.filtered(lambda line: line.tax_ids).tax_ids:
                        if "SRB" in tax.name:
                            sheet.write(row, col, tax.x_TaxNature, format2)
                            row += 1
                else:
                    sheet.write(row, col, "-", format2)
                    row += 1


class PartnerXlsx(models.AbstractModel):
    _name = "report.report_xlsx.partner_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "WHT XLSX Report"

    def generate_xlsx_report(self, workbook, data, partners):
        row = 0
        col = 0
        # for i, obj in enumerate(partners):
        #     bold = workbook.add_format({"bold": True})
        #     sheet.write(i, 0, obj.name, bold)
        report_name = 'WHT Report'
        format = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': False})
        format1 = workbook.add_format({'font_size': 12, 'align': 'center', 'bold': True})
        format2 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': False})
        sheet = workbook.add_worksheet(report_name)
        width = len("long text hidden test-1")
        sheet.write(0, 0, partners[0].company_id.name, format)
        sheet.write(1, 0, 'D93, North Western Industrial Zone, Port Qasim Authority', format)
        sheet.write(2, 0, 'Karachi 021 75020', format)
        sheet.write(3, 0, 'Pakistan', format)
        sheet.write(4, 0, '')
        row = 5
        col = 0
        sheet.write(row, col, 'Document No', format1)
        sheet.write(row, col + 1, 'Reference', format1)
        sheet.write(row, col + 2, 'Business Name', format1)
        sheet.write(row, col + 3, 'Tax Rate', format1)
        sheet.write(row, col + 4, 'Service/Goods', format1)
        sheet.write(row, col + 5, 'Filer/Non Filer', format1)
        sheet.write(row, col + 6, 'Code', format1)
        sheet.write(row, col + 7, 'Section', format1)
        sheet.write(row, col + 8, 'NTN', format1)
        sheet.write(row, col + 9, 'CNIC', format1)
        sheet.write(row, col + 10, 'Status', format1)
        sheet.write(row, col + 11, 'City', format1)
        sheet.write(row, col + 12, 'Address', format1)
        sheet.write(row, col + 13, 'Certificate / Provision', format1)
        sheet.write(row, col + 14, 'Exemption Date', format1)
        sheet.write(row, col + 15, 'Payment Date', format1)
        sheet.write(row, col + 16, 'Taxable Amount', format1)
        sheet.write(row, col + 17, 'Tax Amount', format1)
        sheet.write(row, col + 18, 'Tax Nature', format1)
        sheet.set_column(0, 0, 30)
        sheet.set_column(0, 1, 70)
        sheet.set_column(0, 2, 10)
        sheet.set_column(0, 3, 15)
        sheet.set_column(0, 4, 15)
        sheet.set_column(0, 5, 15)
        sheet.set_column(0, 6, 20)
        sheet.set_column(0, 7, 20)
        sheet.set_column(0, 8, 30)
        sheet.set_column(0, 9, 25)
        sheet.set_column(0, 10, 40)
        sheet.set_column(0, 11, 90)
        sheet.set_column(0, 12, 35)
        sheet.set_column(0, 13, 30)
        sheet.set_column(0, 14, 30)
        sheet.set_column(0, 15, 30)
        sheet.set_column(0, 16, 30)
        sheet.set_column(0, 17, 30)
        sheet.set_column(0, 17, 30)

        payments = partners.filtered(lambda x: x.reversal_move_id.id == False and x.state == 'posted')

        row = 6
        col = 0
        for payment in payments:
            if payment.x_studio_with_holding_tax.invoice_line_ids.filtered(lambda x: x.account_id.is_wht_account):
                sheet.write(row, col, payment.name, format2)
                row += 1
            sheet.write(row, col, 'Total', format1)

        row = 6
        col = 1
        for payment in payments:
            if payment.x_studio_with_holding_tax:
                if payment.x_studio_with_holding_tax.invoice_line_ids.filtered(lambda x: x.account_id.is_wht_account):
                    refs = str(payment.x_studio_with_holding_tax.mapped('name'))
                    sheet.write(row, col, refs, format2)
                    row += 1

        row = 6
        col = 2
        for payment in payments:
            if payment.x_studio_with_holding_tax.invoice_line_ids.filtered(lambda x: x.account_id.is_wht_account):
                sheet.write(row, col, payment.partner_id.name, format2)
                row += 1

        row = 6
        col = 3
        for payment in payments:
            if payment.x_studio_with_holding_tax.invoice_line_ids.filtered(lambda x: x.account_id.is_wht_account):
                if payment.partner_id.x_studio_wht_position.tax_ids:
                    for tax in payment.partner_id.x_studio_wht_position.tax_ids:
                        if tax.tax_dest_id:
                            if 'Income' in tax.tax_dest_id.name:
                                if tax.x_studio_field_NJLfU == 0:
                                    x = '-'
                                else:
                                    x = tax.x_studio_field_NJLfU
                                sheet.write(row, col, x, format2)
                                row += 1
                else:
                    sheet.write(row, col, "-", format2)
                    row += 1

        row = 6
        col = 4
        for payment in payments:
            if payment.x_studio_with_holding_tax.invoice_line_ids.filtered(lambda x: x.account_id.is_wht_account):
                if payment.partner_id.x_studio_wht_position.tax_ids.tax_dest_id:
                    for tax in payment.partner_id.x_studio_wht_position.tax_ids:
                        if tax.tax_dest_id:
                            if 'Income' in tax.tax_dest_id.name:
                                if tax.tax_dest_id.x_Goods_Service:
                                    goods_service = tax.tax_dest_id.x_Goods_Service
                                else:
                                    goods_service = "-"
                                sheet.write(row, col, goods_service, format2)
                                row += 1
                else:
                    sheet.write(row, col, "-", format2)
                    row += 1

        row = 6
        col = 5
        for payment in payments:
            if payment.x_studio_with_holding_tax.invoice_line_ids.filtered(lambda x: x.account_id.is_wht_account):
                if payment.partner_id.x_studio_wht_position.tax_ids.tax_dest_id:
                    for tax in payment.partner_id.x_studio_wht_position.tax_ids:
                        if tax.tax_dest_id:
                            if 'Income' in tax.tax_dest_id.name:
                                if tax.tax_dest_id.x_Filer_NonFiler:
                                    filer_non_filer = tax.tax_dest_id.x_Filer_NonFiler
                                else:
                                    filer_non_filer = "-"
                                sheet.write(row, col, filer_non_filer, format2)
                                row += 1
                else:
                    sheet.write(row, col, "-", format2)
                    row += 1

        row = 6
        col = 6
        for payment in payments:
            if payment.x_studio_with_holding_tax.invoice_line_ids.filtered(lambda x: x.account_id.is_wht_account):
                if payment.partner_id.x_studio_wht_position.tax_ids.tax_dest_id:
                    for tax in payment.partner_id.x_studio_wht_position.tax_ids:
                        if tax.tax_dest_id:
                            if 'Income' in tax.tax_dest_id.name:
                                if tax.tax_dest_id.x_SectionCode:
                                    code = tax.tax_dest_id.x_SectionCode.split()[0]
                                else:
                                    code = '-'
                                sheet.write(row, col, code, format2)
                                row += 1
                else:
                    sheet.write(row, col, "-", format2)
                    row += 1

        row = 6
        col = 7
        for payment in payments:
            if payment.x_studio_with_holding_tax.invoice_line_ids.filtered(lambda x: x.account_id.is_wht_account):
                if payment.partner_id.x_studio_wht_position.tax_ids.tax_dest_id:
                    for tax in payment.partner_id.x_studio_wht_position.tax_ids:
                        if tax.tax_dest_id:
                            if 'Income' in tax.tax_dest_id.name:
                                if tax.tax_dest_id.x_SectionReference:
                                    ref = tax.tax_dest_id.x_SectionReference.split()[0]
                                else:
                                    ref = '-'
                                sheet.write(row, col, ref, format2)
                                row += 1
                else:
                    sheet.write(row, col, "-", format2)
                    row += 1

        row = 6
        col = 8
        for payment in payments:
            if payment.x_studio_with_holding_tax.invoice_line_ids.filtered(lambda x: x.account_id.is_wht_account):
                if payment.partner_id.vat == 0:
                    vat = '-'
                else:
                    vat = payment.partner_id.vat
                sheet.write(row, col, vat, format2)
                row += 1

        row = 6
        col = 9
        for payment in payments:
            if payment.x_studio_with_holding_tax.invoice_line_ids.filtered(lambda x: x.account_id.is_wht_account):
                if payment.partner_id.x_cnic == 0:
                    nic = '-'
                else:
                    nic = payment.partner_id.x_cnic
                sheet.write(row, col, nic, format2)
                row += 1

        row = 6
        col = 10
        for payment in payments:
            if payment.x_studio_with_holding_tax.invoice_line_ids.filtered(lambda x: x.account_id.is_wht_account):
                sheet.write(row, col,
                            payment.partner_id.x_business_status,
                            format2)
                row += 1

        row = 6
        col = 11
        for payment in payments:
            if payment.x_studio_with_holding_tax.invoice_line_ids.filtered(lambda x: x.account_id.is_wht_account):
                if payment.partner_id.city == 0:
                    city = '-'
                else:
                    city = payment.partner_id.city
                sheet.write(row, col, city, format2)
                row += 1

        row = 6
        col = 12
        for payment in payments:
            if payment.x_studio_with_holding_tax.invoice_line_ids.filtered(lambda x: x.account_id.is_wht_account):
                if payment.partner_id.street == 0:
                    address = '='
                else:
                    address = payment.partner_id.street
                sheet.write(row, col, address, format2)
                row += 1

        row = 6
        col = 13
        for payment in payments:
            if payment.x_studio_with_holding_tax.invoice_line_ids.filtered(lambda x: x.account_id.is_wht_account):
                if payment.partner_id.x_Exemption_Certificate:
                    sheet.write(row, col,
                                payment.partner_id.x_Exemption_Certificate,
                                format2)
                    row += 1
                else:
                    sheet.write(row, col, "-", format2)

        row = 6
        col = 14
        for payment in payments:
            if payment.x_studio_with_holding_tax.invoice_line_ids.filtered(lambda x: x.account_id.is_wht_account):
                if payment.partner_id.x_tax_exemption_date:
                    sheet.write(row, col,
                                str(payment.partner_id.x_tax_exemption_date),
                                format2)
                    row += 1
                else:
                    sheet.write(row, col, "-", format2)

        row = 6
        col = 15
        for payment in payments:
            if payment.x_studio_with_holding_tax.invoice_line_ids.filtered(lambda x: x.account_id.is_wht_account):
                sheet.write(row, col,
                            str(payment.date),
                            format2)
                row += 1

        row = 6
        col = 16
        total_taxable_amount = 0
        for payment in payments:
            if payment.x_studio_with_holding_tax.invoice_line_ids.filtered(lambda x: x.account_id.is_wht_account):
                total_taxable = sum(payment.x_studio_with_holding_tax.mapped('amount_total_signed'))
                total_taxable_amount += total_taxable
                sheet.write(row, col, total_taxable, format2)
                row += 1
            sheet.write(row, col, total_taxable_amount, format1)

        row = 6
        col = 17
        total_tax_amount = 0
        for payment in payments:
            if payment.x_studio_with_holding_tax.invoice_line_ids.filtered(lambda x: x.account_id.is_wht_account):
                if payment.x_studio_with_holding_tax:
                    tax_amount = abs(sum(payment.x_studio_with_holding_tax.line_ids.filtered(
                        lambda x: x.account_id.is_wht_account).mapped('balance')))
                    total_tax_amount += tax_amount
                    sheet.write(row, col, tax_amount, format2)
                    row += 1
                else:
                    sheet.write(row, col, 0, format2)
                    row += 1
            sheet.write(row, col, total_tax_amount, format1)

        row = 6
        col = 18
        for payment in payments:
            if payment.x_studio_with_holding_tax.invoice_line_ids.filtered(lambda x: x.account_id.is_wht_account):
                if payment.partner_id.x_studio_wht_position.tax_ids.tax_dest_id:
                    for tax in payment.partner_id.x_studio_wht_position.tax_ids:
                        if tax.tax_dest_id:
                            if 'Income' in tax.tax_dest_id.name:
                                sheet.write(row, col, tax.tax_dest_id.x_TaxNature, format2)
                                row += 1
                else:
                    sheet.write(row, col, "-", format2)
                    row += 1
