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
        commandHelp += "**{}** - This sets the days you work.  Use comma separated numbers from 0-6 (0-Monday, 1-Tuesday, 2-Wednesday, 3-Thursday, 4-Friday, 5-Saturday, 6-Sunday).\n".format(SetCommands.WORK_DAYS.value)
        commandHelp += "\t\tExample: `{} {} 0,1,2,3,4`   - This would set your work days as Monday-Friday\n".format(UserCommands.SET.value, SetCommands.WORK_DAYS.value)
        commandHelp += "**{}** - This sets your work hours.  Use comma separated numbers in military time. __**UTC Timezone - The API won't give me yours.**__\n".format(SetCommands.WORK_HOURS.value)
        commandHelp += "\t\tExample: `{} {} 8,17` - This would set your work hours from 8am-5pm (13,22 for CT Timezone)\n".format(UserCommands.SET.value, SetCommands.WORK_HOURS.value)
        commandHelp += "**{}** - This sets your sleep hours.  Use comma separated numbers in military time. __**UTC Timezone - The API won't give me yours.**__\n".format(SetCommands.SLEEP_HOURS.value)
        commandHelp += "\t\tExample: `{} {} 22,8` - This would set your sleep time from 10pm-8am  (3,13 for CT Timezone)\n".format(UserCommands.SET.value, SetCommands.SLEEP_HOURS.value)
        
        commandHelp += "__**Here's a full Example**__: `{} {} 0,1,2,3,4 {} 8,17 {} 22,8`\n".format(UserCommands.SET.value, SetCommands.WORK_DAYS.value, SetCommands.WORK_HOURS.value, SetCommands.SLEEP_HOURS.value)
        return commandHelp

class UserType(Enum):
    NORMAL_USER = 0
    ADMIN_USER = 1

class UserAutoResponse:
    name: str
    discriminator: str
    customReason: str
    workDays: [0,1,2,3,4]
    workHours: tuple
    sleepHours: tuple
    userType: UserType

    def __init__(self, name, discriminator):
        self.name = name
        self.discriminator = discriminator
        self.customReason = ''
        self.setWorkDays([])
        self.workHours = tuple()
        self.sleepHours = tuple()

        if name == 'Scholar' and discriminator == '1148':
            self.userType = UserType.ADMIN_USER
        else:
            self.userType = UserType.NORMAL_USER
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
    userAutoResponses = []
    scholarAutoResponse = UserAutoResponse('Scholar', '1148')
    scholarAutoResponse.setWorkDays([0,1,2,3,4])
    scholarAutoResponse.workHours = (13,22)
    scholarAutoResponse.sleepHours = (3,13)
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
            await message.channel.send('There are **{}** users configured.'.format(len(self.userAutoResponses)))
            for userAutoResponse in self.userAutoResponses:
                await message.channel.send('__User information__: \n{}'.format(userAutoResponse.toString()))
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
                await message.channel.send("Here's your status: \n{}".format(user.toString()))
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
        hoursRemovedHelp = "Perhaps this was on accident? Double check your syntax.  2 ints - 0-23 (Military time). 0=Midnight."
        user = self.findSingleUserByAuthor(message.author)
        commandsExecuted = ''
        if not user:
            user = UserAutoResponse(message.author.display_name, message.author.discriminator)
            commandsExecuted += "Created user auto response for user: {}\n".format(user.name)
            self.userAutoResponses.append(user)
        commandWithSetRemovedAndLowered = message.content.replace(UserCommands.SET.value, '').lower()
        commandsSplit = commandWithSetRemovedAndLowered.split('-')
        setCommandsAndValues = []
        for command in commandsSplit:
            setCommandAndValue = self.getSetCommandArgument(command)
            if len(setCommandAndValue):
                setCommandsAndValues.append(setCommandAndValue)
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
                if not len(workHours):
                    user.workHours = tuple()
                    commandsExecuted += "Removed `{}`. {}\n".format(setCommandAndValue[0].value, hoursRemovedHelp)
                else:
                    user.workHours = workHours
                    commandsExecuted += "Set `{}`.\n".format(setCommandAndValue[0].value)
            if SetCommands.SLEEP_HOURS == setCommandAndValue[0]:
                sleepHours = self.getBeforeAndAfterHoursFromCommandValue(setCommandAndValue[1])
                if not len(sleepHours):
                    user.sleepHours = tuple()
                    commandsExecuted += "Removed `{}`. {}\n".format(setCommandAndValue[0].value, hoursRemovedHelp)
                else:
                    user.sleepHours = sleepHours
                    commandsExecuted += "Set `{}`.\n".format(setCommandAndValue[0].value)
        commandsExecutedOutput = "Commands run for user: *{}*.\n{}".format(user.name, commandsExecuted)
        commandsExecutedOutput += "Here's your status: \n{}".format(user.toString())
        await message.channel.send(commandsExecutedOutput)

    def getSetCommandArgument(self, commandString: str):
        setCommandFound = False
        setCommand :SetCommands
        commandString = commandString.lower()
        for sC in SetCommands:
            if sC.value.replace('-','') in commandString:
                setCommand = sC
                setCommandFound = True
        if not setCommandFound:
            return tuple()
        commandValue = commandString.replace(setCommand.value.replace('-','') , '').replace(' ', '')
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
        commandMessageOutput += 'Because this was just a fun way to learn bots and python, there is no database.  Therefore, if the __***bot shuts down all settings with user information will be lost***__.\n\n'
        commandMessageOutput += '__**Commands available**:__\n'
        if user and user.userType == UserType.ADMIN_USER.value:
            commandMessageOutput += AdminCommands.toString()

        commandMessageOutput += UserCommands.toString()
        await message.channel.send(commandMessageOutput)

    async def handleUsersBeingTagged(self, message: discord.Message):
        for userAutoResponse in self.userAutoResponses:
            if userAutoResponse.getNameTag() in message.clean_content:
                if userAutoResponse.isUserAway():
                    responseMessage = 'Hi {} :slight_smile:.\n'.format(message.author.display_name)
                    responseMessage += '{} is currently unavailable.\n'.format(userAutoResponse.name)
                    responseMessage += 'Reason: {}'.format(userAutoResponse.getAwayReason())
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
