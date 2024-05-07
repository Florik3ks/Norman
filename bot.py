'''
# invite link: 
id = 0
https://discord.com/api/oauth2/authorize?client_id={id}&permissions=8&scope=bot
'''

import discord
import asyncio
import traceback
import config.public_config as config
from discord.ext import commands
import config.private_config as private
from help.help_command import HelpCommand
from discord.ext.commands.errors import (CommandNotFound, MissingRequiredArgument)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=config.get("prefix"),
                   intents=intents, application_id=private.get("app_id"))
bot.owner_id = private.get("owner_id")


@bot.event
async def on_error(event, *args, **kwargs):
    print("on_error:\n")
    print(traceback.format_exc())
    print("\n\n")


@bot.event
async def on_command_error(ctx, error):
    
    
    error = error.original if hasattr(error, 'original') else error

    if isinstance(error, (CommandNotFound, MissingRequiredArgument)):
        return


    embed = discord.Embed(title=type(error).__name__[
                          :256], color=discord.Color.red())
    
    traceback_str = ""
    if hasattr(error, "text"):
        traceback_str = error.text + "\n"
    if hasattr(error, "offset"):
        traceback_str += " " * (error.offset - 1) + "^" + "\n"
    if hasattr(error, "msg"):
        traceback_str += error.msg
    if hasattr(error, "args"):
        traceback_str += "\n".join(error.args)

    if len(traceback_str) > 0:
        if len(traceback_str) > 2000:
            traceback_str = traceback_str[:1994] + "..."
        embed.description = f"```{traceback_str}```"

    print("on command error:")
    print(error)
    await ctx.send(embed=embed)


@bot.tree.error
async def on_app_command_error(interaction, error):
    print(f"on_slash_command_error:\n{error}")
    await interaction.channel.send(error)
    return


@bot.command()
async def syncguild(ctx):
    if ctx.author.id != bot.owner_id:
        return
    print("syncing..")
    bot.tree.copy_global_to(guild=ctx.guild)
    await bot.tree.sync(guild=ctx.guild)
    print("synced to guild " + ctx.guild.name)
    embed = discord.Embed(title="Synced to guild " +
                          ctx.guild.name, color=discord.Color.green())
    await ctx.send(embed=embed)


@bot.command()
async def sync(ctx):
    if ctx.author.id != bot.owner_id:
        return
    print("syncing globally..")
    await bot.tree.sync()
    print("synced globally")
    embed = discord.Embed(title="Synced", color=discord.Color.green())
    await ctx.send(embed=embed)


@bot.event
async def on_ready():
    await bot.change_presence(status=discord.enums.Status.dnd)
    print("ready")
    print(f"logged in as {bot.user}")


async def main():
    async with bot:
        await bot.load_extension("cogs.uni")
        await bot.load_extension("cogs.memes")
        await bot.load_extension("cogs.utility")
        await bot.load_extension("cogs.reminder")
        await bot.load_extension("cogs.wholesome")
        await bot.load_extension("cogs.user_messages")

        bot.help_command = HelpCommand()
        bot.on_command_error = on_command_error
        await bot.start(token=private.get("discord_token"), reconnect=True)


if __name__ == "__main__":
    asyncio.run(main())
