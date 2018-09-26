#!/usr/bin/python2.7
'''
Freeswitch Mattermost notifications

Notify a Mattermost channel or user about new, answered, missed 
and finished calls and new voicemails
'''
import ESL
import requests
import json
from ConfigParser import ConfigParser, NoOptionError

INCOMING = 'incoming'
OUTGOING = 'outgoing'
PANEL = 'panel'

def post_message(message, webhook, user=None, icon=None, username=None):
    '''
    Post a message to Mattermost 
    :param message: text to be posted
    :param webhook: URL of the webhook to send message to
    :param user: mattermost username that will receive the message 
    :param icon: URL of the image to overwrite icon for post 
    :param username: Name to overwrite username on post
    :return: True if post was succesful
    '''

    payload = {
        "text": message
    }
    if user:
        payload['channel'] = '@' + user
    if icon:
        payload['icon'] = icon
    if username:
        payload['username'] = username
    r = requests.post(webhook, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
    if r.status_code != requests.codes.ok:
        print ('Unable to post message. Received {} code as response'.format(r.status_code))
        return False
    return True


def read_channel_create(event, message_type=INCOMING):

    if message_type == INCOMING:
        message = ':arrow_left: ***Incoming Call***\n\t\t*From:*  {}\n\t\t*CallerID:* {}'.format(
            event.get('Caller-Username'),
            event.get('Caller-Caller-ID-Number'))
    elif message_type == PANEL:
        message = ':telephone_receiver: ***New Call***\n\t\t{} is calling {}'.format(
            event.get('Caller-Username'),
            event.get('Caller-Destination-Number'))
    elif message_type == OUTGOING:
        if event.get('Caller-Destination-Number') == 'voicemail':
            message = ':arrow_right_hook: ***Redirected Call***\n\t\tCalling to {}'.format(
                event.get('Caller-Destination-Number'))
        else:
            message = ':arrow_right: ***New Call***\n\t\tCalling to {}'.format(
                event.get('Caller-Destination-Number'))
    return message


def read_channel_answer(event, message_type=OUTGOING):
    if message_type == OUTGOING:
        message = ':white_check_mark: ***Call Answered***\n\t\t{} answered'.format(
            event.get('Caller-Destination-Number'))
    if message_type == INCOMING:
        message = ':white_check_mark: ***Call Answered***\n\t\tCall from {} answered'.format(
            event.get('Caller-Caller-ID-Number'))
    elif message_type == PANEL:
        message = ':white_check_mark: ***Call Answered***\n\t\t{} answered {}'.format(
            event.get('Caller-Destination-Number'),
            event.get('Caller-Username'))
    return message


def read_channel_answer_rejected(event, message_type=OUTGOING):
    if message_type == OUTGOING:
        message = ':x: ***Call Rejected***\n\t\t{} rejected the call'.format(
            event.get('Caller-Destination-Number'))
    elif message_type == INCOMING:
        message = ':x: ***Call Rejected***\n\t\tCall from {} rejected'.format(
            event.get('Caller-Caller-ID-Number'))
    return message


def read_channel_hangup_complete(event, message_type=OUTGOING):
    if message_type == OUTGOING:
        message = ':telephone: ***Call Hang Up***\n\t\tFinished call with: {}\n\t\t*Cause:* {}\n\t\t*Duration:* {} seconds'.format(
            event.get('Caller-Destination-Number'),
            event.get('Hangup-Cause'),
            event.get('variable_duration'))
    elif message_type == INCOMING:
        message = ':telephone: ***Call Hang Up***\n\t\tFinished call with: {}\n\t\t*Cause:* {}\n\t\t*Duration:* {} seconds'.format(
            event.get('Caller-Caller-ID-Number'),
            event.get('Hangup-Cause'),
            event.get('variable_duration'))
    elif message_type == PANEL:
        message = ':telephone: ***Call Hang Up***\n\t\t{} and {} finished their call\n\t\t*Cause:* {}\n\t\t*Duration:* {} seconds'.format(
            event.get('Caller-Destination-Number'),
            event.get('Caller-Username'),
            event.get('Hangup-Cause'),
            event.get('variable_duration'))
    return message


def read_no_pickup(event):
    message = ':exclamation:  ***Missed Call*** \n\t\t{} called you on {} \n'.format(
        event.get('Caller-Username'),
        event.get('Event-Date-Local'))
    return message


def read_leave_message(event):
    message = ':mailbox_with_mail:   ***New Voicemail***\n\t\t*From:* {}\n\t\t*CallerID:* {}\n\t\t*On:* {}\n\t\t*Duration:* {} seconds\n'.format(
        event.get("VM-Caller-ID-Name"),
        event.get("VM-Caller-ID-Number"),
        event.get("Event-Date-Local"),
        event.get("VM-Message-Len")
    )
    return message


def main():

    config = ConfigParser()
    config.read('freemat.ini')

    esl_server = config.get('freeswitch', 'esl_server')
    esl_port = config.get('freeswitch', 'esl_port')
    esl_secret = config.get('freeswitch', 'esl_secret')

    mm_webhook = config.get('mattermost', 'webhook_url')
    notify_caller = False

    try:
        notify_caller = config.get('freemat', 'notify_caller')
        if notify_caller.lower() == 'false':
            notify_caller = False
    except NoOptionError:
        print ('No notify_caller option set. Using default')

    if not notify_caller:
        print ('We are not notifying events to caller')

    con = ESL.ESLconnection(esl_server, esl_port, esl_secret)

    if con.connected():
        subscribed_events = ['CHANNEL_CREATE', 'CHANNEL_ANSWER', 'CHANNEL_HANGUP_COMPLETE', 'CUSTOM', 'vm::maintenance']

        con.events('plain', ' '.join(subscribed_events))
        while 1:
            e = con.recvEvent()
            if e:
                event = json.loads(e.serialize('json'))
                caller = None
                callee = None
                if notify_caller:
                    try:
                        orig = event.get('Caller-Caller-ID-Number')
                        caller = config.get('extensions', orig)
                    except NoOptionError:
                        print 'No Mattermost user for extension {}'.format(orig)

                try:
                    dest = event.get('Caller-Destination-Number')
                    callee = config.get('extensions', dest)
                except NoOptionError:
                    try:
                        dest = event.get('variable_dialed_user')
                        if dest:
                            callee = config.get('extensions', dest)
                    except NoOptionError:
                        print 'No Mattermost user for extension {}'.format(dest)

                if event.get('Event-Name') == 'CHANNEL_CREATE' and event.get('Call-Direction') == 'inbound':
                    if caller:
                        post_message(read_channel_create(event, message_type=OUTGOING), mm_webhook, user=caller)
                    if callee:
                        post_message(read_channel_create(event, message_type=INCOMING), mm_webhook, user=callee)
                elif event.get('Event-Name') == 'CHANNEL_ANSWER' and event.get(
                    'Call-Direction') == 'inbound' and event.get(
                    'variable_last_bridge_hangup_cause') != 'NO_ANSWER' and event.get(
                    'variable_originate_disposition') != 'NO_PICKUP':
                    if event.get('variable_originate_disposition') == 'CALL_REJECTED':
                        if caller:
                            post_message(read_channel_answer_rejected(event), mm_webhook, user=caller)
                        if callee:
                            post_message(read_channel_answer_rejected(event, message_type=INCOMING), mm_webhook,
                                         user=callee)
                    else:
                        if caller:
                            post_message(read_channel_answer(event), mm_webhook, user=caller)
                        if callee:
                            post_message(read_channel_answer(event, message_type=INCOMING), mm_webhook, user=callee)
                elif event.get('Event-Name') == 'CHANNEL_HANGUP_COMPLETE':
                    if event.get('Call-Direction') == 'inbound' and 'voicemail' not in event.get(
                            'Other-Leg-Channel-Name', ''):
                        if caller:
                            post_message(read_channel_hangup_complete(event), mm_webhook, user=caller)
                        if callee and event.get('Other-Leg-Destination-Number') != 'voicemail':
                           post_message(read_channel_hangup_complete(event, message_type=INCOMING), mm_webhook,
                                        user=callee)
                        if event.get('Hangup-Cause') in ['NO_PICKUP', 'ORIGINATOR_CANCEL', 'NO_ANSWER'] and event.get(
                                'variable_last_app') != 'voicemail':
                            if callee:
                                post_message(read_no_pickup(event), mm_webhook, user=callee)
                    elif event.get('Call-Direction') == 'outbound' and event.get('Hangup-Cause') in ['NO_PICKUP', 'ORIGINATOR_CANCEL', 'NO_ANSWER']:
                        if callee:
                            post_message(read_no_pickup(event), mm_webhook, user=callee)
                elif event.get('Event-Name') == 'CUSTOM':
                    if event.get('VM-Action') == 'leave-message':
                        user = event.get("VM-User")
                        try:
                            user = config.get('extensions', user)
                            post_message(read_leave_message(event), mm_webhook, user=user)
                        except NoOptionError:
                            print 'No Mattermost user for extension {}'.format(user)

    else:
        print 'Could not connect to ESL'


if __name__ == '__main__':
    main()