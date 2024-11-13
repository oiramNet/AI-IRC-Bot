import os
import sys
import socket
import ssl
import time
import configparser
import pyshorteners
from typing import Union, Tuple
import datetime
import pytz
import random
import string
import openai
import anthropic

print("")
print("+----------------------------------------+")
print("|               AI IRC Bot               |")
print("|          by Mariusz J. Handke          |")
print("|      oiram@IRCnet   oiram@IRCnet2      |")
print("|                                        |")
print("| https://github.com/oiramNet/AI-IRC-Bot |")
print("+----------------------------------------+")
print("")

#
# DEFINITIONS
# 

# Lists of supported AI models

# ChatGPT (OpenAI)
#  REF: https://platform.openai.com/docs/models
chatcompletion_models = ["gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-4-turbo", "gpt-4-turbo-preview", "gpt-3.5-turbo"]
images_models = ["dall-e-2", "dall-e-3"]

# Claude(Anthropic)
#  REF: https://docs.anthropic.com/en/docs/about-claude/models
anthropic_models = ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"]

# other global settings
reconnect = 5

def printDebug(debug, txt):
	"""
	Print the text for debugging purposes
	"""
	if debug:
		print("DEBUG: " + txt)

def srand(N):
	"""
	Generate string of N random characters (uppercase letters, digits)
	"""
	return "".join(random.choices(string.ascii_uppercase + string.digits, k=N))

def timeInUtc():
	"""
	Generate string containing current date and time in UTC 
	"""
	dt = datetime.datetime.now(pytz.timezone('UTC'))
	now_of_year = dt.strftime("%Y")
	now_of_month = dt.strftime("%B")
	now_of_day = dt.strftime("%d")
	now_of_wday = dt.strftime("%A")
	now_of_time = dt.strftime("%H:%M")
	system_message_content = f"Today is {now_of_wday}, the year is {now_of_year}, the month is {now_of_month}, and the date is {now_of_day}. " \
	f"The current time in UTC is {now_of_time}."
	return system_message_content

def strtobool(val):
	"""
	Return BOOLEAN value of the input string
		True: 'y'|'yes'|'t'|'true'|'on'|'1'
		False: 'n'|'no'|'f'|'false'|'off'|'0'
	"""
	match val.lower().strip():
		case 'y'|'yes'|'t'|'true'|'on'|'1':
			return 1
		case 'n'|'no'|'f'|'false'|'off'|'0':
			return 0
		case _:
			raise ValueError("Invalid logical value %r" % (val,))

def getData(sock):
	"""
	Pull (read) data (4096 bytes) from SOCKET and decode it as UTF-8
	"""
	return sock.recv(4096).decode("UTF-8")

def nextServer(id, idmax):
	"""
	Return index of next server on the list, or start from beginning
	"""
	if id == idmax:
		return 0
	else:
		return id + 1

def netConnect(server, port, usessl):
	"""
	Connect using SSL (if specified) to the remote server on specified port
	and return SOCKET
	"""
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.connect((server, int(port)))
	if strtobool(usessl):
		context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
		context.check_hostname = False
		context.verify_mode = ssl.CERT_NONE
		sock = context.wrap_socket(sock, server_hostname=server)
	return sock

def ircAuth(irc, password, ident, realname, nickname):
	"""
	Authenticate with IRC server
	"""
	if password:
		irc.send(bytes("PASS " + password + "\n", "UTF-8"))
	irc.send(bytes("USER " + ident + " 0 * :" + realname + "\n", "UTF-8"))
	irc.send(bytes("NICK " + nickname + "\n", "UTF-8"))

def ircSetNick(irc, nick, nickname):
	"""
	Set the nickname
		nick: correct/expected nickname (from config)
		nickname: random nickname (eg. generated during connection)
	"""
	irc.send(bytes("NICK " + nick + "\n", "UTF-8"))
	ircmsg = getData(irc)
	rcode = ircmsg.split()[1]
	rnick = nickname
	match rcode:
		case "432":
			"""
			ERR_ERRONEUSNICKNAME (RFC1459)
			"""
			print("ERROR: Erroneus nickname (" + nick + "). Using random nickname instead (" + nickname + ")")
		case "433":
			"""
			ERR_NICKNAMEINUSE (RFC1459)
			"""
			print("ERROR: My nickname (" + nick + ") is in use. Using random nickname instead (" + nickname + ")")
		case _:
			"""
			UNKNOWN RCODE
			"""
			print("INFO: RCODE = ", rcode)
			rnick = nick
	return rnick

def ircJoinChannels(irc, channels):
	"""
	Join channels
	"""
	irc.send(bytes("JOIN " + ",".join(channels) + "\n", "UTF-8"))
#	ircmsg = ""
#	while ircmsg.find("End of /NAMES list.") == -1:
#		ircmsg = getData(irc)
#		print("ircmsg = ", ircmsg)

def ircConnect(server, port, usessl, password, ident, realname, wait):
	"""
	Connect to IRC server using RANDOM nick
	"""
	time.sleep(wait)
	#generate 9 characters random nick (AIbot####)
	nickname = ("AIbot" + srand(4))[:9]
	try:
		print("INFO: Connecting to " + server)
		irc = netConnect(server, port, usessl)
		ircAuth(irc, password, ident, realname, nickname)
		ircmsg = getData(irc)
		rcode = ircmsg.split()[1]
		if rcode == "020":
			"""
			some IRC server send info message/motd/...
			"""
			ircmsg = getData(irc)
			rcode = ircmsg.split()[1]
		match rcode:
			case "001":
				"""
				RPL_WELCOME (RFC2812)
				"""
			case "432":
				"""
				ERR_ERRONEUSNICKNAME (RFC1459)
				"""
			case "433":
				"""
				ERR_NICKNAMEINUSE (RFC1459)
				"""
			case _:
				"""
				UNKNOWN RCODE
				"""
				print("INFO: RCODE = ", rcode)
	except:
		print("ERROR: Connection to " + server + " failed")
	ircmsg = getData(irc)
	return irc, nickname

def isIrcConnected(irc, server, port, usessl, password, ident, realname, nickname, channels, wait):
	"""
	Check if connected to IRC server and display connection details
	"""
	try:
		irc.getpeername()
		print("INFO: Connected to IRC")
		print("\tSERVER: " + server)
		print("\tNICK: " + nickname)
		print("\tCHANNELS: ", end="")
		print(*channels, sep =', ')
		return True
	except socket.error:
		print("INFO: Not connected to IRC")
		return False

def sendMessageToIrcChannel(irc, channel, reply_to, message):
	"""
	Send message to IRC channel
	"""
	if reply_to != "":
		irc.send(bytes("PRIVMSG " + channel + " :" + reply_to + ": ...\n", "UTF-8"))
	msgs = [x.strip() for x in message]
	for msg in msgs:
		while len(msg) > 0:
			if len(msg) <= 392:
				irc.send(bytes("PRIVMSG " + channel + " :" + msg + "\n", "UTF-8"))
				msg = ""
			else:
				last_space_index = msg[:392].rfind(" ")
				if last_space_index == -1:
					last_space_index = 392
				irc.send(bytes("PRIVMSG " + channel + " :" + msg[:last_space_index] + "\n", "UTF-8"))
				msg = msg[last_space_index:].lstrip()

def prepMessages(history, previous_QA, question):
	"""
	Create list of messages
	"""
	messages = []
	if history > 0:
		for q, a in previous_QA[-history:]:
			messages.append({ "role": "user", "content": q })
			messages.append({ "role": "assistant", "content": a })
	messages.append({ "role": "user", "content": question })
	return messages


#
# CONFIGURATION
#
# - name of the configuration file is passed as a command-line argument
#

# Check if configuration file name was provided
if len(sys.argv)>1:
	# Read configuration file
	conf_file = sys.argv[1]
	if os.path.isfile(conf_file):
		print("INFO: Loading configuration file (" + conf_file + ")")
		config = configparser.ConfigParser()
		config.read(conf_file)
	else:
		print("ERROR: Specified configuration file (" + conf_file + ") does not exist.\n")
		exit(1)
else:
	print("ERROR: Missing configuration file name.\n\nUSAGE: " + sys.argv[0] + " conf_file\n")
	exit(1)

try:
	# Set up AI model
	model = config.get('AI', 'model')
	# Set up API KEY
	api_key = config.get('AI', 'api_key')
	# Create AI object based on model and assign API KEY
	if (model in chatcompletion_models) | (model in images_models):
		ai_type = "ChatGPT (OpenAI)"
#		ai = openai.OpenAI()	# openai >= 1.x
		ai = openai				# openai 0.28.x
	elif model in anthropic_models:
		ai_type = "Claude (Anthropic)"
		ai = anthropic.Anthropic()
	else:
		print("ERROR: Invalid model selected.\n")
		exit(1)
	ai_type = ai_type + " and model " + model
	ai.api_key = api_key

	# Set up AI parameters
	temperature = config.getfloat('AI', 'temperature')
	max_tokens = config.getint('AI', 'max_tokens')
	top_p = config.getint('AI', 'top_p')
	frequency_penalty = config.getint('AI', 'frequency_penalty')
	presence_penalty = config.getint('AI', 'presence_penalty')
	request_timeout = config.getint('AI', 'request_timeout')
	context = config.get('AI', 'context')
	history = config.getint('AI', 'history')

	# Set up IRC connection settings
	servers = "".join(config.get('IRC', 'servers').split()).split(',')
	ident = config.get('IRC', 'ident')
	realname = config.get('IRC', 'realname')
	nick = config.get('IRC', 'nickname')[:9]
	channels = "".join(config.get('IRC', 'channels').split()).split(',')
	accept_invites = config.getboolean('IRC', 'accept_invites', fallback=False)
	rejoin_invited = config.getboolean('IRC', 'rejoin_invited', fallback=False)
	debug = config.getboolean('IRC', 'debug', fallback=False)

except Exception as e:
	print("ERROR: Missing or invalid configuration option(s)")
	print(""  + str(e) + "\n")
	exit(1)



#
# EXECUTION
#

print("INFO: This bot is configured to use " + ai_type)
server_id = 0
server_id_max = len(servers)-1
irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
previous_QA = []


# Listen for messages from users and answer questions
while True:

	# Check if data is received and connect/re-connect if needed
	while True:
		try:
			ircmsg = getData(irc).strip()
			break
		except UnicodeDecodeError:
			continue
		except:
			if 'ircmsg' in globals():
				print("ERROR: Connection to IRC lost (" + srv[0] + "). Reconnecting in " + str(reconnect) + " seconds...")
				server_id = nextServer(server_id, server_id_max)
			else:
				print("INFO: Starting...")
			srv = servers[server_id].split(':')
			#connect with a random nick (AIbot####)
			irc, nickname = ircConnect(srv[0], srv[1], srv[2], srv[3], ident, realname, reconnect)
			#set correct nick (from config) if not possible use previously generated random nick (AIbot####)
			nickname = ircSetNick(irc, nick, nickname)
			#join permanent channels (from config)
			ircJoinChannels(irc, channels)
			#display connection details
			if isIrcConnected(irc, srv[0], srv[1], srv[2], srv[3], ident, realname, nickname, channels, 0):
				"""
				"""
			else:
				"""
				"""
			print("---\n")

	if len(ircmsg) > 0:
		"""
		Split received data into segments depending on message format
		FORMAT-1: [command] [:server]
		FORMAT-2: [:sender|server] [command] [channel] [:MESSAGE]
					MESSAGE is what user writes to the channel
							when addressing other users the common format is "USER: text"
							full FORMAT-2: [:sender] [command] [channel] [:USER:] [text]
		"""
		chunk = ircmsg.split()
		if chunk[0].startswith(":"):
			"""
			Received server or channel message (FORMAT-2)
			"""
			printDebug(debug, "ircmsg = [" + ircmsg + "]")

#			if chunk[0][1:].lower() == server.lower():
#				srvmsg = True
#			else
#				srvmsg = False

#			srvmsg = (chunk[0][1:].lower() == srv[0].lower())
#			print("A = " + chunk[0][1:].lower())
#			print("B = " + srv[0].lower())
#			print("srvmsg = [", srvmsg, "]")

			command = chunk[1]
			who_full = chunk[0][1:]
			who_nick = who_full.split("!")[0]
		else:
			"""
			Received special server message (FORMAT-1, e.g. PING)
			"""
			command = chunk[0]
			who_full = ""
			who_nick = ""

		channel = ""

		match command:
			case "353" | "366":
				"""
				353: RPL_NAMREPLY (RFC1459)
				366: RPL_ENDOFNAMES (RFC1459)
				"""
			case "471" | "473" | "474" | "475":
				"""
				471: ERR_CHANNELISFULL (RFC1459)
				473: ERR_INVITEONLYCHAN (RFC1459)
				474: ERR_BANNEDFROMCHAN (RFC1459)
				475: ERR_BADCHANNELKEY (RFC1459)
				"""
				channel = chunk[3].replace(":", "")
				print("ERROR: Unable to join " + channel + ": Channel can be full, invite only, bot is banned or needs a key.\n")
			case "ERROR":
				print("ERROR: Received an ERROR from the server. Reconnecting in " + str(reconnect) + " seconds...\n")
				irc.close()
				irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			case "INVITE":
				if accept_invites:
					channel = chunk[3].replace(":", "")
					print("INFO: Invited into channel " + channel + " by " + who_full + ". Joining...\n")
					irc.send(bytes("JOIN " + channel + "\n", "UTF-8"))
			case "JOIN":
				""" no actions """
			case "KICK":
				if chunk[3].lower() == nickname.lower():
					channel = chunk[2].replace(":", "")
					print("INFO: Kicked from channel " + channel + " by " + who_full + ".", end="")
					if channel in channels or rejoin_invited:
						print(" Rejoining...\n")
						irc.send(bytes("JOIN " + channel + "\n", "UTF-8"))
					else:
						print("\n")
			case "MODE":
				""" no actions """
			case "PING":
				irc.send(bytes("PONG " + chunk[1] + "\n", "UTF-8"))
			case "PRIVMSG":
				"""
				Processing channel message
				"""
				chunk0to3 = chunk[0] + " " + chunk[1] + " " + chunk[2] + " " + chunk[3] + " "
				channel = chunk[2].replace(":", "")
				to = chunk[3].replace(":", "")
				if channel.startswith("#") and to.lower() == nickname.lower():
					""" prepare assistant's profile with current time included """
					profile = str(timeInUtc()) + " " + context
					""" pull out the question """
					question = ircmsg[len(chunk0to3):].strip()
					print(who_full + " : " + question)
					""" process message in accordance with selected model """
					if model in chatcompletion_models:
						""" OpenAI """
						messages = [{ "role": "system", "content": profile }] + prepMessages(history, previous_QA, question)
						try:
#							response = ai.chat.completions.create(
							response = ai.ChatCompletion.create(
								model=model,
								max_tokens=max_tokens,
								temperature=temperature,
								messages=messages,
								frequency_penalty=frequency_penalty,
								presence_penalty=presence_penalty,
								request_timeout=request_timeout,
								response_format={"type": "text"}
							)
							answers = response.choices[0].message.content.strip()
							previous_QA.append((question, answers))
							sendMessageToIrcChannel(irc, channel, who_nick, answers.split('\n'))
						except ai.error.Timeout as e:
							print("ERROR: " + str(e) + "\n")
						except ai.error.OpenAIError as e:
							print("ERROR: " + str(e) + "\n")
						except Exception as e:
							print("ERROR: " + str(e) + "\n")
					elif model in images_models:
						""" OpenAI """
						try:
							response = ai.Image.create(
								model=model,
								prompt=question,
								n=1,
								size="1024x1024"
							)
							long_url = response.ircmsg[0].url
							type_tiny = pyshorteners.Shortener()
							short_url = type_tiny.tinyurl.short(long_url)
							sendMessageToIrcChannel(irc, channel, who_nick, short_url)
						except ai.error.Timeout as e:
							print("ERROR: " + str(e) + "\n")
						except ai.error.OpenAIError as e:
							print("ERROR: " + str(e) + "\n")
						except Exception as e:
							print("ERROR: " + str(e) + "\n")
					elif model in anthropic_models:
						""" Antropic """
						messages = [] + prepMessages(history, previous_QA, question)
						try:
							response = ai.messages.create(
								model=model,
								max_tokens=max_tokens,
								temperature=temperature,
								system=profile,
								messages=messages,
							)
							answers = response.content[0].text.strip()
							previous_QA.append((question, answers))
							sendMessageToIrcChannel(irc, channel, who_nick, answers.split('\n'))
						except ai.APIConnectionError as e:
							print("ERROR: The server could not be reached." + str(e) + "\n")
							print(e.__cause__)
						except ai.RateLimitError as e:
							print("A 429 status code was received; we should back off a bit.")
							print("ERROR: A 429 status code was received; we should back off a bit.\n")
						except ai.APIStatusError as e:
							print("Another non-200-range status code was received")
							print("ERROR: Another non-200-range status code was received.\n")
							print(e.status_code)
							print(e.response)
						except Exception as e:
							print("ERROR: " + str(e) + "\n")
					else:
						print("ERROR: Invalid model selected.\n")
						continue
			case "QUIT":
				print("", end="")
			case _:
				print("", end="")
	else:
		continue
	time.sleep(1)
