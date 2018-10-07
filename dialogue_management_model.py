import rasa_core
from rasa_core.agent import Agent
from rasa_core.interpreter import RasaNLUInterpreter
from rasa_core.utils import EndpointConfig


def dialogue_initialization():
	print('Loading Model')

	interpreter = RasaNLUInterpreter('./models/nlu_tf/default/service_nlu')
	action_endpoint = EndpointConfig(url = "http://localhost:5055/webhook")
	
	agent = Agent.load('./models/dialogue', interpreter = interpreter, action_endpoint = action_endpoint)
	
	print('Model loaded')

	return agent
	
def run_service_bot(text, agent, serve_forever = True):
	responses = agent.handle_text(text)
	print(responses)

	ans = ""

	for i in range(len(responses)):
		if 'recipient_id' in responses[i]:
			ans += responses[i]['text']
			if not i == (len(responses) - 1):
				ans += '\n'

	# rasa_core.run.serve_application(agent ,channel = 'cmdline')
		
	return ans
