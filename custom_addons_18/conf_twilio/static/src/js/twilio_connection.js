/** @odoo-module **/
/** @odoo-module **/

import { Composer } from '@mail/components/composer/composer';
import { MessagingMenu } from '@mail/components/messaging_menu/messaging_menu';
import { RtcActivityNotice } from '@mail/components/rtc_activity_notice/rtc_activity_notice';
import { useService } from "@web/core/utils/hooks";
import session from 'web.session';
import { patch } from 'web.utils';
import { getMessagingComponent } from '@mail/utils/messaging_component';
import { registry } from '@web/core/registry';
import AbstractService from 'web.AbstractService';
const systrayRegistry = registry.category('systray');
import { ChatWindowHeader } from '@mail/components/chat_window_header/chat_window_header';
const { Component } = owl;

var to_call_partner;
var tw_session_id;
var tw_calls_logs = [];

patch(ChatWindowHeader.prototype, 'mail/static/src/components/chat_window_header/chat_window_header.js', {
    _onClickClose(ev) {
        ev.stopPropagation();
        if (!this.chatWindow) {
            return;
            }
        this.chatWindow.close();
        if(this.messaging.widget_call_params){
            delete(this.messaging.widget_call_params);
            }
        if(this.messaging.widget_call){
            delete(this.messaging.widget_call);
            }
        if(this.messaging.callConnection){
            this.messaging.callConnection.disconnect();
            }
        if(this.messaging.callConnection){
            delete(this.messaging.callConnection);
            }
        }
    });
//JQNCVT
patch(MessagingMenu.prototype, 'mail/static/src/components/messaging_menu/messaging_menu.js', {
    setup(){
        this._super();
        this.rpc = useService("rpc");
        this.callSID = '';
        this.callConnection = '';
        var self = this;
        //tw_calls_logs[this.composerView.composer.thread.id] = new Object();
        //tw_calls_logs[this.composerView.composer.thread.id].thread_id = this.composerView.composer.thread.id;
        const result = this.rpc({
            route: "/twilio/token",
            params: {user_id: self.env.session.uid}
            }).then(function (result) {
                var parse = JSON.parse(result)
                tw_session_id = parse.token

                Twilio.Device.setup(parse.token);
                //tw_calls_logs[self.composerView.composer.thread.id].access_token = parse.token;
                Twilio.Device.ready(function (device) {
                    //$('.twilio-success-connect-msg').show();
                    //if (typeof self.env.twilio_details != "undefined") {
                    //    self._onClickCallTwilio();
                    //}
                    //setTimeout(function() { $('.twilio-success-connect-msg').hide(); }, 1000);
                    });
                Twilio.Device.error(function (error) {
                    $('.twilio-error-connect-msg').html('<b>Unable to Connect with Twilio. Error Message: </b>'+error.message);
                    $('.twilio-error-connect-msg').show();
                    setTimeout(function() {
                        $('.twilio-error-connect-msg').hide();
                        }, 10000);
                    });
                Twilio.Device.connect(function (conn) {
                    $('.twilio-calling-to').addClass('twilio-call-connected');
                    self.messaging.callConnection = conn;
                    });
                Twilio.Device.incoming(function (conn) {
                    $('.tw-incoming-call-alert').addClass('tw-incoming-call');
                    var callParameters = conn.parameters.Params.split("&");
                    var user_id = callParameters[0].split("=");
                    var caller_name = callParameters[1].split("=");
                    $('.tw-incoming-call-alert .twilio-incoming-caller-name').text(caller_name[1].replace("+", " "));
                    $('.tw-incoming-call-alert .twilio-incoming-caller-number').text(conn.parameters.From);
                    conn.tw_user_id = parseInt(user_id[1]);
                    conn.tw_user_name = caller_name[1].replace("+", " ");
                    self.messaging.callConnection = conn;
                    });
                Twilio.Device.disconnect(function (conn) {
                    setTimeout(function() {
                        $('.twilio-calling').hide();
                        $('.twilio-hangup').show();
                        }, 3000);
                    $('.twilio-calling-to').removeClass('twilio-call-connected');
                    $('.twilio-hangup').hide();
                    });
                });
    }
});
patch(Composer.prototype, 'mail/static/src/components/composer/composer.js', {
    setup(){
        if(this.messaging.callConnection){
            if(this.messaging.callConnection._direction == 'INCOMING'){
                var number = this.messaging.callConnection.tw_user_name + " (" + this.messaging.callConnection.parameters.From + ")";
                setTimeout(function() {
                    $(".twilio-calling-to").html('Connected With: '+number+'.....<span class="twilio-connected">Connected</span>');
                    $(".twilio-calling").show();
                    }, 1500);
                }
            }
        else{
            var self = this;
            if (self.messaging.widget_call){
                self.messaging.toCallPhone = self.messaging.widget_call_params;
                setTimeout(function() {
                    self._onClickCallTwilio();
                    }, 1500);
            } else {
                this.rpc({
                    route: "/twilio/getUserDetails",
                    params: {thread_id: this.composerView.composer.thread.id}
                    }).then(function (result) {
                        self.messaging.toCallPhone = JSON.parse(result).partner_ids[0];
                        //if(self.messaging.widget_call){
                        //    self._onClickCallTwilio();
                        //}
                    });
                }
            }
        },
    async _openChat(params) {
        if (!this.noOpenChat) {
            const messaging = await Component.env.services.messaging.get();
            messaging.env.twilio_details = params
            return messaging.openChat(params);
            }
        return Promise.resolve();
        },
    _disconnectSendCallDetailsToServer(t_id){
        /*
        this.rpc({
            route: "/twilio/savecall",
            params: {callDetails: tw_calls_logs[t_id]}
            }).then(function(result){

            });
        */
        },
    _onClickCallTwilio() {
        var params = {
            phone: this.messaging.toCallPhone['phone'],
            };
        //var callTo = to_call_partner[0].name + " ("+to_call_partner[0].phone+")"
        $(".twilio-calling-to").html('Calling to: '+this.messaging.toCallPhone['phone']+'.....<span class="twilio-connected">Connected</span>');
        $(".twilio-calling").show();
        //tw_calls_logs[this.composerView.composer.thread.id].call_start_time = moment().format("D-MMMM-YYYY h:mma");
        try {
            this.callConnection = Twilio.Device.connect(params);
            }
        catch(err) {
            alert(err.message);
            }
        },
    _onClickDisconnectTwilio(ev) {
        Twilio.Device.disconnectAll();
        setTimeout(function() {
            $('.twilio-calling').hide();
            $('.twilio-hangup').show();
            }, 5000);
        jQuery(ev.target).parents().find(".twilio-open-dialpad").removeClass("twilio-open-dialpad-visible");
        jQuery(ev.target).parents().find(".twilio-send-digit-dialpad").hide();
        $('.twilio-calling-to').removeClass('twilio-call-connected');
        $('.twilio-hangup').hide();
        },
    _onClickToggleDialPad(ev){
        if(jQuery(ev.target).parents().find(".twilio-open-dialpad").hasClass("twilio-open-dialpad-visible")){
            jQuery(ev.target).parents().find(".twilio-open-dialpad").removeClass("twilio-open-dialpad-visible");
            jQuery(ev.target).parents().find(".twilio-send-digit-dialpad").hide();
            }
        else{
            jQuery(ev.target).parents().find(".twilio-open-dialpad").addClass("twilio-open-dialpad-visible");
            jQuery(ev.target).parents().find(".twilio-send-digit-dialpad").show();
            }
        },
    _onCallSendDigit(ev){
        var getNum = jQuery(ev.target).attr('tnumber');
        this.messaging.callConnection.sendDigits(getNum);
        /*
        this.rpc({
            route: "/twilio/sendDigit",
            params: {callSid: tw_calls_logs[this.composerView.composer.thread.id].call_sid,extension: getNum}
            }).then(function(result){

            });
        */
        }
    });