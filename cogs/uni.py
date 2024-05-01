import hashlib
import os
import discord
from discord.ext import commands, tasks
import traceback
import json
import config.public_config as public_config
from discord import app_commands
from typing import List, Optional

from PyPDF2 import PdfReader
import re
from datetime import datetime
import locale

DISCORD_TIMESTAMP = "<t:{timestamp}:D> (<t:{timestamp}:R>)"


class DeleteAssignment(discord.ui.View):

    def __init__(self, data, channel, update_data):
        super().__init__(timeout=60.0)
        self.assignments = data["assignments"]["channels"][channel].keys()
        self.update_data = update_data
        self.data = data

        self.options = [
            discord.SelectOption(
                label=assignment,
                value=assignment
            ) for i, assignment in enumerate(self.assignments)]

        self.select = discord.ui.Select(
            options=self.options,
            min_values=1,
            max_values=1,
            placeholder="Wähle das Assignment aus, das du löschen möchtest."
        )
        self.select.callback = self.callback
        self.add_item(self.select)

    async def callback(self, interaction: discord.Interaction) -> None:
        self.select.disabled = True
        embed = discord.Embed(
            title=f"Das Assignment {interaction.data['values'][0]} wurde gelöscht.", color=discord.Color.green())

        del self.data["assignments"]["channels"][str(
            interaction.channel.id)][interaction.data['values'][0]]
        update_data(self.data)

        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        await interaction.response.send_message('Oops! Something went wrong. ' + str(error), ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_exception(type(error), error, error.__traceback__)


class AddAssignmentModal(discord.ui.Modal, title='Assignment'):
    def __init__(self, data, update_data, update_assignments, assignment=None, channel=None):
        self.data = data
        self.update_data = update_data
        self.update_assignments = update_assignments
        self.edit = False
        self.assignment = None
        super().__init__()
        if assignment:
            self.assignment = assignment
            self.name.default = assignment
            self.path.default = data["assignments"]["channels"][str(
                channel)][assignment]["path"]
            self.pattern.default = data["assignments"]["channels"][str(
                channel)][assignment]["pattern"]
            self.datetime_pattern.default = data["assignments"]["channels"][str(
                channel)][assignment]["datetime_pattern"]
            self.edit = True

    name = discord.ui.TextInput(
        label='Fach',
        placeholder='LA2'
    )

    path = discord.ui.TextInput(
        label='PFERD Pfad',
        placeholder='SS-23/LA-2/Übungsblätter/'
    )

    pattern = discord.ui.TextInput(
        label='Zeilen pattern, G1 ist Datum, G2 ist Uhrzeit.',
        placeholder='.*zum[ ]?(\\d\\d.\\d\\d.\\d\\d\\d\\d)[ ]?um[ ]?(\\d\\d)[ ]?Uhr',
        required=False
    )

    datetime_pattern = discord.ui.TextInput(
        label='Datums pattern',
        placeholder='%d.%m.%Y %H',
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = str(interaction.channel.id)
        if not channel in self.data["assignments"]["channels"].keys():
            self.data["assignments"]["channels"][channel] = {}
            print("creating new")

        if not self.edit and self.name.value in self.data["assignments"]["channels"][channel].keys():
            await interaction.response.send_message(embed=discord.Embed(title=f'Das Fach {self.name.value} existiert hier bereits!', color=discord.Color.red()), ephemeral=True)
            return

        entry = {
            self.name.value: {
                "path": self.path.value,
                "pattern": self.pattern.value,
                "datetime_pattern": self.datetime_pattern.value,
                "assignments": self.data["assignments"]["channels"][channel][self.assignment]["assignments"] if self.edit else {}
            }
        }
        self.data["assignments"]["channels"][channel].update(entry)
        update_data(self.data)
        end = "bearbeitet" if self.edit else "hinzugefügt"
        e = discord.Embed(title=f"Hook für {self.name.value} wurde erfolgreich {end}!", color=discord.Color.green())
        e.description = "```"
        e.description += f"Path: {self.path.value}\n"
        e.description += f"Pattern: {self.pattern.value}\n" if self.pattern.value else ""
        e.description += f"Datetime Pattern: {self.datetime_pattern.value}" if self.datetime_pattern.value else ""
        e.description += "```"
        await interaction.response.send_message(embed=e)
        await self.update_assignments()

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message(embed=discord.Embed(title="Etwas ist schiefgelaufen", color=discord.Color.red()), ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_exception(type(error), error, error.__traceback__)


class Uni(commands.Cog):
    """Commands zum debuggen"""

    def __init__(self, bot):
        self.bot = bot
        self.data = get_data()
        self.update_assignments.start()

    def cog_unload(self):
        self.update_assignments.cancel()

    @app_commands.command(name="addassignmenthook", description="Erstellt einen Assignment Hook in diesem Channel.")
    async def addAssignmentHook(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddAssignmentModal(self.data, update_data, update_assignments=self.update_assignments))

    @app_commands.command(name="removeassignmenthook", description="Entfernt einen Assignment Hook in diesem Channel.")
    async def removeAssignmentHook(self, interaction: discord.Interaction):
        channel = str(interaction.channel.id)
        if not channel in self.data["assignments"]["channels"].keys():
            await interaction.response.send_message(embed=discord.Embed(title=f'Es gibt keine Assignment Hooks in diesem Channel!', color=discord.Color.red()), ephemeral=True)
            return

        await interaction.response.send_message(view=DeleteAssignment(self.data, channel, update_data), ephemeral=True)

    async def update_assignment_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        choices = [x for x in self.data["assignments"]
                   ["channels"][str(interaction.channel.id)].keys()]
        return [
            app_commands.Choice(name=choice, value=choice) for choice in choices if current.lower() in choice.lower()
        ]

    @app_commands.command(name="editassignmenthook", description="Bearbeitet einen Assignment Hook in diesem Channel.")
    @app_commands.describe(
        assignment="Assignment, welches aktualisiert werden soll",
    )
    @app_commands.autocomplete(assignment=update_assignment_autocomplete)
    async def editAssignmentHook(self, interaction: discord.Interaction, assignment: str):
        channel = str(interaction.channel.id)
        if not channel in self.data["assignments"]["channels"].keys():
            await interaction.response.send_message(embed=discord.Embed(title=f'Es gibt keine Assignment Hooks in diesem Channel!', color=discord.Color.red()), ephemeral=True)
            return

        assignments = self.data["assignments"]["channels"][channel]
        if not assignment in assignments.keys():
            await interaction.response.send_message(embed=discord.Embed(title=f'Das Assignment {assignment} existiert hier nicht!', color=discord.Color.red()), ephemeral=True)
            return

        await interaction.response.send_modal(AddAssignmentModal(self.data, update_data=update_data, assignment=assignment, channel=channel, update_assignments=self.update_assignments))

    async def send_to_channel(self, file, date, channel_id, ver=1):
        filename = file.split("/")[-1].split("\\")[-1]
        channel = self.bot.get_channel(channel_id)
        f = discord.File(file)
        if ver > 1:
            date_str = f", Abgabedatum {date}" if date else ""
            await channel.send(f"``{filename}`` wurde aktualisiert. Version: ``{ver}``{date_str}", file=f)
            return
        date_str = f", Abgabe am {date}" if date else ""
        await channel.send(f"Neues Übungsblatt: ``{filename}``{date_str}", file=f)

    @tasks.loop(hours=2)
    async def update_assignments(self):
        # load files (https://github.com/Garmelon/PFERD)
        os.chdir(os.path.dirname(__file__) + os.sep + ".." + os.sep + "assignment-data")
        os.popen("sh loadAssignments.sh").read()
        
        change = False
        fulldata = get_data()

        for channel in fulldata["assignments"]["channels"].keys():
            data = fulldata["assignments"]["channels"][channel]
            channel = int(channel)
            for subject in data.keys():
                path = data[subject]["path"] + os.sep

                locale = "de_DE.UTF-8"
                if "locale" in data[subject]:
                    locale = data[subject]["locale"]
                # iterate over pdf files in assignment folder
                for root, dirs, files in os.walk(path):
                    root += os.sep
                    for file in files:

                        if not file.endswith(".pdf"):
                            continue

                        # check whether file is already in data
                        if file not in data[subject]["assignments"].keys():
                            date = self.get_due_date(
                                root + file,
                                data[subject]["pattern"],
                                data[subject]["datetime_pattern"],
                                locale
                            )

                            with open(root + file, "rb") as f:
                                filehash = hashlib.sha1(f.read()).hexdigest()

                            data[subject]["assignments"][file] = {
                                "version": 1,
                                "last_change": datetime.now().timestamp(),
                                "hash": filehash
                            }
                            await self.send_to_channel(root + file, date, channel)
                            change = True

                        else:
                            # # check if file hash has changed
                            with open(root + file, "rb") as f:
                                filehash = hashlib.sha1(f.read()).hexdigest()

                            if filehash != data[subject]["assignments"][file]["hash"]:
                                date = self.get_due_date(
                                    root + file,
                                    data[subject]["pattern"],
                                    data[subject]["datetime_pattern"],
                                    locale
                                )
                                data[subject]["assignments"][file]["version"] += 1
                                data[subject]["assignments"][file]["last_change"] = datetime.now(
                                ).timestamp()
                                data[subject]["assignments"][file]["hash"] = filehash

                                await self.send_to_channel(
                                    root + file,
                                    date,
                                    channel,
                                    data[subject]["assignments"][file]["version"]
                                )
                                change = True

            # update data file
            if change:
                update_data(fulldata)

    @update_assignments.before_loop
    async def before_assignment_loop(self):
        await self.bot.wait_until_ready()

    @update_assignments.error
    async def assignment_error(self, error):
        print("Error in assignment loop")
        traceback.print_exception(type(error), error, error.__traceback__)

    def get_due_date(self, path, time_pattern, datetime_pattern, locale_="de_DE.UTF-8"):
        try:
            locale.setlocale(locale.LC_TIME, locale_)
            pdf_reader = PdfReader(path)
            for page in pdf_reader.pages:
                lines = page.extract_text().splitlines()
                for line in lines:
                    if re.match(time_pattern, line) and len(re.match(time_pattern, line).groups()) > 1:
                        date = re.match(time_pattern, line).group(1)
                        time = re.match(time_pattern, line).group(2)
                        actual_date = datetime.strptime(
                            date + " " + time, datetime_pattern)
                        # set year if none is specified
                        if actual_date.year < datetime.now().year:
                            actual_date = actual_date.replace(
                                year=datetime.now().year)
                        # fix year if date is in the next year (e.g. 1.1.20xx)
                        if actual_date.timestamp() < datetime.now().timestamp():
                            actual_date = actual_date.replace(
                                year=datetime.now().year + 1)
                        return DISCORD_TIMESTAMP.format(timestamp=int(actual_date.timestamp()))
        except ValueError as e:
            return None


def update_data(data):
    public_config.dump("assignments.json", data)


def get_data():
    return public_config.load("assignments.json")


async def setup(bot):
    if get_data() == {}:
        update_data({
            "assignments": {
                "channels": {}
            }
        })

    await bot.add_cog(Uni(bot))
    print("Cog loaded: Uni")


# structure is:
"""
    "channels" : {
        "channel_id" : {
            "subject_name" : {
                "path" : "",
                "pattern": "",              # pattern to find the time line, Group 1 is date, Group 2 is time
                "datetime_pattern": "",     
                "locale": "",
                "assignments" : {
                    "BlattXX": {
                        "hash": "",
                        "version": 0,
                        "last_change": 0
                    }
                }
            }
        }
    }
"""
