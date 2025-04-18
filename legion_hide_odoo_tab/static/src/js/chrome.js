
/** @odoo-module **/

import { WebClient } from "@web/webclient/webclient";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import rpc from 'web.rpc';


patch(WebClient.prototype, "legion_hide_odoo_tab.WebClient", {
    setup() {
            this._super.apply(this, arguments);
            var domain = session.user_companies.allowed_companies;
            this.title.setParts({ zopenerp: "" });
            var obj = this;
            var def = rpc.query({
                fields: ['name','id',],
                model: 'res.config.settings',
                method: 'current_company_id',
                args: [domain, domain],
            })
                .then(function (result) {
//                const app_system_name = session.app_system_name || 'New title';
                const app_system_name = session.app_system_name || '';
                obj.title.setParts({ zopenerp: result });
            });
    }
});



//// my_module/static/js/custom_title.js
//
//odoo.define('legion_hide_odoo_tab.custom_title', function (require) {
//    "use strict";
//
//    var WebClient = require('web.WebClient');
//    var session = require('web.session');
//
//    WebClient.include({
//        start: function () {
//            var self = this;
//            return this._super.apply(this, arguments).then(function () {
//                // Set a custom title here
//                var customTitle = session.app_system_name || 'Custom Title';
//                self.set_title(customTitle);
//            });
//        },
//    });
//});
//
//
