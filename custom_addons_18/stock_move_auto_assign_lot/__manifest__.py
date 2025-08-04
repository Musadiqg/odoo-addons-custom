{
    'name': 'Stock Move Auto Assign Lot for QC',
    'version': '18.0.1.0',
    'summary': 'Automatically assign unassigned stock to existing lots during QC transfers',
    'description': """
        This module automatically assigns unassigned quantities to existing lots during stock transfers from the WH/Quality Control location.
        It ensures that stock operations proceed without negative stock issues by allocating specified quantities to existing lots assigned by QC.
    """,
    'author': 'Musadiq',
    'category': 'Inventory',
    'depends': ['stock'],
    'data': [
        
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
