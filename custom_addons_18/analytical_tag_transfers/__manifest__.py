# -*- coding: utf-8 -*-
{
    'name': "analytical_tag_transfers",

    'summary': """
        For inventory transfers with destination location of
        1) EN/Engineering Items consumed, 
        2) R&D- Research & Development, 
        3) Virtual locations/QC Sampling, 
        4) WH/General items consumed, 
        please add mandatory fields for analytical account and analytical tag""",

    'author': "Hudson Pharma",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'stock',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','stock','account'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
