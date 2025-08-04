import os
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.twiml.voice_response import VoiceResponse, Play, Dial
from odoo.http import Controller, route, request, Response
import json
from datetime import datetime,date, timedelta
import logging
_logger = logging.getLogger(__name__)

class HandleTwilioConnection(Controller):
    def checkCredentials(self):
        if not request.env.company.twilio_account_sid:
            return 'Please provide Twilio Account SID'
        elif not request.env.company.twilio_auth_token:
            return 'Please provide Twilio Auth Token'
        elif not request.env.company.twilio_api_key:
            return 'Please provide Twilio API Key'
        elif not request.env.company.twilio_api_secret:
            return 'Please provide Twilio API Secret'
        elif not request.env.company.twilio_outgoing_application_sid:
            return 'Please provide Twilio Outgoing Application SID'
        else:
            return 'fine'

    @route('/twilio/getUserDetails', type='json', auth='user')
    def getUserDetails(self):
        if 'thread_id' in request.params:
            channel = request.env['mail.channel'].browse(request.params['thread_id'])
            return_partner_ids = []
            for i in channel.channel_partner_ids:
                if i.id != request.env.user.partner_id.id:
                    return_partner_ids.append({
                        'name': i.name,
                        'phone': i.phone or i.mobile
                    })
            return json.dumps({'partner_ids': return_partner_ids})

    @route('/twilio/token', type='json', auth='user')
    def getToken(self):
        if 'user_id' in request.params:
            user = request.env['res.users'].browse(request.params['user_id'])
            return_partner_ids = []
            check = self.checkCredentials()
            if check == 'fine':
                twilioAccountSid = request.env.company.twilio_account_sid
                twilioApiKey = request.env.company.twilio_api_key
                twilioApiSecret = request.env.company.twilio_api_secret
                outgoingApplicationSid = request.env.company.twilio_outgoing_application_sid
                identity = "MitchellAdmin"
                token = AccessToken(twilioAccountSid,twilioApiKey,twilioApiSecret,identity=identity)
                voiceGrant = VoiceGrant(outgoing_application_sid=outgoingApplicationSid, incoming_allow=True)
                token.add_grant(voiceGrant)
                return json.dumps({ "identity": identity,"token": token.to_jwt() })
            else:
                return check

    @route('/twilio/sendDigit', type='json', auth='user')
    def twSendDigit(self):
        data = request.params
        response = VoiceResponse()
        response.play('', digits=data['extension'])
        print(response)

    @route('/twilio/voice', type='http', auth='public', csrf=False)
    def twVoicecall(self):
        data = request.params
        response = VoiceResponse()
        dial = Dial(caller_id=request.env.company.sudo().twilio_number_id.phone_number)
        dial.number(data['phone'])
        response.append(dial)
        return str(response)

    @route('/twilio/answercall', type='http', auth='public', methods=['GET'], csrf=False)
    def answer_call(self):
        check = self.checkCredentials()
        if check == 'fine':
            user_id = 2
            caller_name = "Unknown"
            if 'From' in request.params:
                caller = request.params['From']
                request.cr.execute("select name, user_id from res_partner where replace(replace(replace(replace(phone,'-', ''), ')', ''), '(', ''),' ','')='"+caller+"' or replace(replace(replace(replace(mobile,'-', ''), ')', ''), '(', ''),' ','')='"+caller+"'")
                for res in request._cr.dictfetchall():
                    if 'user_id' in res:
                        user_id = res['user_id']
                    caller_name = res['name']

            response = VoiceResponse()
            dial = Dial()
            client = dial.client('Admin')
            client.parameter(name='UserId', value=user_id)
            client.parameter(name='Caller_name', value=caller_name)
            dial.append(client)
            response.append(dial)
            return str(response)

    @route('/twilio/savecall', type='json', auth='user')
    def twSavecall(self):
        if 'model' in request.params['callDetails']['call_details'] and 'res_id' in request.params['callDetails']['call_details']:
            chatter_model = request.params['callDetails']['call_details']['model']
            r_id = int(request.params['callDetails']['call_details']['res_id'])
            channel = request.env[chatter_model].browse(r_id)
            if channel:
                caller_details = request.params['callDetails']['call_details']
                call_start_time = datetime.strptime(request.params['callDetails']['call_start_time'], '%d-%B-%Y %H:%M%p')
                call_end_time = datetime.strptime(request.params['callDetails']['call_disconnect_time'], '%d-%B-%Y %H:%M%p')

                call_diff = call_end_time - call_start_time
                call_string = ''
                if hasattr(call_diff, 'hour'):
                    call_string = str(call_diff.hours) + ' hour, '
                if hasattr(call_diff, 'minute'):
                    call_string = str(call_diff.minute) + ' min, '
                if hasattr(call_diff, 'seconds'):
                    call_string += str(call_diff.seconds) + ' sec'

                channel.message_post(body = ("<span class='message-twilio-call-information'>Twilio Call made to %s (%s) <br /><span class='twilio-call-duration'>%s</span></span>" %
                                             (caller_details['name'],caller_details['phone'],call_string)),
                                     message_type='notification')