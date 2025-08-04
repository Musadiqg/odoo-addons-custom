{
    'name': 'Studio Views',
    'version': '1.0',
    'summary': 'Fix clearing_code on account.payment and add to form view',
    'depends': ['account', 'dev_import_lc_recordings'],
    'data': [
        'views/account_payment_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}