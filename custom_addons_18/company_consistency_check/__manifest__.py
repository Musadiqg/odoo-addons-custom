{
    'name': 'Company Consistency Check',
    'version': '18.0.1.0',
    'category': 'Purchases',
    'summary': 'Enforce company consistency on Purchase Orders and receipts',
    'description': """
        This module ensures that vendors, products, and taxes in Purchase Orders,
        as well as products in related receipts, belong to the same company as
        the PO or receipt, handling edge cases beyond UI filters.
    """,
    'depends': ['purchase', 'stock'],
    'data': [],
    'installable': True,
    'auto_install': False,
}