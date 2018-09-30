from flask import Flask, session
from flask import render_template,jsonify,request
import requests
import pickle


import random
import numpy as np
import json
import os

from dialogue_management_model import run_service_bot, dialogue_initialization

app = Flask(__name__)
app.secret_key = '12345'

agent = None

@app.route('/')
def hello_world():
	global agent
	agent = dialogue_initialization()
	return render_template('home.html')


@app.route('/chat',methods=["POST"])
def chat():
	user_message = request.form["text"]
	print(user_message)
	print(type(user_message))
	
	global agent
	response = run_service_bot(user_message, agent)
	print(response)
	
	return jsonify({"status":"success","response":str(response)})


if __name__ == "__main__":
	# port = int(os.environ['PORT'])
	port = 8080
	app.run(host='localhost', port = port, debug = True, threaded = True)
	# text = 'Show me a veg pizza'
	# nlu = NLU()
	# intent,entites = nlu.nlu(text)
	# print(intent,entites)