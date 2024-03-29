'''
https://discord.com/api/oauth2/authorize?client_id=760125323580276757&permissions=8&scope=bot
'''
import asyncio
import datetime
import traceback

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands.errors import (CheckFailure, CommandNotFound,
                                         MissingRequiredArgument, NotOwner, UserNotFound)

import config
from helper_functions import simple_embed

intents = discord.Intents.all()
intents.messages = True
intents.presences = True
bot = commands.Bot(command_prefix=config.PREFIX, intents=intents, application_id=config.APP_ID)
# tree = app_commands.CommandTree(bot)
bot.owner_ids = config.OWNER_IDS

@bot.event
async def on_error(event, *args, **kwargs):
    embed = discord.Embed(title=f'new Error in event {event}()')
    embed.color = discord.Color.red()
    embed.description = f"```{traceback.format_exc()}```"
    embed.set_footer(text=kwargs)
    channel = bot.get_channel(config.LOG_CHANNEL_ID)
    await channel.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    # if this is not manually called with a textchannel as ctx and the ctx has no own error handler 
    if not isinstance(ctx, discord.TextChannel) and hasattr(ctx.command, 'on_error'):
        print("on_command_error:\n")
        print(traceback.format_exception(type(error), value=error, tb=error.__traceback__))
        print("\n\n")
        return

    error: Exception = getattr(error, 'original', error)
    if isinstance(error, (CommandNotFound, MissingRequiredArgument)):
        return
    if isinstance(error, (NotOwner, CheckFailure)):
        await ctx.send(embed=simple_embed(ctx.author, "Du hast keine Berechtigung diesen Command auszuführen.", color=discord.Color.red()))
        return
    if isinstance(error, (UserNotFound)):
        await ctx.send(embed=simple_embed(ctx.author, "Der angegebene Nutzer wurde nicht gefunden.", color=discord.Color.red()))
        return
    embed = discord.Embed(title=repr(error)[:256])
    embed.color = discord.Color.red()
    traceback_str = ''.join(traceback.format_exception(type(error), value=error, tb=error.__traceback__))

    embed.description = f"```{traceback_str}```"
    if len(embed.description) > 2000: 
        embed.description = f"```{traceback_str[-1994:]}```"

    await ctx.send(embed=embed)


@bot.event
async def on_ready():
    activity = discord.Activity(
        type=discord.ActivityType.listening, name=config.STATUS_MSG)
    await bot.change_presence(activity=activity, status=discord.enums.Status.dnd)
    e = discord.Embed(title="Bot started")
    e.color = discord.Color.blurple()
    e.timestamp = datetime.datetime.now()
    e.set_footer(text=bot.user.name, icon_url=bot.user.avatar)
    channel = bot.get_channel(config.LOG_CHANNEL_ID)
    await channel.send(embed=e)
    if(config.DEBUG):
        await bot.tree.sync(guild=config.DEBUG_GUILD)
    else:
        await bot.tree.sync()
        
def is_bot_dev():
    async def predicate(ctx):
        return ctx.author.id in config.OWNER_IDS or 761237826758246412 in [r.id for r in bot.get_guild(config.SERVER_ID).get_member(ctx.author.id).roles]

    return commands.check(predicate)


class LeftRight(discord.ui.View):
    def __init__(self, embed, pages, page, ctx):
        super().__init__(timeout=60)
        self.e = embed
        self.value = 0
        self.pages = pages
        self.page = page
        self.ctx = ctx

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True

        await self.message.edit(view=self)

    async def updateEmbed(self, interaction, value):
        e = self.e
        pages = self.pages
        page_count = len(pages)
        if value == -1 and self.page > 0:
            self.page -= 1
        elif value == 1 and self.page < page_count - 1:
            self.page += 1
        else:
            await interaction.response.edit_message(embed=e, view=self)
            return
        e.clear_fields()
        e.title = pages[self.page][0]
        e.description = pages[self.page][1]

        for cmd in pages[self.page][2]:
            e.add_field(name=f"{cmd.name} \n< {' | '.join(cmd.aliases)} >" if len(cmd.aliases) > 0 else cmd.name + "\n<>",
                        value=cmd.short_doc if cmd.short_doc != '' else " - ")
            
        e.set_footer(text=f"{self.page + 1} / {page_count}",
                        icon_url=self.ctx.author.avatar)
        
        await interaction.response.edit_message(embed=e, view=self)

    @discord.ui.button(emoji="\u25C0", style=discord.ButtonStyle.blurple)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.updateEmbed(interaction, -1)

    @discord.ui.button(emoji="\u25B6", style=discord.ButtonStyle.blurple)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.updateEmbed(interaction, 1)
        
        
class HelpCommand(commands.HelpCommand):
    """Zeigt eine hilfreiche Auflistung aller Commands"""

    async def send_bot_help(self, mapping):
        await self.send_pages()

    async def send_cog_help(self, cog):
        if len(cog.get_commands()) > 0:
            await self.send_pages(cog)
        else:
            await self.context.send("Diese Kategorie beinhaltet keine Commands.")

    async def can_run_cmd(self, cmd):
        try:
            return await cmd.can_run(self.context)
        except Exception:
            return False

    async def send_command_help(self, command):
        e = discord.Embed(title=command.name, color=discord.Color.blurple())
        cmdhelp = command.help if command.help != None else " - "
        e.description = f"```{' | '.join(command.aliases)}```" + \
            cmdhelp if len(command.aliases) > 0 else cmdhelp
        e.set_footer(icon_url=self.context.author.avatar)
        e.timestamp = datetime.datetime.now()

        if not await self.can_run_cmd(command):
            e.color = discord.Color.red()
            e.description += "\nDu hast keine Berechtigungen, diesen Command auszuführen."
        await self.get_destination().send(embed=e)

    async def prepare_pages(self):  
        pages = []
        for name in bot.cogs:
            c = bot.cogs[name]
            usable_commands = [cmd for cmd in c.get_commands() if await self.can_run_cmd(cmd)]
            if usable_commands:
                pages.append([name, c.description, usable_commands])
        return pages

    async def send_pages(self, page=""):
        ctx = self.context
        destination = self.get_destination()
        e = discord.Embed(color=discord.Color.blurple(), description='')

        pages = await self.prepare_pages()
        if page == "":
            page = 0

        elif page in [bot.cogs[k] for k in bot.cogs.keys()]:
            page = [i for i in range(len(pages))
                    if pages[i][0] == page.qualified_name][0]

        page_count = len(pages)
        e.title = pages[page][0]
        e.description = pages[page][1]

        for cmd in pages[page][2]:
            e.add_field(name=f"{cmd.name} \n< {' | '.join(cmd.aliases)} >" if len(cmd.aliases) > 0 else cmd.name + "\n<>",
                        value=cmd.short_doc if cmd.short_doc != '' else " - ")
        e.set_footer(text=f"{page + 1} / {page_count}",
                     icon_url=ctx.author.avatar)

        e.timestamp = datetime.datetime.now()
        view = LeftRight(e, pages, page, ctx)
        msg = await destination.send(embed=e, view=view)
        view.message = msg
        await view.wait()
        e.color = discord.Color.orange()
        await msg.edit(embed=e)


# class ServerRules(commands.Cog):
#     def __init__(self, bot):
#         self.bot = bot

#     @commands.Cog.listener()
#     async def on_guild_update(self, before, after):
#         if after.id == 693062821650497597:
#             if after.name != "Mujika-Kult":
#                 await after.edit(name="Mujika-Kult")

#     @commands.Cog.listener()
#     async def on_message(author, message):
#         if message.channel.id == 804652343428644874 and not message.author.id in config.wortspielAllowedUserIds:
#             await message.delete()

# bot.add_cog(ServerRules(bot))


async def main():
    async with bot:
        await bot.load_extension("cogs.reminder")
        await bot.load_extension("cogs.user_messages")
        await bot.load_extension("cogs.wholesome")
        await bot.load_extension("cogs.utility")
        await bot.load_extension("cogs.memes")

        await bot.load_extension("cogs.uni")

        # await bot.load_extension("cogs.news")
        await bot.load_extension("cogs.debug")
        await bot.load_extension("cogs.music")

        bot.help_command = HelpCommand()

        # await bot.tree.sync()
        # print(bot.tree)
        # await bot.tree.copy_global_to(guild=discord.Object(id=572410770520932352))
        
        await bot.start(config.TOKEN, reconnect=True)

if __name__ == "__main__":
    asyncio.run(main())
