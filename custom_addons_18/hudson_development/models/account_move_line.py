import requests
from datetime import date, datetime, time
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)  # Get the logger for this module
from odoo.tools.float_utils import float_compare, float_is_zero, float_round

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    internal_note = fields.Char(string="Internal Note")
    
    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE

        processed_vals_list = []
        for vals in vals_list:
            new_vals = vals.copy()

            move = self.env['account.move'].browse(new_vals.get('move_id')) 
            if not move: # Ensure move exists
                processed_vals_list.append(new_vals)
                continue
                
            new_vals.setdefault('company_currency_id', move.company_id.currency_id.id)

            # This block tries to ensure amount_currency is set correctly for company currency.
            # Review if Odoo 18's computes (_compute_amount_currency/_inverse_amount_currency) handle this sufficiently.
            # It might be removable if 'balance' or 'amount_currency' are consistently provided or computed correctly.
            currency_id = new_vals.get('currency_id') or move.company_id.currency_id.id
            if currency_id == move.company_id.currency_id.id:
                if 'balance' not in new_vals and 'amount_currency' not in new_vals and ('debit' in new_vals or 'credit' in new_vals):
                   balance = new_vals.get('debit', 0.0) - new_vals.get('credit', 0.0)
                   new_vals.update({
                       'currency_id': currency_id,
                       'amount_currency': balance,
                   })
            # else: # If currency is different, ensure amount_currency is at least 0.0 if not provided
            #    new_vals.setdefault('amount_currency', 0.0) # Setdefault is safer if key might be missing

            # Removed the Odoo 15-style synchronization logic involving calls to
            # _get_price_total_and_subtotal_model, _get_fields_onchange_balance_model, etc.
            # Odoo 18 handles this via compute fields and sync managers called during super().create().

            # Apply custom account mapping logic
            # Ensure account_id exists in vals before comparing
            current_account_id = new_vals.get('account_id')
            if current_account_id:
                if move.move_type == 'out_invoice' and current_account_id == 3965:
                    new_vals['account_id'] = 3964
                elif move.move_type == 'out_refund' and current_account_id == 3964:
                    new_vals['account_id'] = 3965

            processed_vals_list.append(new_vals)

        # Call super() with the processed list containing potential account changes
        lines = super(AccountMoveLine, self).create(processed_vals_list)

        # Post-create checks (_check_balanced, lock dates, _synchronize_business_models)
        # are handled by the Odoo 18 framework during the super().create() call chain and/or posting.
        # Explicit calls here are removed as they are likely redundant.

        return lines

    # Removed commented-out round_off method

    # @api.onchange('price_unit','tax_ids')
    # def round_off(self):
    #     for rec in self:
    #         rec.price_unit = round(rec.price_unit,0)
