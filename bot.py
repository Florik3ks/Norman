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
bot = commands.Bot(command_prefix=config.get("prefix"), intents=intents, application_id=secrets.get("app_id"))
bot.owner_id = secrets.get("owner_id")

@bot.event
async def on_error(event, *args, **kwargs):
    print("on_error:\n")
    print(traceback.format_exc())
    print("\n\n")

@bot.event
async def on_command_error(ctx, error):
    print("on_command_error:\n")
    return


@bot.tree.error
async def on_app_command_error(ctx, error):
    print(f"on_slash_command_error:\n{error}")
    return
    
    
    # # if this is not manually called with a textchannel as ctx and the ctx has no own error handler 
    # if not isinstance(ctx, discord.TextChannel) and hasattr(ctx.command, 'on_error'):
    #     print("on_command_error:\n")
    #     print(traceback.format_exception(type(error), value=error, tb=error.__traceback__))
    #     print("\n\n")
    #     return

    # error: Exception = getattr(error, 'original', error)
    # if isinstance(error, (CommandNotFound, MissingRequiredArgument)):
    #     return
    # if isinstance(error, (NotOwner, CheckFailure)):
    #     await ctx.send(embed=simple_embed(ctx.author, "Du hast keine Berechtigung diesen Command auszuführen.", color=discord.Color.red()))
    #     return
    # if isinstance(error, (UserNotFound)):
    #     await ctx.send(embed=simple_embed(ctx.author, "Der angegebene Nutzer wurde nicht gefunden.", color=discord.Color.red()))
    #     return
    # embed = discord.Embed(title=repr(error)[:256])
    # embed.color = discord.Color.red()
    # traceback_str = ''.join(traceback.format_exception(type(error), value=error, tb=error.__traceback__))

    # embed.description = f"```{traceback_str}```"
    # if len(embed.description) > 2000: 
    #     embed.description = f"```{traceback_str[-1994:]}```"

    # await ctx.send(embed=embed)


@bot.event
async def on_ready():
    await bot.change_presence(status=discord.enums.Status.dnd)
    print("ready")
    await bot.tree.sync()
    print("synced")
    print(f"logged in as {bot.user}")
        

async def main():
    async with bot:
        await bot.load_extension("cogs.reminder")
        await bot.load_extension("cogs.wholesome")
        # await bot.load_extension("cogs.user_messages")
        # await bot.load_extension("cogs.utility")
        # await bot.load_extension("cogs.memes")

        # await bot.load_extension("cogs.uni")
        bot.on_command_error = on_command_error
        await bot.start(token=secrets.get("discord_token"), reconnect=True)

if __name__ == "__main__":
    asyncio.run(main())
