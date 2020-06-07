import discord

#globals
from datetime import datetime
from enum import Enum

class AdminCommands(Enum):
    LIST_USERS = '/sar list'
    @staticmethod
    def toString():
        commandHelp = "Admin Commands:\n"
        commandHelp += "{} - lists all users and their information.\n".format(AdminCommands.LIST_USERS.value)
        return commandHelp


class UserCommands(Enum):
    SET = '/sar set'
    USER_STATUS = '/sar status'
    REMOVE_USER = '/sar reset'
    @staticmethod
    def toString():
        commandHelp = "User Commands:\n"
        commandHelp += "`{}` - returns your away status information\n".format(UserCommands.USER_STATUS.value)
        commandHelp += "`{}` - removes your information\n".format(UserCommands.REMOVE_USER.value)
        commandHelp += "`{}` - starts setting user away response information\n".format(UserCommands.SET.value)
        commandHelp += "{}\n".format(SetCommands.toString())
        return commandHelp
    
class SetCommands(Enum):
    WORK_DAYS = '-workdays'
    WORK_HOURS = '-workhours'
    SLEEP_HOURS = '-sleephours'
    CUSTOM_REASON = '-customreason'
    @staticmethod
    def toString():
        commandHelp = "Set Arguments (you can chain these):\n"
        commandHelp += "**{}** - Sets a custom reason.  This bypasses work and sleep hours and simply tells people why you are away.\n".format(SetCommands.CUSTOM_REASON.value)
        commandHelp += "\t\tExample: `{} {} I'll be in the hospital`\n".format(UserCommands.SET.value, SetCommands.CUSTOM_REASON.value)
        commandHelp += "**{}** - This sets the days you work.  Use comma separated numbers from 0-6 (0-Monday, 1-Tuesday, 2-Wednesday, 3-Thursday, 4-Friday, 5-Saturday, 6-Sunday)\n".format(SetCommands.WORK_DAYS.value)
        commandHelp += "\t\tExample: `{} {} 0,1,2,3,4`   - This would set your work days as Monday-Friday\n".format(UserCommands.SET.value, SetCommands.WORK_DAYS.value)
        commandHelp += "**{}** - This sets your work hours.  Use comma separated numbers in military time\n".format(SetCommands.WORK_HOURS.value)
        commandHelp += "\t\tExample: `{} {} 8,17` - This would set your work hours from 8am-5pm\n".format(UserCommands.SET.value, SetCommands.WORK_HOURS.value)
        commandHelp += "**{}** - This sets your work hours.  Use comma separated numbers in military time\n".format(SetCommands.SLEEP_HOURS.value)
        commandHelp += "\t\tExample: `{} {} 22,8` - This would set your sleep time from 10pm-8am\n".format(UserCommands.SET.value, SetCommands.SLEEP_HOURS.value)
        
        commandHelp += "__**Here's a full Example**__: `{} {} 0,1,2,3,4 {} 8,17 {} 22,8`\n".format(UserCommands.SET.value, SetCommands.WORK_DAYS.value, SetCommands.WORK_HOURS.value, SetCommands.SLEEP_HOURS.value)
        return commandHelp

class UserType(Enum):
    NORMAL_USER = 0
    ADMIN_USER = 1

class UserAutoResponse:
    name: str
    discriminator: str
    userType: UserType
    customReason = ''
    sleepStartHour: int
    sleepEndHour: int
    workDays: [0,1,2,3,4]
    workStartHour: int
    workEndHour: int

    def __init__(self, name, discriminator):
        self.name = name
        self.discriminator = discriminator

        if name == 'Scholar' and discriminator == '1148':
            self.userType = UserType.ADMIN_USER
        else:
            self.userType = UserType.NORMAL_USER
        return
    
    def getNameTag(self):
        return '@{}'.format(self.name)

    def isCurrentDayAWeekday(self):
        now = datetime.now()
        return now.weekday() in self.workDays

    def isTimeDuringWorkHours(self):
        now = datetime.now()
        return now.hour >= self.workStartHour and now.hour <= self.workEndHour

    def isTimeDuringSleepingHours(self):
        now = datetime.now()
        return now.hour <= self.sleepEndHour or now.hour >= self.sleepStartHour

    def getAwayReason(self):
        if self.customReason:
            return self.customReason
        if self.isCurrentDayAWeekday() and self.isTimeDuringWorkHours():
            return 'Working'
        if self.isTimeDuringSleepingHours():
            return 'Sleeping'
        return ''
    
    def setCustomAwayReason(self, reason):
        self.customReason = reason

    def toString(self):
        output = 'Name: {}\n'.format(self.name)
        output += 'Custom away reason: {}\n'.format(self.customReason if self.customReason else 'None')
        output += 'Work hours: {} to {}\n'.format(self.workStartHour, self.workEndHour)
        output += 'Sleep hours: {} to {}'.format(self.sleepEndHour, self.sleepStartHour)
        return output

class Utilities:
    @staticmethod
    def getToken():
        file = open('bottoken.txt', 'r')
        token = file.readline()
        file.close()
        return token

class ChannelManager:
    userAutoResponses = []
    scholarAutoResponse = UserAutoResponse('Scholar', '1148')
    scholarAutoResponse.sleepStartHour = 11
    scholarAutoResponse.sleepEndHour = 8
    scholarAutoResponse.workDays = [0,1,2,3,4]
    scholarAutoResponse.workStartHour = 8
    scholarAutoResponse.workEndHour = 17
    userAutoResponses.append(scholarAutoResponse)

    def findSingleUserByAuthor(self, author):
        for userAutoResponse in self.userAutoResponses:
            if userAutoResponse.name in author.display_name and userAutoResponse.discriminator == author.discriminator:
                return userAutoResponse

    async def handleAdminCommandsIfFound(self, message: discord.Message):
        content = message.content.lower()
        if content.startswith(AdminCommands.LIST_USERS.value):
            user = self.findSingleUserByAuthor(message.author)
            if not user or user.userType != UserType.ADMIN_USER:
                await message.channel.send('Nice try {}.'.format(message.author.display_name))
                return True
            await message.channel.send('There are {} users configured.'.format(self.userAutoResponses.count))
            for userAutoResponse in self.userAutoResponses:
                await message.channel.send('User information: \n{}'.format(userAutoResponse.toString()))
            return True
        return

    async def handleUserCommands(self, message: discord.Message):
        content = message.content.lower()
        user = self.findSingleUserByAuthor(message.author)
        if content.startswith(UserCommands.SET.value):
            await self.handleSetCommand(message)
            return True
        if content.startswith(UserCommands.USER_STATUS.value):
            if user:
                await message.channel.send('User status: \n{}'.format(user.toString()))
                return True
            await message.channel.send('User not found: \n{}'.format(message.author.display_name))
        if content.startswith(UserCommands.REMOVE_USER.value):
            if user:
                self.userAutoResponses.remove(user)
                await message.channel.send('User removed: \n{}'.format(user.name))
                return True
            await message.channel.send('User not found: \n{}'.format(message.author.display_name))  
            return True
        return

    async def handleSetCommand(self, message: discord.Message):
        user = self.findSingleUserByAuthor(message.author)
        commandsExecuted = ''
        if not user:
            user = UserAutoResponse(message.author.display_name, message.author.discriminator)
            commandsExecuted += "Created user auto response for user: {}\n".format(user.name)
            self.userAutoResponses.append(user)
        commandWithSetRemovedAndLowered = message.content.replace(UserCommands.SET.value, '').lower()
        commandsSplit = commandWithSetRemovedAndLowered.split('-')
        for command in commandsSplit:
            setCommandAndValue = self.getSetCommandArgument(command)
            if SetCommands.CUSTOM_REASON == setCommandAndValue[0]:
                user.customReason = setCommandAndValue[1]
                commandsExecuted += "Set `{}` to **{}**.\n".format(setCommandAndValue[0].value, setCommandAndValue[1])
        await message.channel.send("Commands run for user: *{}*.\n{}".format(user.name, commandsExecuted))

    def getSetCommandArgument(self, commandString: str):
        setCommandFound = False
        setCommand :SetCommands
        commandString = commandString.lower()
        for sC in SetCommands:
            if sC.value.replace('-','') in commandString:
                setCommand = sC
                setCommandFound = True
        if not setCommandFound:
            return (None, None)
        commandValue = commandString.replace(setCommand.value.replace('-','') , '').replace(' ', '')
        return (setCommand, commandValue)




    async def outputCommands(self, message: discord.Message):
        user = self.findSingleUserByAuthor(message.author)
        commandMessageOutput = 'The ***Scholar Away Responder*** bot is intended to automatically reply to you being tagged if you know you cannot be available during a time period.\n'
        commandMessageOutput += 'Most people are not available while asleep.  Some people need temporary absenses.  Others are very focused at work and unable to respond.\n'
        commandMessageOutput += 'This bot helps for any one of these you may need to set.\n'
        commandMessageOutput += 'Because this was just a fun way to learn bots and python, there is no database.  Therefore, if the __***bot shuts down all settings with user information will be lost***__.\n\n'
        commandMessageOutput += '__**Commands available**:__\n'
        if user and user.userType == UserType.ADMIN_USER.value:
            commandMessageOutput += AdminCommands.toString()

        commandMessageOutput += UserCommands.toString()
        await message.channel.send(commandMessageOutput)

    async def handleUsersBeingTagged(self, message: discord.Message):
        for userAutoResponse in self.userAutoResponses:
            if userAutoResponse.getNameTag() in message.clean_content:
                reason = userAutoResponse.getAwayReason()
                if reason:                    
                    responseMessage = 'Hi {} :slight_smile:.\n'.format(message.author.display_name)
                    responseMessage += '{} is currently unavailable.\n'.format(userAutoResponse.name)
                    responseMessage += 'Reason: **{}**.'.format(reason)
                    await message.channel.send(responseMessage)

    async def handleMessage(self, message: discord.Message):
        if await self.handleAdminCommandsIfFound(message):
            None
        elif await self.handleUserCommands(message):
            None
        elif message.content.startswith('/sar'):
            await self.outputCommands(message)            
        elif await self.handleUsersBeingTagged(message):
            None





print('Booting up')

client = discord.Client()
channelManager = ChannelManager()



@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    await channelManager.handleMessage(message)

client.run(Utilities.getToken())
