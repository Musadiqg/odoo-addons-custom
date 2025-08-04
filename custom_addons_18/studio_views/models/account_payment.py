# from odoo import api, fields, models
# import logging

# _logger = logging.getLogger(__name__)

# class AccountPayment(models.Model):
#     _inherit = 'account.payment'

#     clearing_code = fields.Many2one('clearing.code', string='Clearing Code', readonly=True, store=True)

#     @api.model
#     def create(self, vals):
#         payment = super(AccountPayment, self).create(vals)
#         payment._update_clearing_code()
#         return payment

#     def write(self, vals):
#         res = super(AccountPayment, self).write(vals)
#         if 'invoice_ids' in vals:
#             self._update_clearing_code()
#         return res

#     def _update_clearing_code(self):
#         for payment in self:
#             bill = False
#             if payment.invoice_ids:
#                 bill = payment.invoice_ids.filtered(lambda x: x.move_type in ('in_invoice', 'in_refund'))[:1]
#             elif self.env.context.get('active_ids'):
#                 moves = self.env['account.move'].browse(self.env.context.get('active_ids'))
#                 bill = moves.filtered(lambda x: x.move_type in ('in_invoice', 'in_refund'))[:1]
#             if bill and bill.clearing_code:
#                 payment.clearing_code = bill.clearing_code
#                 _logger.debug(f"Set clearing_code {bill.clearing_code.name} for payment {payment.id}")
#             else:
#                 payment.clearing_code = False
#                 _logger.warning(f"No bill or clearing_code found for payment {payment.id}")