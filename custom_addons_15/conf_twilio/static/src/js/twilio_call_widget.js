/* Copyright 2019 GRAP - Quentin DUPONT
 * Copyright 2020 Tecnativa - Alexandre Díaz
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html) */


odoo.define("conf_twilio.twilio_phone", function (require) {
    "use strict";

    const field_utils = require("web.field_utils");
    const Registry = require("web.field_registry");
    const FieldFloat = require("web.basic_fields").FieldFloat;
    const session = require("web.session");
    //import core from 'web.core';
    const { Component } = owl;

    const TwilioCall = FieldFloat.extend({
        template: "twilio_call_widget",
        className: "o_field_twilio_call",
        events: _.extend({}, _.omit(FieldFloat.prototype.events, ["click"]), {
            "click .twilio-wrapper-class": "_onClickTwilio",
        }),
        supportedFieldTypes: ["float", "integer"],

        init: function () {
            this._super.apply(this, arguments);

        },

        start: function () {
            return this._super.apply(this, arguments);
        },
        _renderEdit: function () {
            this.$el.addClass("hide-twilio-wrapper-class");
        },

        _renderReadonly: function () {
            var def = this._super.apply(this, arguments);
            var num = this.$el.text();
            var $composerButton = $('<div>', {
                title: 'Call using Twilio',
                class: 'twilio-wrapper-class-img',
                html: '<img src="/conf_twilio/static/src/img/twilio-call.png" />'
                });
            $composerButton.attr('user-num', num);
            $composerButton.on('click', this._onClickTwilio.bind(this));
            this.$el = this.$el.html($composerButton);
            return def;
        },

        _onClickTwilio: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            var get = this.$el.find(".twilio-wrapper-class-img").attr('user-num').split('||');
            this._openChat({ userId: parseInt(get[0]), incoming: false, name: get[1],phone: get[2], model: this.model, res_id: this.res_id });
        },

        async _openChat(params) {
            if (!this.noOpenChat) {
                const messaging = await Component.env.services.messaging.get();
                messaging.widget_call = true;
                messaging.widget_call_params = params;
                return messaging.openChat(params);
            }
            return Promise.resolve();
        },
    });
    Registry.add("twilio_call", TwilioCall);
    return TwilioCall;
});
