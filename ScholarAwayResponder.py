import discord

#globals
from datetime import datetime
debugMode = False
client = discord.Client()
customReason = ""
ENABLE_DEBUG_MODE = "/sar enabledebugmode"
DISABLE_DEBUG_MODE = "/sar disabledebugmode"
#end of globals

def getToken():
    file = open('bottoken.txt', 'r')
    token = file.readline()
    file.close()
    return token

def isCurrentDayAWeekday():
    now = datetime.now()
    if now.weekday() >= 0 and now.weekday() < 5:
        return True
    return False

def isTimeDuringWorkHours():
    now = datetime.now()
    if now.hour > 8 and now.hour < 17:
        return True
    return False

def isTimeDuringSleepingHours():
    now = datetime.now()
    if now.hour <= 8 or now.hour > 20:
        return True
    return False

def getAwayReason(channel: discord.channel):
    if customReason:
        return customReason
    if isCurrentDayAWeekday() and isTimeDuringWorkHours():
        return 'Working'
    if isTimeDuringSleepingHours():
        return 'Sleeping'
    return ''

async def sendMessageIfDebugMode(message: str, channel: discord.TextChannel):
    if debugMode:
        await channel.send(message)
        print ('Sent message: {} to channel: {}.'.format(message, channel))
    return

async def handleDebugModeCommandIfFound(message: discord.Message):
    global debugMode
    content = message.content.lower()
    if content.startswith(ENABLE_DEBUG_MODE):
        debugMode = True
        await sendMessageIfDebugMode('Debug mode enabled', message.channel)
    if content.startswith(DISABLE_DEBUG_MODE):
        debugMode = False
        await sendMessageIfDebugMode('Debug mode disabled', message.channel)
    return


async def handleKillCommandIfFound(message: discord.Message):
    global debugMode
    content = message.content.lower()
    if content.startswith('/sar shutup'):
        await sendMessageIfDebugMode("Ok ok.  Shutting down.", message.channel)
        exit()
    return


async def handleCustomReasonCommandIfFound(message: discord.Message):
    global customReason
    content = message.content.lower()
    customReasonCommand = '/sar customreason='
    if content.startswith(customReasonCommand):
        customReason = content.replace(customReasonCommand, '')
        await sendMessageIfDebugMode('Custom reason set to: {}.'.format(customReason), message.channel)
    return

async def handleCommands(message: discord.Message):
    await handleKillCommandIfFound(message)
    await handleDebugModeCommandIfFound(message)
    await handleCustomReasonCommandIfFound(message)
    return


async def handleMessage(message: discord.Message):
    await sendMessageIfDebugMode('HandleMessage fired.', message.channel)
    await handleCommands(message)

    if '@Scholar' in message.clean_content:
        reason = getAwayReason(message.channel)
        if reason:
            responseMessage = 'Hi ' + message.author.display_name + " :slight_smile:.\n"
            responseMessage += 'Scholar is currently unavailable.\n'
            responseMessage += 'Reason: ' + reason + '.'
            await message.channel.send(responseMessage)

    await sendMessageIfDebugMode('HandleMessage completed.', message.channel)
    return

print('Booting up')

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    await handleMessage(message)

client.run(getToken())
