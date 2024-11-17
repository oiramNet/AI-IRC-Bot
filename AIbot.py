import os
import sys
import socket
import ssl
import configparser
import time
import datetime
import pytz
from typing import Union, Tuple
import random
import string
import pyshorteners
"""
AI API(s)
"""
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

def printError(txt):
	"""
	Print the error message
	"""
	print("ERROR: " + txt)

def printInfo(txt):
	"""
	Print the info message
	"""
	print("INFO: " + txt)

def srand(N):
	"""
	Generate string of N random characters (uppercase letters, digits)
	"""
	return "".join(random.choices(string.ascii_uppercase + string.digits, k=N))

def nowUTC():
	"""
	Get current date/time in 24-hour format in UTC
	"""
	return datetime.datetime.now(pytz.timezone('UTC'))

def todayIsUTC():
	"""
	Generate string containing current date and time in 24-hour format in UTC 
	"""
	dt = nowUTC()
	now_of_year = dt.strftime("%Y")
	now_of_month = dt.strftime("%B")
	now_of_day = dt.strftime("%d")
	now_of_wday = dt.strftime("%A")
	now_of_time = dt.strftime("%H:%M:%S")
	x = "Today is " + now_of_wday + ", the day is " + now_of_day + ", the month is " + now_of_month + ", and the year is " + now_of_year + ". "
	x += "The current time in 24-hour format and UTC time zone is " + now_of_time + ". "
	return x

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
		sslcontext = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
		sslcontext.check_hostname = False
		sslcontext.verify_mode = ssl.CERT_NONE
		sock = sslcontext.wrap_socket(sock, server_hostname=server)
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
			printError("Erroneus nickname (" + nick + "). Using random nickname instead (" + nickname + ")")
		case "433":
			"""
			ERR_NICKNAMEINUSE (RFC1459)
			"""
			printError("My nickname (" + nick + ") is in use. Using random nickname instead (" + nickname + ")")
		case _:
			"""
			UNKNOWN RCODE
			"""
			printInfo("RCODE = " + str(rcode))
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
		printInfo("Connecting to " + server)
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
				printInfo("RCODE = " + str(rcode))
	except:
		printError("Connection to " + server + " failed")
	ircmsg = getData(irc)
	return irc, nickname

def isIrcConnected(irc, server, port, usessl, password, ident, realname, nickname, channels, wait):
	"""
	Check if connected to IRC server and display connection details
	"""
	try:
		irc.getpeername()
		printInfo("Connected to IRC")
		print("\tSERVER: " + server)
		print("\tNICK: " + nickname)
		print("\tCHANNELS: ", end="")
		print(*channels, sep =', ')
		return True
	except socket.error:
		printInfo("Not connected to IRC")
		return False

def ircConnectionDetails(irc, server, port, usessl, password, ident, realname, nickname, channels):
	"""
	Display IRC connection details
	"""
	try:
		irc.getpeername()
		printInfo("Connected to IRC")
		print("\tSERVER: " + server)
		print("\tNICK: " + nickname)
		print("\tCHANNELS: ", end="")
		print(*channels, sep =', ')
	except socket.error:
		printInfo("Not connected to IRC")

def sendMessageToIrcChannel(irc, channel, reply_to, message):
	"""
	Send message to IRC channel
	"""
	if reply_to != "":
		irc.send(bytes("PRIVMSG " + channel + " :" + reply_to + ": ...\n", "UTF-8"))
	msgs = [x.strip() for x in message.split('\n')]
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

def getChannelHistory(previous_QA, channel, N):
	"""
	Create list of last-N Q/A pairs for the channel.
		N > 0 return N pairs
		N = 0 do not return any pairs
		N < 0 return all pairs
	"""
	previous_QA_chan = []
	for sub_arr in previous_QA:
		if sub_arr[0].lower() == channel.lower():
			previous_QA_chan.append(sub_arr)
	if (N < 0):
		return previous_QA_chan
	elif (N == 0):
		return []
	else:
		return previous_QA_chan[-N:]

def leaveInChannelHistory(previous_QA, channel, N):
	"""
	Leave last-N Q/A pairs in channel history
		N > 0 leave N pairs
		N = 0 leave no pairs (remove all)
		N < 0 leave all pairs (remove none)
	"""
	previous_QA_chan = getChannelHistory(previous_QA, channel, -1)
	cnt = len(previous_QA_chan)
	todelete = []
	if (N < 0):
		""" do nothing """
	elif (N == 0):
		todelete = previous_QA_chan
	else:
		if (N < cnt):
			todelete = previous_QA_chan[0:(cnt-N)]
	for sub_arr in todelete:
		previous_QA.remove(sub_arr)

def prepMessages(previous_QA, channel, history, question):
	"""
	Create list of AI-readable messages
	"""
	#get previous Q/A pairs
	previous_QA_chan = getChannelHistory(previous_QA, channel, history)
	#change into list of AI-readable messages (user/assistant pairs)
	messages = []
	for c, t, n, q, a in previous_QA_chan[:]:
		messages.append({"role": "user", "content": q})
		messages.append({"role": "assistant", "content": a})
	#append current question
	messages.append({"role": "user", "content": question})
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
		printInfo("Loading configuration file (" + conf_file + ")")
		config = configparser.ConfigParser()
		config.read(conf_file)
	else:
		printError("Specified configuration file (" + conf_file + ") does not exist.\n")
		exit(1)
else:
	printError("Missing configuration file name.\n\nUSAGE: " + sys.argv[0] + " conf_file\n")
	exit(1)

try:
	# Set up AI model
	AI_MODEL = config.get('AI', 'model')
	# Set up API KEY
	AI_API_KEY = config.get('AI', 'api_key')
	# Create AI object based on AI_MODEL and assign AI_API_KEY
	if (AI_MODEL in chatcompletion_models) | (AI_MODEL in images_models):
		ai_type = "ChatGPT (OpenAI)"
		ai = openai.OpenAI(api_key=AI_API_KEY)
	elif (AI_MODEL in anthropic_models):
		ai_type = "Claude (Anthropic)"
		ai = anthropic.Anthropic(api_key=AI_API_KEY)
	else:
		printError("Invalid AI model selected.\n")
		exit(1)
	ai_type = ai_type + " and model " + AI_MODEL

	# Set up AI parameters
	TEMPERATURE = config.getfloat('AI', 'temperature', fallback=0.5)
	TOP_P = config.getint('AI', 'top_p', fallback=1)
	MAX_TOKENS = config.getint('AI', 'max_tokens', fallback=1000)
	FREQUENCY_PENALTY = config.getint('AI', 'frequency_penalty', fallback=0)
	PRESENCE_PENALTY = config.getint('AI', 'presence_penalty', fallback=0)
	REQUEST_TIMEOUT = config.getint('AI', 'request_timeout', fallback=60)
	CONTEXT = config.get('AI', 'context', fallback="You are helpful and friendly assistant.")
	HISTORY = config.getint('AI', 'history', fallback=0)
	USE_NICK = config.getboolean('AI', 'use_nick', fallback=True)

	# Set up IRC connection settings
	DEBUG = config.getboolean('IRC', 'debug', fallback=False)
	SERVERS = "".join(config.get('IRC', 'servers').split()).split(',')
	IDENT = config.get('IRC', 'ident')
	REALNAME = config.get('IRC', 'realname')
	NICK = config.get('IRC', 'nickname')[:9]
	CHANNELS = "".join(config.get('IRC', 'channels').split()).split(',')
	ACCEPT_INVITES = config.getboolean('IRC', 'accept_invites', fallback=False)
	REJOIN_INVITED = config.getboolean('IRC', 'rejoin_invited', fallback=False)

except Exception as e:
	printError("Missing or invalid configuration option(s)\n" + str(e) + "\n")
	exit(1)



#
# EXECUTION
#

printInfo("This bot is configured to use " + ai_type)
server_id = 0
server_id_max = len(SERVERS)-1
irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
"""
ELEMENT FORMAT: CHANNEL, TIMESTAMP, NICK, QUESTION, ANSWER
"""
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
			if ('ircmsg' in globals()):
				printError("Connection to IRC lost (" + srv[0] + "). Reconnecting in " + str(reconnect) + " seconds...")
				server_id = nextServer(server_id, server_id_max)
			else:
				printInfo("Starting...")
			srv = SERVERS[server_id].split(':')
			#connect with a random nick (AIbot####)
			irc, nickname = ircConnect(srv[0], srv[1], srv[2], srv[3], IDENT, REALNAME, reconnect)
			#set correct nick (from config) if not possible use previously generated random nick (AIbot####)
			nickname = ircSetNick(irc, NICK, nickname)
			#join permanent channels (from config)
			ircJoinChannels(irc, CHANNELS)
			#display connection details
#			if isIrcConnected(irc, srv[0], srv[1], srv[2], srv[3], IDENT, REALNAME, nickname, CHANNELS, 0):
#				"""
#				"""
#			else:
#				"""
#				"""
			ircConnectionDetails(irc, srv[0], srv[1], srv[2], srv[3], IDENT, REALNAME, nickname, CHANNELS)
			print("---\n")

	if (len(ircmsg) > 0):
		"""
		Split received data into segments depending on message format
		FORMAT-1: [command] [:server]
		FORMAT-2: [:sender|server] [command] [channel] [:MESSAGE]
					MESSAGE is what user writes to the channel
							when addressing other users the common format is "USER: text"
							full FORMAT-2: [:sender] [command] [channel] [:USER:] [text]
		"""
		chunk = ircmsg.split()
		if (chunk[0].startswith(":")):
			"""
			Received server or channel message (FORMAT-2)
			"""
			printDebug(DEBUG, "ircmsg = [" + ircmsg + "]")
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
				printError("Unable to join " + channel + ": Channel can be full, invite only, bot is banned or needs a key.\n")
			case "ERROR":
				printError("Received an ERROR from the server. Reconnecting in " + str(reconnect) + " seconds...\n")
				irc.close()
				irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			case "INVITE":
				if (ACCEPT_INVITES):
					channel = chunk[3].replace(":", "")
					printInfo("Invited into channel " + channel + " by " + who_full + ". Joining...\n")
					irc.send(bytes("JOIN " + channel + "\n", "UTF-8"))
			case "JOIN":
				""" no actions """
			case "KICK":
				if (chunk[3].lower() == nickname.lower()):
					channel = chunk[2].replace(":", "")
					printInfo("Kicked from channel " + channel + " by " + who_full + ".")
					if (channel in CHANNELS) or (REJOIN_INVITED):
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
				""" to whom message is addressed """
				to = chunk[3][1:]
				""" respond if channel starts with # and if message is addressed to me """
				if (channel.startswith("#")) and ((to.lower()) == (nickname.lower() + ":")):
					""" set the history """
					leaveInChannelHistory(previous_QA, channel, HISTORY)
					""" prepare assistant's profile (instructions) with current time included """
					profile = todayIsUTC() + CONTEXT
					if (USE_NICK):
						profile += " When responding, address the person using their nickname. This question was asked by a person who's nickname is " + who_nick + "."
					""" pull out the question """
					question = ircmsg[len(chunk0to3):].strip()
					""" display question on console (CHANNEL : WHO_FULL : QUESTION) """
					print(channel + " : " + who_full + " : " + question)
					""" process message in accordance with selected AI_MODEL """
					if (AI_MODEL in chatcompletion_models):
						""" OpenAI """
						messages = [{ "role": "system", "content": profile }] + prepMessages(previous_QA, channel, HISTORY, question)
						try:
							response = ai.chat.completions.create(
								model=AI_MODEL,
								max_tokens=MAX_TOKENS,
								temperature=TEMPERATURE,
								messages=messages,
								frequency_penalty=FREQUENCY_PENALTY,
								presence_penalty=PRESENCE_PENALTY,
								response_format={"type": "text"}
							)
							answers = response.choices[0].message.content.strip()
							previous_QA.append((channel, nowUTC().timestamp(), who_nick, question, answers))
							sendMessageToIrcChannel(irc, channel, who_nick, answers)
						except ai.error.Timeout as e:
							printError(str(e) + "\n")
						except ai.error.OpenAIError as e:
							printError(str(e) + "\n")
						except Exception as e:
							printError(str(e) + "\n")
					elif (AI_MODEL in images_models):
						""" OpenAI """
						try:
							response = ai.Image.create(
								model=AI_MODEL,
								prompt=question,
								n=1,
								size="1024x1024"
							)
							long_url = response.ircmsg[0].url
							type_tiny = pyshorteners.Shortener()
							short_url = type_tiny.tinyurl.short(long_url)
							sendMessageToIrcChannel(irc, channel, who_nick, short_url)
						except ai.error.Timeout as e:
							printError(str(e) + "\n")
						except ai.error.OpenAIError as e:
							printError(str(e) + "\n")
						except Exception as e:
							printError(str(e) + "\n")
					elif (AI_MODEL in anthropic_models):
						""" Anthropic """
						messages = [] + prepMessages(previous_QA, channel, HISTORY, question)
						try:
							response = ai.messages.create(
								model=AI_MODEL,
								max_tokens=MAX_TOKENS,
								temperature=TEMPERATURE,
								system=profile,
								messages=messages,
							)
							answers = response.content[0].text.strip()
							previous_QA.append((channel, nowUTC().timestamp(), who_nick, question, answers))
							sendMessageToIrcChannel(irc, channel, who_nick, answers)
						except ai.APIConnectionError as e:
							printError("The server could not be reached." + str(e) + "\n")
							print(e.__cause__)
						except ai.RateLimitError as e:
							printError("A 429 status code was received; we should back off a bit.\n")
						except ai.APIStatusError as e:
							printError("Another non-200-range status code was received.\n")
							print(e.status_code)
							print(e.response)
						except Exception as e:
							printError(str(e) + "\n")
					else:
						printError("Invalid AI model selected.\n")
						continue
			case "QUIT":
				print("", end="")
			case _:
				print("", end="")
	else:
		continue
	time.sleep(1)
