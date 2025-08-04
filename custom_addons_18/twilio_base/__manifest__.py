# © 2018 Danimar Ribeiro <danimaribeiro@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    'name': 'Twilio Base Module',
    'version': '18.0.1.0',
    'category': 'Tools',
    'license': 'AGPL-3',
    'author': 'Hudson Pharma',
    'description': """Base module that holds twilio configuration""",

    'depends': [
        'base',
    ],
    'data': [
        'views/res_company.xml',
        'views/twilio.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
