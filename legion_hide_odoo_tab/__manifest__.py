# -*- coding: utf-8 -*-
{
    "name": "Hide Odoo from Browser Tab",
    "category": "Tools",
    "version": "16.0.1.1",
    'license': 'LGPL-3',

    "author": "ByteLegion",
    "website": "http://www.bytelegions.com",
    'company': 'ByteLegion',
    'maintainer': 'Waqar Ahmad',

    "depends": ['base', 'web'],
    "data": [
        'views/template.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'legion_hide_odoo_tab/static/src/js/chrome.js',
        ],
    },

    "application": True,
    "installable": True,
    "auto_install": False,
}
