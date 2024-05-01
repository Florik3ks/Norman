'''
https://discord.com/api/oauth2/authorize?client_id=760125323580276757&permissions=8&scope=bot
'''
import asyncio
import datetime
import traceback

import discord
from discord import app_commands
from discord.ext import commands

import public_config as config
import private_config as secrets

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=config.get("prefix"),
                   intents=intents, application_id=secrets.get("app_id"))
bot.owner_id = secrets.get("owner_id")


@bot.event
async def on_error(event, *args, **kwargs):
    print("on_error:\n")
    print(traceback.format_exc())
    print("\n\n")


@bot.event
async def on_command_error(ctx, error):
    error = error.original if hasattr(error, 'original') else error
    embed = discord.Embed(title=type(error).__name__[
                          :256], color=discord.Color.red())
    # traceback_str = ''.join(traceback.format_exception(type(error), value=error, tb=error.__traceback__))
    traceback_str = error.text + "\n"
    if hasattr(error, "offset"):
        traceback_str += " " * (error.offset - 1) + "^" + "\n"
    if hasattr(error, "msg"):
        traceback_str += error.msg

    embed.description = f"```{traceback_str}```"
    if len(embed.description) > 2000:
        embed.description = f"```{traceback_str[-1994:]}```"

    await ctx.send(embed=embed)


@bot.tree.error
async def on_app_command_error(ctx, error):
    print(f"on_slash_command_error:\n{error}")
    await ctx.send(error.text)
    return


@bot.command()
async def syncguild(ctx):
    if ctx.author.id != bot.owner_id:
        return
    print("syncing..")
    bot.tree.copy_global_to(guild=ctx.guild)
    await bot.tree.sync(guild=ctx.guild)
    print("synced to guild " + ctx.guild.name)
    embed = discord.Embed(title="Synced to guild " + ctx.guild.name, color=discord.Color.green())
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
        await bot.load_extension("cogs.reminder")
        await bot.load_extension("cogs.wholesome")
        await bot.load_extension("cogs.utility")
        await bot.load_extension("cogs.uni")

        # await bot.load_extension("cogs.user_messages")
        # await bot.load_extension("cogs.memes")

        bot.on_command_error = on_command_error
        await bot.start(token=secrets.get("discord_token"), reconnect=True)


if __name__ == "__main__":
    asyncio.run(main())
