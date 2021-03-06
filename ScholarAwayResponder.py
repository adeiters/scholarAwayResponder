import discord
import boto3
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
from boto3.dynamodb.types import TypeDeserializer
from marshmallow_dataclass import dataclass as marshmallow_dataclass
import json

#globals
from datetime import datetime
from enum import Enum

class AdminCommands(Enum):
    LIST_USERS = '/sar list'
    RELOAD_USERS = '/sar reload'
    @staticmethod
    def toString():
        commandHelp = "Admin Commands:\n"
        commandHelp += "{} - lists all users and their information.\n".format(AdminCommands.LIST_USERS.value)
        return commandHelp


class UserCommands(Enum):
    SET = '/sar set'
    USER_STATUS = '/sar status'
    REMOVE_USER = '/sar delete'
    @staticmethod
    def toString():
        commandHelp = "User Commands:\n"
        commandHelp += "`{}` - returns your away status information\n".format(UserCommands.USER_STATUS.value)
        commandHelp += "`{}` - deletes your account\n".format(UserCommands.REMOVE_USER.value)
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
        commandHelp += "**{}** - This sets the days you work.  Use comma separated numbers from 0-6 (0-Monday, 1-Tuesday, 2-Wednesday, 3-Thursday, 4-Friday, 5-Saturday, 6-Sunday).\n".format(SetCommands.WORK_DAYS.value)
        commandHelp += "\t\tExample: `{} {} 0,1,2,3,4`   - This would set your work days as Monday-Friday.  Leave it blank to remove them.\n".format(UserCommands.SET.value, SetCommands.WORK_DAYS.value)
        commandHelp += "**{}** - This sets your work hours.  Use comma separated numbers in military time. __**UTC Timezone - The API won't give me yours.**__\n".format(SetCommands.WORK_HOURS.value)
        commandHelp += "\t\tExample: `{} {} 8,17` - This would set your work hours from 8am-5pm (13,22 for CT Timezone).  Leave it blank to remove them.\n".format(UserCommands.SET.value, SetCommands.WORK_HOURS.value)
        commandHelp += "**{}** - This sets your sleep hours.  Use comma separated numbers in military time. __**UTC Timezone - The API won't give me yours.**. Leave it blank to remove them.__\n".format(SetCommands.SLEEP_HOURS.value)
        commandHelp += "\t\tExample: `{} {} 22,8` - This would set your sleep time from 10pm-8am  (3,13 for CT Timezone)\n".format(UserCommands.SET.value, SetCommands.SLEEP_HOURS.value)
        
        commandHelp += "__**Here's a full Example**__: `{} {} 0,1,2,3,4 {} 8,17 {} 22,8`\n".format(UserCommands.SET.value, SetCommands.WORK_DAYS.value, SetCommands.WORK_HOURS.value, SetCommands.SLEEP_HOURS.value)
        commandHelp += "__**If you run this command, it would empty out everything**__: `{} {} {} {}`\n".format(UserCommands.SET.value, SetCommands.WORK_DAYS.value, SetCommands.WORK_HOURS.value, SetCommands.SLEEP_HOURS.value)
        return commandHelp

class UserType(Enum):
    NORMAL_USER = 0
    ADMIN_USER = 1

@marshmallow_dataclass
class User:
    userId: int
    name: str
    userType: int
    customReason: str
    workDays: list
    workHours: list
    sleepHours: list

    def __init__(self, userId, name, userType = 0, customReason='', workDays = [], workHours = [], sleepHours = []):
        self.userId = userId
        self.name = name
        self.userType = userType
        self.customReason = customReason
        self.setWorkDays([int(x) for x in workDays]) #dynamo db serializes these 3 as Decimal so need to convert to int
        self.workHours = [int(x) for x in workHours]
        self.sleepHours = [int(x) for x in sleepHours]
        return
    
    def getNameTag(self):
        return '@{}'.format(self.name)

    def isCurrentDayAWorkday(self):
        return datetime.utcnow().weekday() in self.workDays

    def isTimeDuringWorkHours(self):
        if not len(self.workHours):
            return False
        return self.isCurrentTimeWithinRange(self.workHours)

    def isTimeDuringSleepingHours(self):
        if not len(self.sleepHours):
            return False
        return self.isCurrentTimeWithinRange(self.sleepHours)

    def isCurrentTimeWithinRange(self, hours):
        now = datetime.utcnow()
        if hours[0] < hours[1]:
            #8am-5pm - hour >=8 and hour < 5
            return now.hour >= hours[0] and now.hour < hours[1] 
        #10pm-5am - hour >=10 or hour < 5    
        return now.hour >= hours[0] or now.hour < hours[1]

    def setWorkDays(self, workDays: list):
        workDays.sort()
        distinctDays = list(dict.fromkeys(workDays))
        self.workDays = distinctDays

    def setWorkHours(self, workHours: list):
        self.workHours = workHours

    def setSleepHours(self, sleepHours: list):
        self.sleepHours = sleepHours

    def isUserAway(self):
        return self.getAwayReason()

    def getAwayReason(self):
        if self.customReason:
            return self.customReason
        if self.isCurrentDayAWorkday() and self.isTimeDuringWorkHours():
            return '**Working**.  Work hours: {}'.format(Utilities.getHourTupleToDisplayStringInUTCAndCT(self.workHours))
        if self.isTimeDuringSleepingHours():
            return '**Sleeping**.  Sleep hours: {}'.format(Utilities.getHourTupleToDisplayStringInUTCAndCT(self.sleepHours))
        return ''
    
    def setCustomAwayReason(self, reason):
        self.customReason = reason

    def toString(self):
        output = 'Name: **{}**\n'.format(self.name)
        output += 'Custom away reason: **{}**\n'.format(self.customReason if self.customReason else 'Not Set')
        if self.workDays:
            weekdaysOutput = Utilities.getWeekDaysWithDaysOfTheWeek(self.workDays)
            output += 'Work days: **{}**\n'.format(weekdaysOutput)
        else:
            output += 'Work days: **{}**\n'.format('Not Set')
        if not len(self.workHours):
            output += 'Work hours: **Not Set**\n'
        else:
            output += 'Work hours: {}'.format(Utilities.getHourTupleToDisplayStringInUTCAndCT(self.workHours))
        if not len(self.sleepHours):
            output += 'Sleep hours: **Not Set**\n'
        else:
            output += 'Sleep hours: {}'.format(Utilities.getHourTupleToDisplayStringInUTCAndCT(self.sleepHours))
        return output

class Utilities:
    @staticmethod
    def getToken():
        file = open('bottoken.txt', 'r')
        token = file.readline()
        file.close()
        return token
    @staticmethod
    def isAnInt(string: str) -> bool:
        try: 
            int(string)
            return True
        except ValueError:
            return False
    @staticmethod
    def getListOfIntsFromCsv(string: str) -> list:
        stringSplit = string.split(',')
        listOfInts = []
        for string in stringSplit:
            string = string.replace(' ', '')
            if Utilities.isAnInt(string):
                listOfInts.append(int(string))
        return listOfInts
    @staticmethod
    def getValidWeekDaysFromCsv(string: str) -> list:
        listOfInts = Utilities.getListOfIntsFromCsv(string)
        listOfDays = []
        for i in listOfInts:
            if i >= 0 and i <=6:
                listOfDays.append(i)
        return listOfDays
    @staticmethod
    def getValidHoursFromCsv(string: str) -> list:
        listOfInts = Utilities.getListOfIntsFromCsv(string)
        listOfHours = []
        for i in listOfInts:
            if i >= 0 and i < 24:
                listOfHours.append(i)
        return listOfHours
    @staticmethod
    def convertUTCtoCT(hour: int) -> int:
        utcToCTOffset = 5 #todo: do we care about DST?
        #3am UTC becomes 10PM (22) CT - 3, 2, 1, 0, 23, 22
        if hour - utcToCTOffset < 0:
            remainder = hour - utcToCTOffset
            return 24 - abs(remainder)
        return hour - utcToCTOffset
    @staticmethod
    def convertMilitaryToStandard(hour: int) -> str: 
        if hour > 12:
            hour = hour - 12
            return str(hour) + " p.m."
        if hour == 0:
            return 'Midnight'
        if hour == 12:
            return 'Noon'
        return str(hour) + " a.m."
    @staticmethod
    def convertWeekdayFromIntToStringAbbreviation(weekday: int) -> str:
        if weekday == 0:
            return 'Mon'
        if weekday == 1:
            return 'Tues'
        if weekday == 2:
            return 'Wed'
        if weekday == 3:
            return 'Thurs'
        if weekday == 4:
            return 'Fri'
        if weekday == 5:
            return 'Sat'
        if weekday == 6:
            return 'Sun'
        return 'Invalid Input'
    @staticmethod
    def getHourTupleToDisplayStringInUTCAndCT(hours: tuple) -> str:
        fromHour = 0
        toHour = 1
        utcMilitary = "**{} to {}**".format(hours[fromHour], hours[toHour])
        standardTimeUTC = "**{}** to **{}**".format(Utilities.convertMilitaryToStandard(hours[fromHour]),Utilities.convertMilitaryToStandard(hours[toHour]))
        miliaryTimeCT = "{} to {}".format(Utilities.convertUTCtoCT(hours[fromHour]), Utilities.convertUTCtoCT(hours[toHour]))
        standardTimeCT = "**{}** to **{}**".format(Utilities.convertMilitaryToStandard(Utilities.convertUTCtoCT(hours[fromHour])), Utilities.convertMilitaryToStandard(Utilities.convertUTCtoCT(hours[toHour])))

        return '{} ({}) UTC.\t\tIn Central Time: {} ({}).\n'.format(utcMilitary, standardTimeUTC, miliaryTimeCT, standardTimeCT)
    @staticmethod
    def getWeekDaysWithDaysOfTheWeek(weekdays: list) -> str:
        weekDaysAbbreviated = []
        for i in weekdays:
            weekDaysAbbreviated.append(Utilities.convertWeekdayFromIntToStringAbbreviation(i))

        weekDaysAbbreviatedOutput = ''
        for i in weekDaysAbbreviated:
            weekDaysAbbreviatedOutput += '{}/'.format(i)
        weekDaysAbbreviatedOutput = weekDaysAbbreviatedOutput.rstrip('/')
        output = "**{} ({})**".format(weekdays, weekDaysAbbreviatedOutput)
        return output


class ChannelManager:
    users = []
    userRepository: any
    
    def __init__(self):
        self.userRepository = UserRepository()
        self.users = self.userRepository.getAll()

    def findSingleUserByAuthor(self, author):
        for user in self.users:
            if user.userId == author.id:
                return user

    async def handleAdminCommandsIfFound(self, message: discord.Message):
        content = message.content.lower()
        if content.startswith(AdminCommands.LIST_USERS.value):
            user = self.findSingleUserByAuthor(message.author)
            if not user or user.userType != UserType.ADMIN_USER.value:
                await message.channel.send('Nice try {}.'.format(message.author.display_name))
                return True
            await message.channel.send('There are **{}** users configured.'.format(len(self.users)))
            for user in self.users:
                await message.channel.send('__User information__: \n{}'.format(user.toString()))
            return True
        if content.startswith(AdminCommands.RELOAD_USERS.value):
            user = self.findSingleUserByAuthor(message.author)
            if not user or user.userType != UserType.ADMIN_USER.value:
                await message.channel.send('Nice try {}.'.format(message.author.display_name))
                return True
            self.users = self.userRepository.getAll()
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
                await message.author.send("Here's your status: \n{}".format(user.toString()))
                return True
            await message.author.send('User not found: \n{}'.format(message.author.display_name))
        if content.startswith(UserCommands.REMOVE_USER.value):
            if user:
                self.userRepository.delete(user)
                self.users.remove(user)
                await message.author.send('User removed: \n{}'.format(user.name))
                return True
            await message.author.send('User not found: \n{}'.format(message.author.display_name))  
            return True
        return

    async def handleSetCommand(self, message: discord.Message):
        hoursRemovedHelp = "Perhaps this was on accident? Double check your syntax.  2 ints - 0-23 (Military time). 0=Midnight."
        user = self.findSingleUserByAuthor(message.author)
        commandsExecuted = ''
        if not user:
            user = User(message.author.id, message.author.display_name)
            commandsExecuted += "Created user auto response for user: {}\n".format(user.name)
            self.users.append(user)
        setCommandsAndValues = self.getAllSetCommandsAndArgumentsFromMessage(message)
        if not len(setCommandsAndValues):
            commandsReminder = "I found no valid arguments for your `set` command.  Here's a reminder of the syntax.\n"
            commandsReminder += SetCommands.toString()
            commandsExecuted += commandsReminder
        for setCommandAndValue in setCommandsAndValues:
            if SetCommands.CUSTOM_REASON == setCommandAndValue[0]:
                user.customReason = setCommandAndValue[1]
                if user.customReason:
                    commandsExecuted += "Set `{}`.\n".format(setCommandAndValue[0].value)
                else:
                    commandsExecuted += "Removed `{}`.\n".format(setCommandAndValue[0].value)
            if SetCommands.WORK_DAYS == setCommandAndValue[0]:
                workDays = Utilities.getValidWeekDaysFromCsv(setCommandAndValue[1])
                user.setWorkDays(workDays)
                if user.workDays:
                    commandsExecuted += "Set `{}`.\n".format(setCommandAndValue[0].value)
                else:
                    commandsExecuted += "Removed `{}`.\n".format(setCommandAndValue[0].value)
            if SetCommands.WORK_HOURS == setCommandAndValue[0]:
                workHours = self.getBeforeAndAfterHoursFromCommandValue(setCommandAndValue[1])
                user.setWorkHours(workHours)
                if not len(workHours):
                    commandsExecuted += "Removed `{}`. {}\n".format(setCommandAndValue[0].value, hoursRemovedHelp)
                else:
                    commandsExecuted += "Set `{}`.\n".format(setCommandAndValue[0].value)
            if SetCommands.SLEEP_HOURS == setCommandAndValue[0]:
                sleepHours = self.getBeforeAndAfterHoursFromCommandValue(setCommandAndValue[1])
                user.setSleepHours(sleepHours)
                if not len(sleepHours):
                    commandsExecuted += "Removed `{}`. {}\n".format(setCommandAndValue[0].value, hoursRemovedHelp)
                else:
                    commandsExecuted += "Set `{}`.\n".format(setCommandAndValue[0].value)
        commandsExecutedOutput = "Commands run for user: *{}*.\n{}".format(user.name, commandsExecuted)
        commandsExecutedOutput += "Here's your status: \n{}".format(user.toString())
        await message.author.send(commandsExecutedOutput)
        self.userRepository.save(user)

    def getAllSetCommandsAndArgumentsFromMessage(self, message: discord.Message):
        commandWithSetRemoved = message.content.replace(UserCommands.SET.value, '')
        commandsSplit = commandWithSetRemoved.split('-')
        setCommandsAndValues = []
        for command in commandsSplit:
            setCommandAndValue = self.getSetCommandArgument(command)
            if len(setCommandAndValue):
                setCommandsAndValues.append(setCommandAndValue)
        return setCommandsAndValues

    def getSetCommandArgument(self, commandString: str):
        setCommandFound = False
        setCommand :SetCommands
        commandStringLowered = commandString.lower()
        for sC in SetCommands:
            if sC.value.replace('-','') in commandStringLowered:
                setCommand = sC
                setCommandFound = True
        if not setCommandFound:
            return tuple()
        commandValue = commandString.replace(setCommand.value.replace('-','') , '')
        if setCommand == SetCommands.CUSTOM_REASON:
            commandValue = commandValue.lstrip(' ').rstrip(' ')
        else:
            commandValue = commandValue.replace(' ', '')
        return (setCommand, commandValue)

    def getBeforeAndAfterHoursFromCommandValue(self, commandValue: str):
        listOfHours = Utilities.getValidHoursFromCsv(commandValue)
        if len(listOfHours) != 2:
            return []
        return listOfHours



    async def outputCommands(self, message: discord.Message):
        user = self.findSingleUserByAuthor(message.author)
        commandMessageOutput = 'The ***Scholar Away Responder*** bot is intended to automatically reply to you being tagged if you know you cannot be available during a time period.\n'
        commandMessageOutput += 'Most people are not available while asleep.  Some people need temporary absenses.  Others are very focused at work and unable to respond.\n'
        commandMessageOutput += 'This bot helps for any one of these you may need to set.\n'
        commandMessageOutput += '__**Commands available**:__\n'
        if user and user.userType == UserType.ADMIN_USER.value:
            commandMessageOutput += AdminCommands.toString()

        commandMessageOutput += UserCommands.toString()
        await message.author.send(commandMessageOutput)

    async def handleUsersBeingTagged(self, message: discord.Message):
        for user in self.users:
            if user.getNameTag() in message.clean_content:
                if user.isUserAway():
                    responseMessage = 'Hi {} :slight_smile:.\n'.format(message.author.display_name)
                    responseMessage += '{} is currently unavailable.\n'.format(user.name)
                    responseMessage += 'Reason: {}'.format(user.getAwayReason())
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


class UserRepository:
    serializer = TypeSerializer()
    deserializer = TypeDeserializer()
    usersTable: any

    def __init__(self):
        dynamodb = boto3.resource('dynamodb')
        self.usersTable = dynamodb.Table('Users')

    def getAll(self):
        users = []
        response = self.usersTable.scan()
        for item in response['Items']:
            dictionary = {k: self.deserializer.deserialize(v) for k, v in item.items() if k != 'userId'}
            dictionary["userId"] = int(item["userId"])
            if not 'customReason' in dictionary:
                dictionary['customReason'] = ''
            user = User.Schema().load(dictionary)
            users.append(user)
        return users

    def save(self, user: User):
        json = {k: self.serializer.serialize(v) for k, v in User.Schema().dump(user).items() if v != ""}
        json['userId'] = user.userId
        self.usersTable.put_item(Item= json)
        return

    def delete(self, user: User):
        self.usersTable.delete_item(Key = {'userId': user.userId})

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
