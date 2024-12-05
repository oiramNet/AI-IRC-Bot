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

VERSION = "20241206"
AUTHOR = "Mariusz J. Handke"
AUTHOR_NICK = "oiram"
GH = "https://github.com/oiramNet/AI-IRC-Bot"

print("")
print("+----------------------------------------+")
print("|               AI IRC Bot               |")
print("|                " + VERSION + "                |")
print("|          by " + AUTHOR + "          |")
print("|      " + AUTHOR_NICK + "@IRCnet   " + AUTHOR_NICK + "@IRCnet2      |")
print("|                                        |")
print("| " + GH + " |")
print("+----------------------------------------+")
print("")

#
# DEFINITIONS
# 

"""
Lists of supported AI models
	ELEMENT:	API(VENDOR), NAME, TYPE(CHAT or IMAGE), MODELS
"""
MODEL = [
["Anthropic",	"Claude",		"CHAT",		"claude-3-5-sonnet-latest"],
["Anthropic",	"Claude",		"CHAT",		"claude-3-5-haiku-latest"],
["OpenAI",		"ChatGPT",	"CHAT",		"gpt-4o"],
["OpenAI",		"ChatGPT",	"CHAT",		"gpt-4o-mini"],
["OpenAI",		"ChatGPT",	"CHAT",		"gpt-4"],
["OpenAI",		"ChatGPT",	"CHAT",		"gpt-4-turbo"],
["OpenAI",		"ChatGPT",	"CHAT",		"gpt-4-turbo-preview"],
["OpenAI",		"ChatGPT",	"CHAT",		"gpt-3.5-turbo"],
["OpenAI",		"DALL",			"IMAGE",	"dall-e-2"],
["OpenAI",		"DALL",			"IMAGE",	"dall-e-3"],
]

# other global settings
reconnect = 5

def printDebug(debug, txt):
	"""
	PURPOSE:	Print the text with DEBUG header
	VERIFIED:	YES
	"""
	if debug:
		print("DEBUG: " + txt)

def printError(txt):
	"""
	PURPOSE:	Print the text with ERROR header
	VERIFIED:	YES
	"""
	print("ERROR: " + txt)

def printInfo(txt):
	"""
	PURPOSE:	Print the text with INFO header
	VERIFIED:	YES
	"""
	print("INFO: " + txt)

def srand(N):
	"""
	PURPOSE:	Return string of N random characters (uppercase letters and digits only)
	VERIFIED:	YES
	"""
	return "".join(random.choices(string.ascii_uppercase + string.digits, k=N))

def nowUTC():
	"""
	PURPOSE:	Return current date/time in 24-hour format in UTC
	VERIFIED:	YES
	"""
	return datetime.datetime.now(pytz.timezone('UTC'))

def todayIsUTC():
	"""
	PURPOSE:	Return string containing current date and time in 24-hour format in UTC 
	VERIFIED:	YES
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

def strtobool(val):	# not used
	"""
	PURPOSE:	Return BOOLEAN value of the input string
							True: 'y'|'yes'|'t'|'true'|'on'|'1'
							False: 'n'|'no'|'f'|'false'|'off'|'0'
	VERIFIED:	YES
	"""
	match (val.lower().strip()):
		case 'y'|'yes'|'t'|'true'|'on'|'1':
			return 1
		case 'n'|'no'|'f'|'false'|'off'|'0':
			return 0
		case _:
			raise ValueError("Invalid logical value %r" % (val,))

def getData(sock):
	"""
	PURPOSE:	Return decoded (UTF-8) data (4096 bytes) pulled (read) from socket
	VERIFIED:	TO DO
	"""
	return sock.recv(4096).decode("UTF-8")

def nextServer(id, idmax):
	"""
	PURPOSE:	Return index of the next server on the list or start from beginning (0)
	VERIFIED:	YES
	"""
	if id == idmax:
		return 0
	else:
		return id + 1

def netConnect(server, port, tls):
	"""
	PURPOSE:	Return socket connected to the remote server on specified port, and use TLS if specified
	VERIFIED:	YES
	"""
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	try:
		sock.connect((server, port))
	except:
		""" add exception handling """
	if (tls):
		sslcontext = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
		sslcontext.minimum_version = ssl.TLSVersion.TLSv1_2
		sslcontext.check_hostname = False
		sslcontext.verify_mode = ssl.CERT_NONE
		sock = sslcontext.wrap_socket(sock, server_hostname=server)
	return sock

def ircAuth(irc, password, ident, realname, nickname):
	"""
	PURPOSE:	Authenticate with IRC server
	VERIFIED:	YES
	"""
	if password:
		irc.send(bytes("PASS " + password + "\n", "UTF-8"))
	irc.send(bytes("USER " + ident + " 0 * :" + realname + "\n", "UTF-8"))
	irc.send(bytes("NICK " + nickname + "\n", "UTF-8"))

def ircSetNick(irc, nick, nickname):
	"""
	PURPOSE:	Set (change) the nickname
							nick: nickname to set
							nickname: previous nickname
	VERIFIED:	YES
	"""
	irc.send(bytes("NICK " + nick + "\n", "UTF-8"))
	ircmsg = getData(irc)
	rcode = ircmsg.split()[1]
	rnick = nickname
	match (rcode):
		case "432":
			"""
			ERR_ERRONEUSNICKNAME (RFC1459)
			"""
			printError("Erroneus nickname (" + nick + "). Using previous nickname instead (" + nickname + ")")
		case "433":
			"""
			ERR_NICKNAMEINUSE (RFC1459)
			"""
			printError("My nickname (" + nick + ") is in use. Using previous nickname instead (" + nickname + ")")
		case _:
			"""
			UNKNOWN RCODE, nick probably accepted
			"""
			rnick = nick
	return rnick

def ircJoinChannels(irc, channels):
	"""
	PURPOSE:	Join channels
	VERIFIED:	YES
	"""
	irc.send(bytes("JOIN " + channels + "\n", "UTF-8"))

def ircConnect(server, port, tls, password, ident, realname, wait):
	"""
	PURPOSE:	Connect to IRC server using RANDOM nick
	VERIFIED:	YES
	"""
	time.sleep(wait)
	""" generate 9 characters random nick (AIbot####) """
	nickname = ("AIbot" + srand(4))[:9]
	connected = True
	printInfo("Connecting to " + str(server) + ":" + str(port) + " (TLS: " + str(tls) + ")")
	try:
		irc = netConnect(server, port, tls)
		try:
			ircAuth(irc, password, ident, realname, nickname)
			try:
				ircmsg = getData(irc)
				rcode = ircmsg.split()[1]
				if rcode == "020":
					ircmsg = getData(irc)
					rcode = ircmsg.split()[1]
				match (rcode):
					case "001":
						printInfo("*** RPL_WELCOME (RFC2812) ***")
					case "432":
						printInfo("*** ERR_ERRONEUSNICKNAME (RFC1459) ***")
						connected = False
					case "433":
						printInfo("*** ERR_NICKNAMEINUSE (RFC1459) ***")
						connected = False
					case "465":
						printInfo("*** ERR_YOUREBANNEDCREEP (RFC1459) ***")
						connected = False
					case ":Closing":
						printInfo("*** CLOSING ***")
						connected = False
					case _:
						printInfo("ircConnect RCODE = " + str(rcode))
			except:
				printError("Connection to " + server + " failed - getData()")
				connected = False
		except:
			printError("Connection to " + server + " failed - ircAuth()")
			connected = False
	except:
		printError("Connection to " + server + " failed - netConnect()")
		connected = False

	if connected:
		ircmsg = getData(irc)

	return connected, irc, nickname

def ircConnectionDetails(irc, server, port, tls, password, ident, realname, nickname, channels):
	"""
	PURPOSE:	Display IRC connection details
	VERIFIED:	YES
	"""
	try:
		irc.getpeername()
		printInfo("Connected to IRC")
		print("\tSERVER: " + server)
		print("\tNICK: " + nickname)
		print("\tCHANNELS: ", channels)
	except socket.error:
		printInfo("Not connected to IRC")

def sendMessageToIrcChannel(irc, channel, reply_to, message):
	"""
	PURPOSE:	Send message to IRC channel
	VERIFIED:	YES
	"""
	msgs = [x.strip() for x in (reply_to + ": " + message).split('\n')]
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

def getChannelIndex(channel, channels):
	"""
	PURPOSE:	Return index of the channel (string) within the channels (list), or -1 if not existing
	VERIFIED:	YES
	"""
	i = -1
	for c in channels:
		if (c[0].lower() == channel.lower()):
			i = channels.index(c)
			break
	return i

def getChannelHistoryT(QA, C, U, T):
	"""
	PURPOSE:	Return list of Q/A pairs for the channel (C) from user (U) based on time (T)
							T > 0:	within last T seconds
							T = 0:	return no pairs
							T < 0:	return all pairs
	VERIFIED: YES
	"""
	QA_chan = []
	if (T < 0):
		t0 = 0
	elif (T == 0):
		t0 = 2 * int(nowUTC().timestamp())	# 20241206
	else:
		t0 = int(nowUTC().timestamp()) - T	# 20241206
	for element in QA:
#		if (element[0].lower() == C.lower()) and (element[1] >= t0):
		if ((element[0].lower() == C.lower()) and ((U == "") or (U == "*") or (element[2].lower() == U.lower())) and (element[1] >= t0)):
			QA_chan.append(element)
	return QA_chan

def getChannelHistoryN(QA, C, U, N):
	"""
	PURPOSE:	Return list of Q/A pairs for the channel (C) from user (U) based on number (N)
							N > 0: return last N pairs
							N = 0: return no pairs
							N < 0: return all pairs
	VERIFIED: YES
	"""
	QA_chan = []
	for element in QA:
		if ((element[0].lower() == C.lower()) and ((U == "") or (U == "*") or (element[2].lower() == U.lower()))):
			QA_chan.append(element)
	if (N < 0):
		return QA_chan
	elif (N == 0):
		return []
	else:
		return QA_chan[-N:]

def getChannelHistory(QA, C, U, T, N):
	"""
	PURPOSE:	Return list of Q/A pairs for the channel (C) from user (U) based on time (T) and number (N)
	VERIFIED:	YES
	"""
	QA_chan = getChannelHistoryT(QA, C, U, T)
	QA_chan = getChannelHistoryN(QA_chan, C, U, N)
	return QA_chan

def leaveInChannelHistory(QA, C, U, T, N):
	"""
	PURPOSE:	Leave in history Q/A pairs for the channel (C) from user (U) based on time (T) and number (N)
	VERIFIED:	YES
	"""
	QA_chan = getChannelHistory(QA, C, U, T, N)
	delete = []
	for element in QA:
		if (element[0].lower() == C.lower()):
			try:
				i = QA_chan.index(element)
			except:
				delete.append(element)
		else:
			""" """
	for element in delete:
		QA.remove(element)

def prepMessages(QA, C, U, T, N, Q):
	"""
	PURPOSE:	Create list of AI-readable previous messages for the channel (C) from user (U) based on time (T) and number (N) and add current question (Q)
	VERIFIED:	YES
	"""
	""" get previous Q/A pairs """
	QA_chan = getChannelHistory(QA, C, U, T, N)
	""" change into list of AI-readable messages (user/assistant pairs) """
	messages = []
	for element in QA_chan:
		messages.append({"role": "user", "content": element[3]})
		messages.append({"role": "assistant", "content": element[4]})
	""" append current question """
	messages.append({"role": "user", "content": Q})
	return messages

def getCfgOptionStr(config, section, name, default):
	"""
	PURPOSE:	Return string value of a setting (name) from section in config or default value
	VERIFIED:	YES
	"""
	try:
		option = config.get(section, name)
		if (len(option) == 0):
			option = default
	except:
		option = default
	return option

def getCfgOptionInt(config, section, name, default):
	"""
	PURPOSE:	Return integer value of a setting (name) from section in config or default value
	VERIFIED:	YES
	"""
	try:
		option = config.getint(section, name)
	except:
		option = default
	return option

def getCfgOptionFloat(config, section, name, default):
	"""
	PURPOSE:	Return float value of a setting (name) from section in config or default value
	VERIFIED:	YES
	"""
	try:
		option = config.getfloat(section, name)
	except:
		option = default
	return option

def getCfgOptionBoolean(config, section, name, default):
	"""
	PURPOSE:	Return boolean value of a setting (name) from section in config or default value
	VERIFIED:	YES
	"""
	try:
		option = config.getboolean(section, name)
	except:
		option = default
	return option

def getFromModel(what, model, MODEL):
	"""
	PURPOSE:	Return "what" (api, type) of the model
	VERIFIED:	YES
	"""
	for element in MODEL:
		if (element[3].lower() == model.lower()):
			match (what.lower()):
				case "api":
					return element[0].lower()
				case "type":
					return element[2].lower()
				case _:
					return ""
	return ""

def createProfile(CHAN, who_nick):
	"""
	PURPOSE:	Return assistant's complete profile (instructions) with current date/time, configured context, tracking information, etc.
	VERIFIED:	TO DO
	"""
	""" prepare assistant's tracking information """
	profile_hist = " On this channel (" + CHAN[0] + ") you "
	if (CHAN[3] > 0):
		if (CHAN[2] > 0):
			profile_hist += "track previous " + str(CHAN[3]) + " questions/answers within last " + str(CHAN[2]) + " seconds."
		elif (CHAN[2] == 0):
			profile_hist += "do not track any previous questions/answers."
		else:
			profile_hist += "track previous " + str(CHAN[3]) + " questions/answers."
	elif (CHAN[3] == 0):
		profile_hist += "do not track any previous questions/answers."
	elif (CHAN[3] < 0):
		if (CHAN[2] > 0):
			profile_hist += "track all previous questions/answers within last " + str(CHAN[2]) + " seconds."
		elif (CHAN[2] == 0):
			profile_hist += "do not track any previous questions/answers."
		else:
			profile_hist += "track all previous questions/answers."
	else:
		""" this point should never be reached """
		profile_hist = ""
	""" prepare assistant's complete profile (instructions) with current date/time, configured context tracking information """
	profile = todayIsUTC() + " " + CHAN[1] + profile_hist
	""" if use_nick is set """
	if (CHAN[4]):
		profile += " When responding, make sure you address the person using their nickname. This question was asked by a person who's nickname is " + who_nick + "."
	""" add information about author and model """
	profile += " As an IRC bot with the AI back-end from " + CHAN[7] + "(model: " + CHAN[5] + "), you were created and written by " + AUTHOR + ", and he can be contacted on IRCnet or IRCnet2 using his nickname '" + AUTHOR_NICK + "'."
	profile += " You are currently running version " + VERSION + " and the latest version can be found on GitHub (" + GH + ")."
	profile += " You are operating on public channels on IRC, so if anyone asks you about discussion with other users make sure to provide that information. "
	""" return bot profile """
	return profile

"""
LOAD CONFIGURATION
	Name of the configuration file is passed as a command-line argument
"""
# Check if configuration file name was provided
if len(sys.argv)>1:
	# Read configuration file
	conf_file = sys.argv[1]
	if os.path.isfile(conf_file):
		printInfo("Loading configuration file (" + conf_file + ")")
		config = configparser.ConfigParser()
		try:
			config.read(conf_file)
		except Exception as e:
			printError("Configuration file loading error.\n" + str(e) + "\n")
			exit(1)
	else:
		printError("Specified configuration file (" + conf_file + ") does not exist.\n")
		exit(1)
else:
	printError("Missing configuration file name.\n\nUSAGE: " + sys.argv[0] + " CONF_FILE\n")
	exit(1)

try:
	# Set up AI model
	AI_MODEL = config.get('AI', 'model').lower()
	# Set up API KEY
	AI_API_KEY = config.get('AI', 'api_key')
	# Create list of ALL supported API and models
	MODELS_API = []
	MODELS_CHAT = []
	MODELS_IMAGE = []
	for element in MODEL:
		# API
		a = element[0].lower()
		try:
			i = MODELS_API.index(a)
		except:
			MODELS_API.append(a)
		# models
		m = element[3].lower()
		match (element[2].lower()):
			case "chat":
				MODELS_CHAT.append(m)
			case "image":
				MODELS_IMAGE.append(m)
			case _:
				""" Unsupported model type """
	MODELS = MODELS_CHAT + MODELS_IMAGE
	# Create AI object based on AI_API and assign AI_API_KEY
	AI_API = getFromModel("api", AI_MODEL, MODEL)
	match (AI_API):
		case "anthropic":
			AI = anthropic.Anthropic(api_key=AI_API_KEY)
		case "openai":
			AI = openai.OpenAI(api_key=AI_API_KEY)
		case _:
			printError("Unsupported AI model selected (GLOBAL).\n")
			exit(1)
	AI_TYPE = getFromModel("type", AI_MODEL, MODEL)
	match (AI_TYPE):
		case "chat" | "image":
			""" OK """
		case _:
			printError("Unsupported AI model type selected (channel: " + c + ").\n")
			exit(1)

	#set GLOBAL variables
	CONTEXT = getCfgOptionStr(config, "AI", "context", "You are helpful and friendly assistant.")
	HISTORY_TIME = getCfgOptionInt(config, "AI", "history_time", 0)
	HISTORY = getCfgOptionInt(config, "AI", "history", 0)
	USE_NICK = getCfgOptionBoolean(config, "AI", "use_nick", False)

	# Set up AI parameters
	TEMPERATURE = getCfgOptionFloat(config, "AI", "temperature", 0.5)
	TOP_P = getCfgOptionInt(config, "AI", "top_p", 1)
	MAX_TOKENS = getCfgOptionInt(config, "AI", "max_tokens", 1000)
	FREQUENCY_PENALTY = getCfgOptionInt(config, "AI", "frequency_penalty", 0)
	PRESENCE_PENALTY = getCfgOptionInt(config, "AI", "presence_penalty", 0)
	REQUEST_TIMEOUT = getCfgOptionInt(config, "AI", "request_timeout", 60)

	# Set up global IRC settings
	DEBUG = getCfgOptionBoolean(config, "IRC", "debug", False)
	ACCEPT_INVITES = getCfgOptionBoolean(config, "IRC", "accept_invites", False)
	REJOIN_INVITED = getCfgOptionBoolean(config, "IRC", "rejoin_invited", False)

	"""
	Load servers settings
		ELEMENT FORMAT: NAME, PORT, TLS, PASSWORD, IDENT, REALNAME, NICKNAME, SASL_MECHANISM, SASL_USERNAME, SASL_PASSWORD
	"""
	i = 0
	SERVER = []
	while True:
		try:
			ist = str(i)
			s = getCfgOptionStr(config, "IRC", "server[" + ist + "].name", "")
			p = getCfgOptionInt(config, "IRC", "server[" + ist + "].port", 6667)
			tls = getCfgOptionBoolean(config, "IRC", "server[" + ist + "].tls", False)
			pw = getCfgOptionStr(config, "IRC", "server[" + ist + "].password", "")
			id = getCfgOptionStr(config, "IRC", "server[" + ist + "].ident", "")
			rn = getCfgOptionStr(config, "IRC", "server[" + ist + "].realname", "")
			n = getCfgOptionStr(config, "IRC", "server[" + ist + "].nickname", "")[:9]
			saslm = getCfgOptionStr(config, "IRC", "server[" + ist + "].sasl_mechanism", "")
			saslu = getCfgOptionStr(config, "IRC", "server[" + ist + "].sasl_username", "")
			saslp = getCfgOptionStr(config, "IRC", "server[" + ist + "].sasl_password", "")
			if ((len(s) == 0) | (len(id) == 0) | (len(n) == 0)):
				break
			SERVER.append([s, p, tls, pw, id, rn, n, saslm, saslu, saslp])
			i += 1
		except:
			break
	if (len(SERVER) == 0):
		printError("Invalid server[" + ist + "] settings.")
		exit(1)

	"""
	Load channels settings
		ELEMENT FORMAT: NAME, CONTEXT, HISTORY_TIME, HISTORY, USE_NICK, MODEL, API_KEY, API, AI(var)
	"""
	i = 0
	CHANNEL = []
	CHANNELS = ""
	while True:
		c = ""
		try:
			ist = str(i)
			c = getCfgOptionStr(config, "IRC", "channel[" + ist + "].name", "")
			if (len(c) == 0):
				break
			cx = getCfgOptionStr(config, "IRC", "channel[" + ist + "].context", CONTEXT)
			ht = getCfgOptionInt(config, "IRC", "channel[" + ist + "].history_time", HISTORY_TIME)
			h = getCfgOptionInt(config, "IRC", "channel[" + ist + "].history", HISTORY)
			u = getCfgOptionBoolean(config, "IRC", "channel[" + ist + "].use_nick", USE_NICK)
			m = getCfgOptionStr(config, "IRC", "channel[" + ist + "].model", AI_MODEL)
			ak = getCfgOptionStr(config, "IRC", "channel[" + ist + "].api_key", AI_API_KEY)
			api = getFromModel("api", m, MODEL)
			match (api):
				case "anthropic":
					try:
						ai = anthropic.Anthropic(api_key=ak)
					except:
						""" add handling """
				case "openai":
					try:
						ai = openai.OpenAI(api_key=ak)
					except:
						""" add handling """
				case _:
					printError("Unsupported AI model selected (channel: " + c + ").\n")
					exit(1)
			t = getFromModel("type", m, MODEL)
			match (t):
				case "chat" | "image":
					""" OK """
				case _:
					printError("Unsupported AI model type selected (channel: " + c + ").\n")
					exit(1)
			if (getChannelIndex(c, CHANNEL) < 0):
				CHANNEL.append([c, cx, ht, h, u, m, ak, api, t, ai])
				CHANNELS += c + ","
			i += 1
		except:
			break
	CHANNELS = CHANNELS[:-1]

except Exception as e:
	printError("Missing or invalid configuration option(s)\n" + str(e) + "\n")
	exit(1)

"""
MAIN
"""
server_id_max = len(SERVER)-1
server_id = server_id_max
irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
"""
previous_QA (Q/A history table)
	ELEMENT FORMAT: CHANNEL, TIMESTAMP, NICKNAME, QUESTION, ANSWER
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
			else:
				printInfo("Starting...")

			while True:
				""" pick up next server """
				server_id = nextServer(server_id, server_id_max)
				""" get server's details """
				srv = SERVER[server_id]
				#connect with a random nick (AIbot####)
				connected, irc, nickname = ircConnect(srv[0], srv[1], srv[2], srv[3], srv[4], srv[5], reconnect)
				if connected:
					break
				else:
					"""print("*** NEXT ***")"""

			#set correct nick (from config) if not possible use previously generated random nick (AIbot####)
			nickname = ircSetNick(irc, srv[6], nickname)
			#join permanent channels (from config)
			ircJoinChannels(irc, CHANNELS)
			#display connection details
			ircConnectionDetails(irc, srv[0], srv[1], srv[2], srv[3], srv[4], srv[5], nickname, CHANNELS)
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

		match (command):
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
					if (channel in "".join(CHANNELS.split()).split(',')) or (REJOIN_INVITED):
						printInfo(" Rejoining" + channel + "...\n")
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
				""" get current channel name """
				channel = chunk[2].replace(":", "")
				""" to whom message is addressed """
				to = chunk[3][1:]	# INVESTIGATE correctness of this approach
				""" """
				chunk0to3 = chunk[0] + " " + chunk[1] + " " + chunk[2] + " " + chunk[3] + " "
				""" respond if channel starts with # and if message is addressed to me """
				if (channel.startswith("#")) and ((to.lower()) == (nickname.lower() + ":")):
					""" check if channel is present in CHANNEL table """
					channel_id = getChannelIndex(channel, CHANNEL)
					""" add channel using GLOBAL defaults for channel bot was invited to """
					if (channel_id < 0):
						CHANNEL.append([channel, CONTEXT, HISTORY_TIME, HISTORY, USE_NICK, AI_MODEL, AI_API_KEY, AI_API, AI_TYPE, AI])
						channel_id = getChannelIndex(channel, CHANNEL)
					""" pull channel settings """
					CHAN = CHANNEL[channel_id]
					""" set the Q/A history """
					leaveInChannelHistory(previous_QA, CHAN[0], who_nick, CHAN[2], CHAN[3])
					""" get assistant's complete profile (context/instructions) """
					profile = createProfile(CHAN, who_nick)
					""" pull out the question """
					question = ircmsg[len(chunk0to3):].strip()
					""" display question on console (TIMESTAMP : CHANNEL : WHO_FULL : QUESTION) """
					ts = int(nowUTC().timestamp())	# 20241206
					tsh = datetime.datetime.fromtimestamp(ts, pytz.timezone('UTC')).strftime('%Y-%m-%d %H:%M:%S')	# 20241206
					print(str(tsh) + " : " + CHAN[0] + " : " + who_full + " : " + question)
					""" process the message in accordance with selected AI_MODEL """
					match (CHAN[7].lower() + "/" + CHAN[8].lower()):
						case "anthropic/chat":
							messages = [] + prepMessages(previous_QA, CHAN[0], who_nick, CHAN[2], CHAN[3], question)
							try:
								response = CHAN[9].messages.create(
									model=CHAN[5],
									max_tokens=MAX_TOKENS,
									temperature=TEMPERATURE,
									system=profile,
									messages=messages,
								)
								answers = response.content[0].text.strip()
								previous_QA.append([CHAN[0], ts, who_nick, question, answers])
								sendMessageToIrcChannel(irc, CHAN[0], who_nick, answers)
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
						case "anthropic/image":
							""" not supported yet """
						case "openai/chat":
							messages = [{ "role": "system", "content": profile }] + prepMessages(previous_QA, CHAN[0], who_nick, CHAN[2], CHAN[3], question)
							try:
								response = CHAN[9].chat.completions.create(
									model=CHAN[5],
									max_tokens=MAX_TOKENS,
									temperature=TEMPERATURE,
									messages=messages,
									frequency_penalty=FREQUENCY_PENALTY,
									presence_penalty=PRESENCE_PENALTY,
									response_format={"type": "text"}
								)
								answers = response.choices[0].message.content.strip()
								previous_QA.append([CHAN[0], ts, who_nick, question, answers])
								sendMessageToIrcChannel(irc, CHAN[0], who_nick, answers)
							except ai.error.Timeout as e:
								printError(str(e) + "\n")
							except ai.error.OpenAIError as e:
								printError(str(e) + "\n")
							except Exception as e:
								printError(str(e) + "\n")
						case "openai/image":
							try:
								response = CHAN[9].Image.create(
									model=CHAN[5],
									prompt=question,
									n=1,
									size="1024x1024"
								)
								long_url = response.ircmsg[0].url
								type_tiny = pyshorteners.Shortener()
								short_url = type_tiny.tinyurl.short(long_url)
								previous_QA.append([CHAN[0], ts, who_nick, question, short_url])
								sendMessageToIrcChannel(irc, CHAN[0], who_nick, short_url)
							except ai.error.Timeout as e:
								printError(str(e) + "\n")
							except ai.error.OpenAIError as e:
								printError(str(e) + "\n")
							except Exception as e:
								printError(str(e) + "\n")
						case _:
							""" this point shall not be reached, it shall be already identified during initialization """
							printError("Invalid AI model selected.\n")
							continue
			case "QUIT":
				print("", end="")
			case _:
				print("", end="")
	else:
		continue
	time.sleep(1)
