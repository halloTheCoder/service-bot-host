# FRIENDLY NAME
# hallo

# SID
# SKe2e247b78a3395c848d60e2199838a57

# KEY TYPE
# Standard

# SECRET
# 4RSi6PLG50sW3QQzlv2XkiL1C9zzyGCc

import os
from twilio.http.http_client import TwilioHttpClient
from twilio.rest import Client
from credentials import account_sid,auth_token,twilio_no

class Msg:
	def __init__(self):
		self.proxy_client = TwilioHttpClient()

		self.proxy_client.session.proxies = {
											 'https': os.environ['https_proxy'],
											 'http': os.environ['http_proxy']
											}

		self.account_sid = account_sid
		self.auth_token = auth_token
		
		self.client = Client(self.account_sid, self.auth_token,http_client=self.proxy_client)

	def send_msg(self, text, to = "+918250599363", from_ = twilio_no):
		msg = " :: "+text
		call = self.client.messages.create(
		    to=to,
		    from_=from_,
		    body=msg
		)