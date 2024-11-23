<div align="center">
<!-- Title: -->
  <h1><a href="https://github.com/oiramNet/AI-IRC-Bot/">AI IRC Bot</h1>
<!-- Labels: -->
  <!-- First row: -->
    <img src="https://img.shields.io/github/repo-size/oiramNet/AI-IRC-Bot?label=Repo%20size&style=flat-square" height="20">
    <img src="https://img.shields.io/github/downloads/oiramNet/AI-IRC-Bot/total?label=Downloads&style=flat-square" height="20">
    <img src="https://img.shields.io/github/license/oiramNet/AI-IRC-Bot?label=License&style=flat-square" height="20">
		<br>
  <!-- Second row: -->
    <img src="https://img.shields.io/github/issues/oiramNet/AI-IRC-Bot/enhancement?label=Enhancements&style=flat-square" height="20">
    <img src="https://img.shields.io/github/issues/oiramNet/AI-IRC-Bot/bug?label=Bugs&style=flat-square" height="20">
    <img src="https://img.shields.io/github/discussions/oiramNet/AI-IRC-Bot?label=Discussions&style=flat-square" height="20">
<!-- Short description: -->
</div>


__AI IRC Bot__ is a simple IRC bot written in Python. It was initially forked from the [knrd1/chatgpt](https://github.com/knrd1/chatgpt) into [oiramNet/ChatGPT-IRC-Bot](https://github.com/oiramNet/ChatGPT-IRC-Bot) but turned into its own project to support other __AI__ back-ends. It connects to the selected __AI__ endpoints to answer questions or generate images and uses official bindings from __AI__ to interact with it using the __API__ through the HTTP/HTTPS requests. You can find more details about supported __APIs__ below:

* ChatGPT (OpenAI): https://platform.openai.com/docs/api-reference
* Claude (Anthropic): https://docs.anthropic.com/en/api/getting-started

## Prerequisites
1. Create an account and obtain your __API KEY__
   * ChatGPT (OpenAI): https://platform.openai.com/account/api-keys
   * Claude (Anthropic): https://console.anthropic.com/settings/keys
2. Install Python3 and the official bindings (__pyshorteners__; __pytz__; __openai__; __anthropic__)
   * Debian/Ubuntu
     ```
     apt install python3 python3-pip
     pip3 install pyshorteners pytz openai anthropic
     ```
   * RedHat/CentOS
     ```
     yum install python3 python3-pip
     pip3 install pyshorteners pytz openai anthropic
     ```
   * FreeBSD
     ```
     pkg install python311 py311-pip
     pip install pyshorteners pytz openai anthropic
     ```

## Installation
Clone the package using the below command. It will copy all files into the __AI-IRC-Bot__ directory, which you can later rename.
```
git clone https://github.com/oiramNet/AI-IRC-Bot
```

## Configuration
__AI IRC Bot__ uses a plain-text file as its configuration file. The package includes an example configuration file (__AIbot.conf.sample__) which is set to connect to __IRCnet__. You can copy and modify it to suit your preferences.
```
cd AI-IRC-Bot
cp AIbot.conf.sample SampleBot.conf
```
> Some of the settings apply only to the specific __AI API__ or models. Make sure to check the sample configuration file for details.

### Supported models
__AI IRC Bot__ can use any of the below models.
* ChatGPT (OpenAI): https://platform.openai.com/docs/models
  * Chat Completion models
    > gpt-4o, __gpt-4o-mini__, gpt-4, gpt-4-turbo, gpt-4-turbo-preview, gpt-3.5-turbo
  * Image creation models
    > dall-e-2, dall-e-3
* Claude (Anthropic): https://docs.anthropic.com/en/docs/about-claude/models
  * Chat Completion models
    > claude-3-5-sonnet-latest, __claude-3-5-haiku-latest__

We suggest starting experimenting with __gpt-4o-mini__ for the ChatGPT (OpenAI) or __claude-3-5-haiku-latest__ for Claude (Anthropic).

## Running bot
To start the bot, run the command below. Make sure to replace __CONFIG__ with the name of your configuration file.
* Debian/Ubuntu/RedHat/CentOS
  ```
  python3 AIbot.py CONFIG
  ```
* FreeBSD
  ```
  python3.11 AIbot.py CONFIG
  ```

## Interaction
__AI IRC Bot__ is designed to process messages on standard channels (__#CHANNEL__) and will interact (respond) only to messages directed to it using its nickname (__BOTNAME: MESSAGE__).
```console
12:34:12 < user> SampleBot: how are you?
12:34:13 < SampleBot> I'm doing well, thank you for asking! How are you today? Is there anything specific I can help you with?
12:56:21 < user> SampleBot: do you like IRC?
12:56:22 < SampleBot> I'm an AI, so I don't personally "like" or "dislike" things in the way humans do. However, I'm familiar with IRC (Internet Relay Chat) as a communication protocol. It's an older form of real-time internet chat that was very popular before modern messaging platforms. Would you like to discuss IRC or chat protocols?
```

If you set the model to __dall-e-2__ or __dall-e-3__ (ChatGPT/Image creation), the __AI IRC Bot__ will return a shortened URL to the generated image.
```console
13:14:05 < user> SampleBot: red apples on the table
13:14:35 < SampleBot> https://tinyurl.com/1a2b3c4d
```

## Bugs, Enhancments, etc.
Feel free to contact us through the __GitHub__.
