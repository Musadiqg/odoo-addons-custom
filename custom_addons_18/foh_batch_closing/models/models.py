# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta
import calendar
from calendar import monthrange
from odoo import models, fields, api
from odoo.exceptions import AccessError, UserError, ValidationError


class FohBatchClosingCOA(models.Model):
    _name = 'batch.closing.coa'
    _description = 'Batch Closing Chart of Accounts'

    name = fields.Char('Name', related='coas.name')
    code = fields.Char('Code', related='coas.code')
    coas = fields.Many2one('account.account', "COA")
    company_id = fields.Many2one('res.company', "Company", compute='_compute_company_id', store=True)

    #logic to extract 1st company from company_ids (many2many since odoo 18)
    @api.depends('coas.company_ids')
    def _compute_company_id(self):
        for record in self:
            if record.coas and record.coas.company_ids:
                record.company_id = record.coas.company_ids[0]  # Take first company
            else:
                record.company_id = False

class FohBatchClosing(models.Model):
    _name = 'batch.closing'

    company_id = fields.Many2one('res.company', "Comapny", required=True)
    name = fields.Char()
    date_from = fields.Date('From', required=False)
    date_to = fields.Date('To', required=False)
    description = fields.Char('Description')
    total_credit = fields.Float('Total Credit')
    total_debit = fields.Float('Total Debit')
    total_units = fields.Float('Total Production Units')
    total_balance = fields.Float('Total Balance', compute='get_balance')
    items_count = fields.Char('Batch Closing Lines')
    units_count = fields.Char('Production Units')
    product_count = fields.Char('FOH Product', default='1')
    state = fields.Selection([('draft', 'Draft'),
                              ('todo', 'To Do'),
                              ('close', 'Activate')],
                             default='draft')
    rate = fields.Float("FOH Rate", compute='get_rate')
    current_year = fields.Char('Year', compute='get_year')
    year_from = fields.Selection([('2023', '2023'), ('2024','2024')], required=False, string="Year From")
    year_to = fields.Selection([('2023', '2023'), ('2024','2024')], required=False, string="Year To")
    month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Compute Rate Month',
        default=False,required=True)
    applied_for = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ],
        default=False, required=True)
    active_foh = fields.Boolean("Active FOH Product (AVCO)",required=True)
    @api.depends('month')
    def get_year(self):
        for rec in self:
            rec.current_year = fields.Date.today().year

    @api.depends('total_credit', 'total_debit')
    def get_balance(self):
        for rec in self:
            rec.total_balance = rec.total_debit - rec.total_credit

    @api.depends('total_units', 'total_balance')
    def get_rate(self):
        for rec in self:
            rec.rate = 0
            if rec.total_units != 0:
                rec.rate = rec.total_balance / rec.total_units

    def action_get_foh_product(self):
        if self.company_id.id == 1:
            product = self.env['product.product'].browse(8192)
        else:
            product = self.env['product.product'].browse(8191)
        result = {
            "type": "ir.actions.act_window",
            "res_model": "product.product",
            "domain": [('id', '=', product.id)],
            "context": {"create": False},
            "name": "FOH Product",
            'view_mode': 'tree,form',
        }
        return result

    def get_lines_count(self):
        codes = self.env['batch.closing.coa'].search([]).mapped('code')
        COAs = self.env['account.account'].search([('code', 'in', codes)]).ids
        for rec in self:
            move = self.env['account.move.line'].search(
                [('account_id.id', 'in', COAs), ('parent_state', '=', 'posted')])
            rec.bills_count = len(move)

    def action_get_lines_view(self):
        if self.state != 'draft':
            company_id = self.company_id.id
            codes = self.env['batch.closing.coa'].search([('company_id', '=', company_id), ]).mapped('code')
            COAs = self.env['account.account'].search([('code', 'in', codes)]).ids
            self.ensure_one()
            domain = [('date', '>=', self.date_from), ('date', '<=', self.date_to), ('account_id.id', 'in', COAs),
                      ('parent_state', '=', 'posted')]
            if self.company_id.id == 1:
                domain += [('analytic_account_id', '=', 2)]
            else:
                domain += [('analytic_account_id', '=', 58)]
            lines = self.env['account.move.line'].search(domain)
            result = {
                "type": "ir.actions.act_window",
                "res_model": "account.move.line",
                "domain": [('id', 'in', lines.ids)],
                "context": {"create": False},
                "name": "Batch Closing Lines",
                'view_mode': 'tree,form',
            }
        return result

    def action_get_units(self):
        if self.state != 'draft':
            company_id = self.company_id.id
            if company_id == 1:
                categ_ids = self.env['product.category'].search([('x_studio_applicable_for_foh_rate', '=', True)]).ids
                location_ids = [197]
                location_dest_ids = [26]
            else:
                categ_ids = [50,52]
                location_ids = [198]
                location_dest_ids = [207]
            date_from = self.date_from
            date_to = self.date_to
            time = datetime.min.time()
            xtime = datetime.max.time()
            date_from = datetime.combine(date_from, time)
            date_to = datetime.combine(date_to, xtime)
            domain = [('date', '>=', date_from), ('date', '<=', date_to), ('location_id', '=', location_ids),
                      ('location_dest_id', 'in', location_dest_ids)]
            lines = self.env['stock.move.line'].search(domain)
            lines = lines.filtered(lambda l: l.product_id.categ_id.id in categ_ids)
            result = {
                "type": "ir.actions.act_window",
                "res_model": "stock.move.line",
                "domain": [('id', 'in', lines.ids)],
                "context": {"create": False},
                "name": "Production Lines",
                'view_mode': 'tree,form',
            }
            return result

    def button_post(self):
        self.validate()
        self.compute_dates()
        # Production Lines
        company_id = self.company_id.id
        if company_id == 1:
            categ_ids = self.env['product.category'].search([('x_studio_applicable_for_foh_rate', '=', True)]).ids
            location_ids = [197]
            location_dest_ids = [26]
        else:
            categ_ids = [50,52]
            location_ids = [198]
            location_dest_ids = [207]
        date_from = self.date_from
        date_to = self.date_to
        time = datetime.min.time()
        x_time = datetime.max.time()
        date_from = datetime.combine(date_from, time)
        date_to = datetime.combine(date_to, x_time)

        x_domain = [('date', '>=', date_from), ('date', '<=', date_to), ('location_id', 'in', location_ids),
                    ('location_dest_id', 'in', location_dest_ids)]
        x_lines = self.env['stock.move.line'].search(x_domain)
        x_lines = x_lines.filtered(lambda l: l.product_id.categ_id.id in categ_ids)
        self.units_count = len(x_lines)
        self.total_units = sum(x_lines.mapped('qty_done'))

        # Accounting Lines

        codes = self.env['batch.closing.coa'].search([('company_id', '=', company_id)]).mapped('code')
        COAs = self.env['account.account'].search([('code', 'in', codes)]).ids
        domain = [('date', '>=', self.date_from), ('date', '<=', self.date_to), ('account_id.id', 'in', COAs),
                  ('parent_state', '=', 'posted')]
        if self.company_id.id == 1:
            domain += [('analytic_account_id', '=', 2)]
        else:
            domain += [('analytic_account_id', '=', 58)]
        lines = self.env['account.move.line'].search(domain)
        self.items_count = len(lines)
        self.total_credit = sum(lines.mapped('credit'))
        self.total_debit = sum(lines.mapped('debit'))
        self.state = 'todo'

    def button_validate(self):
        active_batch = self.env['batch.closing'].search([('active_foh','=',True),('company_id','=',self.company_id.id)])
        if active_batch:
            raise UserError("Active Batch already exists")
        if self.company_id.id == 1:
            product = self.env['product.product'].browse(8192)
        else:
            product = self.env['product.product'].browse(8191)
        if product:
            product.update({'standard_price': self.rate})
        self.state = 'close'

    def btn_reset_to_draft(self):
        self.state = 'draft'
        self.items_count = 0
        self.units_count = 0
        self.total_credit = 0
        self.total_debit = 0
        self.total_balance = 0
        self.total_units = 0

    def validate(self):
        if self.month == self.applied_for:
            raise ValidationError("Compute and Applied dates should have difference of a month")
        existing_batch = self.env['batch.closing'].search(
            [('month', '=', self.month), ('applied_for', '=', self.applied_for),
             ('year_from', '=', int(self.year_from)), ('id', '!=', self.id),
             ('company_id', '=', self.company_id.id)])
        if existing_batch:
            raise ValidationError("Record exists for compute/applied month")

    def compute_dates(self):
        month = int(self.month)
        year_from = int(self.year_from)
        year_to = int(self.year_to)
        start_dt = datetime(year_from, month, 1)

        # monthrange() to gets the date range
        res = calendar.monthrange(start_dt.year, start_dt.month)
        last_day = res[1]
        end_dt = datetime(year_to, month, last_day)
        self.date_from = start_dt.date()
        self.date_to = end_dt.date()


class MRPBOM(models.Model):
    _inherit = 'mrp.bom'

    @api.model
    def create(self, vals_list):
        res = super(MRPBOM, self).create(vals_list)
        if res.product_id :
            if res.x_studio_applicable_for_foh:
                if res.company_id.id == 1:
                    foh = res.bom_line_ids.filtered(lambda l:l.product_id.id == 8192 and l.product_id.categ_id.x_studio_applicable_for_foh_rate)
                else:
                    foh = res.bom_line_ids.filtered(lambda l:l.product_id.id == 8191 and l.product_id.categ_id.id in [50,52])
                if not foh:
                    raise ValidationError("FOH Rate product not found in BOM Lines")
        else:
            raise ValidationError("Product Variant is mandatory")
        return res


class MrpProduction(models.Model):
    _inherit = 'mrp.production'


    def button_mark_done(self):
        res = super(MrpProduction, self).button_mark_done()
        if self.move_raw_ids.filtered(lambda l:l.product_id.id == 8192 or l.product_id.id == 8191):
            if self.company_id.id == 1:
                line = self.move_raw_ids.filtered(lambda l:l.product_id.id == 8192)
            else:
                line = self.move_raw_ids.filtered(lambda l:l.product_id.id == 8191)
            if line.quantity_done < line.product_uom_qty:
                raise ValidationError("Consumed quantity is not sufficient for FOH Rate Product")
        return res

  
    # @api.onchange('product_qty')
    # def onchange_move_raw(self):
    #     if self.move_raw_ids.filtered(lambda l: l.product_id.id == 8075):
    #         self.move_raw_ids.filtered(lambda l: l.product_id.id == 8075).update(
    #             {'product_uom_qty': self.product_qty})

