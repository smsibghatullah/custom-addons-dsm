# -*- coding: utf-8 -*-

{
    'name': 'Dynamic Sales Report',
    'version': '1.1',
    'summary': 'Comprehensive sales invoice report with detailed payment method breakdown',
    'description': """
Dynamic Sales Report by DSM
===========================

This module provides a detailed and customizable sales report by invoice,
including payment method splits (Cash, Card, Cheque, Bank), due amounts,
and salesperson-wise summaries.

Developed by Dynamic Solution Maker (DSM)
Website: https://dsmpk.com
""",
    'author': 'Dynamic Solution Maker (DSM)',
    'website': 'https://dsmpk.com',
    'license': 'LGPL-3',
    'category': 'Reporting',
    'depends': ['base', 'sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/wiz_sales_view.xml',
        'views/action_report.xml',
        'views/account_sales_data_view.xml',
        'views/account_sales_data_view_03.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
