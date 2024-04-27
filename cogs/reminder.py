import re
import json
import asyncio
import discord
import datetime
import traceback
import contextlib
from typing import List, Optional
from discord import app_commands
from discord.ext import commands, tasks

import public_config as config


class Reminder():
    def __init__(self, author=None, date="", message="", users=None, roles=None, reminder_again=0, reminder_again_in="", is_private=False, r=None, channel=None):
        if users is None:
            users = []
        if roles is None:
            roles = []

        if channel != None:
            self.channel = channel

        if not r:
            self.author = author
            self.date = date
            self.message = message
            self.users = users
            self.roles = roles
            if len(users) == len(roles) == 0:
                self.users = [author]
            self.reminder_again = reminder_again
            self.reminder_again_in = reminder_again_in
            self.private = is_private
        else:
            self.__dict__ = json.loads(r)


class DeleteReminder(discord.ui.View):

    def __init__(self, reminders: List[Reminder]):
        super().__init__(timeout=60.0)
        self.reminders = reminders
        self.options = [
            discord.SelectOption(
                label=f"{reminder.message} - {reminder.date}",
                value=str(i)
            ) for i, reminder in enumerate(reminders)]

        self.select = discord.ui.Select(
            options=self.options,
            min_values=1,
            max_values=min(len(self.options), 25),
            placeholder="Wähle die Erinnerung aus, die du löschen möchtest."
        )
        self.select.callback = self.callback
        self.add_item(self.select)

    async def callback(self, interaction: discord.Interaction) -> None:
        self.select.disabled = True
        plural = "en" if len(self.select.values) > 1 else ""
        e = discord.Embed(
            title=f"Die Erinnerung{plural} wurde erfolgreich gelöscht.",
            description="\n".join(
                [f"{self.reminders[int(value)].message} - {self.reminders[int(value)].date}" for value in self.select.values]),
            color=discord.Color.green()
        )
        e.timestamp = datetime.datetime.now()
        e.set_footer(text=interaction.user.name,
                     icon_url=interaction.user.avatar)
        for value in self.select.values:
            remove_new_reminder(interaction.user.id,
                                self.reminders[int(value)])
        await interaction.response.send_message(embed=e, ephemeral=True)
        self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        await interaction.response.send_message('Oops! Something went wrong. ' + str(error), ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_exception(type(error), error, error.__traceback__)


class Reminders(commands.Cog, name="Erinnerungen"):
    """Commands zum Bedienen der Erinnerungs-funktion"""

    def __init__(self, bot):
        self.bot = bot
        self.checkReminder.start()

    @app_commands.command(name="reminder", description="Erstellt einen Reminder")
    @app_commands.describe(
        zeit="Zeitangabe für die Erinnerung, entweder nach Schema dd.mm.yyyy hh:mm oder in relativer Zeitangabe wie 1d 2h 3min",
        nachricht="Erinnerungsnachricht",
        zugriff="Sichtbarkeit der Erinnerung",
        user="Nutzer, der anstatt dir erwähnt werden soll"
    )
    @app_commands.choices(
        zugriff=[
            app_commands.Choice(name="privat", value="private"),
            app_commands.Choice(name="öffentlich", value="public"),
        ]
    )
    async def newreminder(self, interaction: discord.Interaction, zeit: str, nachricht: str, zugriff: Optional[app_commands.Choice[str]], user: Optional[discord.User] = None):
        # Reminder is public by default
        is_private = False if not zugriff else zugriff.value == "private"

        relative_match = re.match(
            r'^((?P<days>\d+?)d)?\s*((?P<hours>\d+?)h)?\s*((?P<minutes>\d+?)min)?$', zeit)
        absolute_match = re.match(
            r'^((?P<day>\d{1,2})(\.(?P<month>\d{1,2}))(\.(?P<year>\d\d(\d\d)?))?)?\s*(?P<time>(?P<hour>\d\d):(?P<minute>\d\d))?$', zeit)

        if not relative_match and not absolute_match:
            e = discord.Embed(title=f"Aktion unzulässig",
                              description="Das angegebene Datum ist nicht zulässig.", color=discord.Color.red())
            e.timestamp = datetime.datetime.now()
            e.set_footer(text=interaction.user.name,
                         icon_url=interaction.user.avatar)
            await interaction.response.send_message(embed=e, ephemeral=True)
            return

        if relative_match:
            time = datetime.datetime.now() + self.parse_to_timedelta(zeit)

        if absolute_match:
            time = datetime.datetime.now()

            if absolute_match.group("day"):
                time = time.replace(day=int(absolute_match.group("day")))
            if absolute_match.group("month"):
                time = time.replace(month=int(absolute_match.group("month")))
            if absolute_match.group("year"):
                year = absolute_match.group("year")
                if len(year) == 2:
                    year = int(year) + 2000
                time = time.replace(year=year)

            if absolute_match.group("time"):
                time = time.replace(hour=int(absolute_match.group(
                    "hour")), minute=int(absolute_match.group("minute")))
                if time < datetime.datetime.now():
                    # add one day
                    time += datetime.timedelta(days=1)
            else:
                time = time.replace(hour=0, minute=0)

            if time < datetime.datetime.now() and not absolute_match.group("year"):
                # add one year
                time = time.replace(year=time.year + 1)

        if time < datetime.datetime.now():
            e = discord.Embed(
                title=f"Aktion unzulässig",
                description=f"Erinnerungen in der Vergangenheit sind nicht erlaubt, {time.strftime('%d.%m.%Y %H:%M')} < {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}",
                color=discord.Color.red()
            )
            e.timestamp = datetime.datetime.now()
            e.set_footer(text=interaction.user.name,
                         icon_url=interaction.user.avatar)
            await interaction.response.send_message(embed=e, ephemeral=True)
            return

        # convert time to readable string
        time = time.strftime('%d.%m.%Y %H:%M')
        # if reminder is for other person, check if it is public
        other = ""
        if user:
            if is_private:
                e = discord.Embed(
                    title=f"Aktion unzulässig", description="Erinnerungen für andere Nutzer müssen öffentlich sein.", color=discord.Color.red())
                e.timestamp = datetime.datetime.now()
                e.set_footer(text=interaction.user.name,
                             icon_url=interaction.user.avatar)
                await interaction.response.send_message(embed=e, ephemeral=True)
                return

            other = f"{user.name}, "
            user = user.id
        else:
            user = interaction.user.id

        r = Reminder(interaction.user.id, time, nachricht, [
                     user], [], is_private=is_private, channel=interaction.channel_id)

        e = discord.Embed(
            title=f"Die Erinnerung für {other}{time} wurde erfolgreich gespeichert.", description=nachricht, color=discord.Color.green())
        e.timestamp = datetime.datetime.now()
        e.set_footer(text=interaction.user.name,
                     icon_url=interaction.user.avatar)

        add_new_reminder(r)
        await interaction.response.send_message(embed=e, ephemeral=is_private)

    @app_commands.command(name="removereminder", description="Löscht Reminder")
    async def removereminder(self, interaction: discord.Interaction):
        r = get_reminder()
        reminders = []
        for reminder in r[str(interaction.user.id)]:
            rem = Reminder(r=reminder)
            reminders.append(rem)
        if len(reminders) == 0:
            e = discord.Embed(
                title=f"Du hast keine Erinnerungen gespeichert.", color=discord.Color.red())
            e.timestamp = datetime.datetime.now()
            e.set_footer(text=interaction.user.name,
                         icon_url=interaction.user.avatar)
            await interaction.response.send_message(embed=e, ephemeral=True)
            return
        await interaction.response.send_message(view=DeleteReminder(reminders), ephemeral=True)

    @tasks.loop(seconds=60)
    async def checkReminder(self):
        r = get_reminder()
        now = datetime.datetime.now()
        recipients = list(r.keys())
        for recipient_id in recipients:
            for reminder in r[recipient_id]:
                rem: Reminder = Reminder(r=reminder)
                # not all reminders have this
                with contextlib.suppress(BaseException):
                    if rem.private:
                        channel = self.bot.get_user(rem.users[0])
                    else:
                        with contextlib.suppress(BaseException):
                            if rem.channel:
                                channel = self.bot.get_channel(rem.channel)
                if channel is None:
                    channel = self.bot.get_user(rem.users[0])
                time = datetime.datetime.strptime(rem.date, '%d.%m.%Y %H:%M')
                if time <= now:
                    content = self.bot.get_user(rem.author).mention
                    color = discord.Color.blurple()
                    if not isinstance(channel, discord.User):
                        guild = channel.guild
                        if guild:
                            content = "" + \
                                ' '.join(
                                    [guild.get_role(role).mention for role in rem.roles])
                            content += " " + \
                                ' '.join(
                                    [guild.get_member(user).mention for user in rem.users])
                            color = guild.get_member(rem.author).color
                    embed = discord.Embed(
                        title="Erinnerung", description=rem.message, color=color)
                    embed.timestamp = datetime.datetime.now()
                    embed.set_footer(text=self.bot.get_user(
                        rem.author).name, icon_url=self.bot.get_user(rem.author).avatar)

                    remove_new_reminder(rem.author, rem)

                    # change reminder date if it is reocurring
                    if rem.reminder_again > 0:
                        embed.description += f"\n\nDiese Erinnerung wird noch {(str(rem.reminder_again) + ' weiteres Mal') if rem.reminder_again == 1 else (str(rem.reminder_again) + ' weitere Male')} eintreten."
                        rem.reminder_again -= 1
                        rem.date = (
                            time + self.parse_to_timedelta(rem.reminder_again_in)).strftime('%d.%m.%Y %H:%M')
                        embed.description += f"\nDas nächste Mal ist {rem.date}."
                        add_new_reminder(rem)

                    elif rem.reminder_again == -1:
                        embed.description += f"\n\nDiese Erinnerung wird noch unendlich weitere Male eintreten."
                        rem.date = (
                            time + self.parse_to_timedelta(rem.reminder_again_in)).strftime('%d.%m.%Y %H:%M')
                        embed.description += f"\nDas nächste Mal ist {rem.date}."
                        add_new_reminder(rem)

                    await channel.send(content=content, embed=embed)

    @checkReminder.before_loop
    async def beforeReminderCheck(self):
        await self.bot.wait_until_ready()
        print("reminder loop ready")

    @checkReminder.after_loop
    async def afterReminderCheck(self):
        print("reminder loop stopped")
        await asyncio.sleep(60)
        self.checkReminder.restart()

    @checkReminder.error
    async def ReminderCheckError(self, error):
        print("reminder loop error: ")
        print(error)

    def parse_to_timedelta(self, time_str) -> Optional[datetime.timedelta]:
        regex = re.compile(
            r'((?P<days>\d+?)d)?\s*((?P<hours>\d+?)h)?\s*((?P<minutes>\d+?)min)?')
        parts = regex.match(time_str)
        if not parts:
            return None
        d = parts.groupdict()
        for key in dict(d):
            if not d[key]:
                del d[key]
            elif d[key].isdigit():
                d[key] = int(d[key])
            else:
                return None
        return datetime.timedelta(**d)


def add_new_reminder(r):
    json_string = json.dumps(r.__dict__)
    reminder = get_reminder()
    authors = list(reminder.keys())
    if not str(r.author) in authors:
        reminder[str(r.author)] = []
    reminder[str(r.author)].append(json_string)
    update_reminder(reminder)


def remove_new_reminder(author, r):
    r = json.dumps(r.__dict__)
    reminder = get_reminder()
    authors = list(reminder.keys())
    if str(author) in authors and r in reminder[str(author)]:
        reminder[str(author)].pop(reminder[str(author)].index(r))
    update_reminder(reminder)


def update_reminder(reminder):
    config.dump("reminder.json", reminder)


def get_reminder():
    return config.load("reminder.json")


async def setup(bot):
    await bot.add_cog(Reminders(bot))
    print("Cog loaded: Reminder")
