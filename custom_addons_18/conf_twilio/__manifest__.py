# © 2018 Danimar Ribeiro <danimaribeiro@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{   # pylint: disable=C8101,C8103
    'name': 'Twilio Integration',
    'version': '18.0.1.0',
    'category': 'Tools',
    'license': 'AGPL-3',
    'author': 'Hudson Pharma',
    'description': """Add Twilio integration to Odoo""",
    'depends': ['twilio_base','sms','mail','web','crm'],
    'data': ['views/res_partner.xml'],
    'assets': {
        'web.assets_qweb': [
            'conf_twilio/static/src/xml/chatter.xml',
            'conf_twilio/static/src/xml/twilio_call_widget.xml'
        ],
        'web.assets_common': ['conf_twilio/static/src/css/twilio-style.css'],
        'web.assets_backend': [
            'conf_twilio/static/src/js/twilio_connection.js',
            'conf_twilio/static/src/js/twilio.min.js',
            'conf_twilio/static/src/js/twilio_call_widget.js',
            'conf_twilio/static/src/js/tw_componen.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
