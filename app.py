from flask import Flask, session
from flask import render_template,jsonify,request
import requests
import pickle


import random
import numpy as np
import json
import os

# from dialogue_management_model import run_service_bot, dialogue_initialization

import rasa_core
from rasa_core.agent import Agent
from rasa_core.interpreter import RasaNLUInterpreter
from rasa_core.utils import EndpointConfig

app = Flask(__name__)
app.secret_key = '12345'

agent = None

@app.route('/')
def hello_world():
	global agent

	print('Loading Model')

	interpreter = RasaNLUInterpreter('./models/nlu_tf/default/service_nlu')
	action_endpoint = EndpointConfig(url = "http://localhost:5055/webhook")
	
	agent = Agent.load('./models/dialogue', interpreter = interpreter, action_endpoint = action_endpoint)
	
	print('Model loaded')

	return render_template('home.html')


@app.route('/chat',methods=["POST"])
def chat():
	user_message = request.form["text"]
	print(user_message)
	print(type(user_message))
	
	global agent

	responses = agent.handle_text(user_message)
	print(responses)

	ans = ""

	for i in range(len(responses)):
		if 'recipient_id' in responses[i]:
			ans += responses[i]['text']
			if not i == (len(responses) - 1):
				ans += '\n'
	
	print(ans)

	return jsonify({"status":"success","response":str(ans)})


if __name__ == "__main__":
	# port = int(os.environ['PORT'])
	port = 8888
	app.run(host='localhost', port = port, debug = True)