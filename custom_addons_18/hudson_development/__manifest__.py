# -*- coding: utf-8 -*-
{
    'name': "hudson_development",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account','report_xlsx','sale','stock','mrp','analytic','l10n_us_check_printing'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/inherit_views.xml',
        'views/report_inv_document.xml',
        'views/report_invoice.xml', 
        'views/invoice_with_decimal.xml',
        #'views/account_payment_views.xml',
        # 'views/party_cheque.xml',
        # 'views/wizard_report_weighted_cost.xml'
    ],
    'test': [
        'tests/test_account_payment.py',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
