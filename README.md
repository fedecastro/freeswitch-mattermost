 Freeswitch Mattermost Plugin
===============================

A plugin to notify a [Mattermost](http://www.mattermost.org/) server about [Freeswitch](https://freeswitch.com/oss/) events.

New call, answer and hang up are notified to the channel asociated to the webhook

Missed call and new voicemail are notified to individual users

## Plugin configuration

### Make plugin executable

`chmod +x freemat.py`

### Set variables in freemat.ini:

`mm_webhook`  Mattermost webhook URL here.

`esl_server` ESL server IP address.

`esl_port`   ESL server port.

`esl_secret` ESL secret.

`notify_caller` set to True if want to notify caller too

Complete `extensions` section to allow `freemat` to notify users about missed calls and new voicemails

## Plugin requirements

* [Python Request](http://docs.python-requests.org/en/master/)
* [Python ESL](https://pypi.org/project/python-ESL/)
* [Freeswitch ESL module](https://freeswitch.org/confluence/display/FREESWITCH/Python+ESL)


## Plugin usage

`./freemat.py`


### To run it on background

`nohup ./freemat.py &`