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
        commandHelp += "{} - starts setting user away response information\n".format(UserCommands.SET.value)
        commandHelp += "{} - returns your away status information\n".format(UserCommands.USER_STATUS.value)
        commandHelp += "{} - removes your information\n".format(UserCommands.REMOVE_USER.value)
        return commandHelp

class UserType(Enum):
    NORMAL_USER = 0
    ADMIN_USER = 1

class UserAutoResponse:
    nametag: str
    discriminator: str
    userType: UserType
    customReason = ''
    sleepStartHour: int
    sleepEndHour: int
    workDays: [0,1,2,3,4]
    workStartHour: int
    workEndHour: int

    def __init__(self, nametag, discriminator):
        self.nametag = nametag
        self.discriminator = discriminator

        if nametag == '@Scholar' and discriminator == '1148':
            self.userType = UserType.ADMIN_USER
        else:
            self.userType = UserType.NORMAL_USER
        return
    
    def getName(self):
        return self.nametag.replace('@', '')

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
        output = 'Name: {}\n'.format(self.getName())
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
    scholarAutoResponse = UserAutoResponse('@Scholar', '1148')
    scholarAutoResponse.sleepStartHour = 11
    scholarAutoResponse.sleepEndHour = 8
    scholarAutoResponse.workDays = [0,1,2,3,4]
    scholarAutoResponse.workStartHour = 8
    scholarAutoResponse.workEndHour = 17
    userAutoResponses.append(scholarAutoResponse)

    def findSingleUserByAuthor(self, author):
        for userAutoResponse in self.userAutoResponses:
            if userAutoResponse.getName() in author.display_name and userAutoResponse.discriminator == author.discriminator:
                return userAutoResponse

    async def handleAdminCommandsIfFound(self, message: discord.Message):
        content = message.content.lower()
        if content.startswith(AdminCommands.LIST_USERS.value):
            user = self.findSingleUserByAuthor(message.author)
            if not user or user.userType != UserType.ADMIN_USER:
                await message.channel.send('Nice try {}.'.format(message.author.display_name))
                return True
            for userAutoResponse in self.userAutoResponses:
                await message.channel.send('User information: \n{}'.format(userAutoResponse.toString()))
            return True
        return

    async def handleUserCommands(self, message: discord.Message):
        content = message.content.lower()
        if content.startswith(UserCommands.USER_STATUS.value):
            user = self.findSingleUserByAuthor(message.author)
            if user:
                await message.channel.send('User status: \n{}'.format(user.toString()))
                return True
            await message.channel.send('User not found: \n{}'.format(message.author.display_name))
        if content.startswith(UserCommands.REMOVE_USER.value):
            user = self.findSingleUserByAuthor(message.author)
            if user:
                self.userAutoResponses.remove(user)
                await message.channel.send('User removed: \n{}'.format(user.getName()))
                return True
            await message.channel.send('User not found: \n{}'.format(message.author.display_name))  
            return True
        return

    async def outputCommands(self, message: discord.Message):
        user = self.findSingleUserByAuthor(message.author)
        commandMessageOutput = 'Commands available:\n'
        if user.userType == UserType.ADMIN_USER:
            commandMessageOutput += AdminCommands.toString()

        commandMessageOutput += UserCommands.toString()
        await message.channel.send(commandMessageOutput)

    async def handleUsersBeingTagged(self, message: discord.Message):
        for userAutoResponse in self.userAutoResponses:
            if userAutoResponse.nametag in message.clean_content:
                reason = userAutoResponse.getAwayReason()
                if reason:                    
                    responseMessage = 'Hi {} :slight_smile:.\n'.format(message.author.display_name)
                    responseMessage += '{} is currently unavailable.\n'.format(userAutoResponse.getName())
                    responseMessage += 'Reason: {}.'.format(reason)
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
