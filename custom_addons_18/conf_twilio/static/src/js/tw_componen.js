/** @odoo-module **/
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { getMessagingComponent } from '@mail/utils/messaging_component';
import AbstractService from 'web.AbstractService';
import { registry } from '@web/core/registry';
const systrayRegistry = registry.category('systray');
import { serviceRegistry } from 'web.core';
const { Component } = owl;

export class TWIncomingCall extends Component {
    setup() {
        this.env = owl.Component.env;
        super.setup();
    }
    _onClickTwIncomingAnswer(ev) {
        $('.tw-incoming-call-alert').removeClass('tw-incoming-call');
        this.messaging.callConnection.accept();
        var returned = this._openChat({ userId: this.messaging.callConnection.tw_user_id, incoming: true, name: this.env.session.name,phone: this.messaging.callConnection, model: false, res_id: false });
        console.log(returned);
    }
    _onClickTwIncomingReject(ev) {
        $('.tw-incoming-call-alert').removeClass('tw-incoming-call');
        this.messaging.callConnection.reject();
    }
    async _openChat(params) {
        if (!this.noOpenChat) {
            const messaging = await Component.env.services.messaging.get();
            messaging.env.widget_call = true;
            return messaging.openChat(params);
        }
        return Promise.resolve();
    }
}
Object.assign(TWIncomingCall, {
    props: {},
    template: 'conf_twilio.tw_call_alert',
});
registerMessagingComponent(TWIncomingCall);

export const SystrayService = AbstractService.extend({
    dependencies: ['messaging'],
    /**
     * @override {web.AbstractService}
     */
    async start() {
        await owl.Component.env.services.messaging.modelManager.messagingCreatedPromise;
        systrayRegistry.add('conf_twilio.tw_call_alert', {
            Component: getMessagingComponent('TWIncomingCall'),
        });
    },
});
serviceRegistry.add('TWIncomingCall', SystrayService);