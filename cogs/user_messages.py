import json
import random
import discord
import datetime
import config.public_config as public_config
from discord.ext import commands


class UserMessages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = self.read_json()

    @commands.Cog.listener()
    async def on_message(self, message):
        js = self.data
        if str(message.author.id) in js.keys() and message.content in js[str(message.author.id)].keys():
            await message.channel.send(random.choice(js[str(message.author.id)][message.content]))

    @commands.command(aliases=["am"])
    async def addMessage(self, ctx, *args):
        """Füge eine neue Reaktion auf eine bestimmte Nachricht von dir hinzu.
        Die Syntax ist: `addMessage "deine Nachricht, falls es mehr als ein Wort ist in Hochkommas" "Die Reaktionsnachricht des Bots"`"""
        if len(args) != 2:
            await ctx.send(embed=simple_embed(ctx.author, "Du musst genau zwei Argumente angeben",
                                              'Die Syntax ist: `addMessage "deine Nachricht, falls es mehr als ein Wort ist in Hochkommas" "Die Reaktionsnachricht des Bots"`',
                                              color=discord.Color.red()))
            return
        self.add_in_json(ctx.author, args[0], args[1])
        e = simple_embed(ctx.author, "Erfolgreich hinzugefügt!",
                         color=ctx.author.color)
        e.description = f"`{args[1]}` wurde erfolgreich `{args[0]}` hinzugefügt."
        await ctx.send(embed=e)

    @commands.command(aliases=["rm"])
    async def removeMessage(self, ctx, *args):
        """Lösche eine bereits existierende Reaktion auf eine bestimmte Nachricht von dir.
        Die Syntax ist: `removeMessage "Nachricht, die gelöscht werden soll (in Hochkommas, falls mehr als ein Wort)"`"""
        if str(ctx.author.id) in self.data.keys():
            if len(args) != 1:
                await ctx.send(embed=simple_embed(ctx.author, "Du musst genau ein Argument angeben",
                                                  'Die Syntax ist: `removeMessage "Nachricht, die gelöscht werden soll (in Hochkommas, falls mehr als ein Wort)"`',
                                                  color=discord.Color.red()))
            elif args[0] in self.data[str(ctx.author.id)].keys():
                self.remove_from_json(ctx.author, args[0])
                e = simple_embed(
                    ctx.author, "Erfolgreich entfernt!", color=ctx.author.color)
                e.description = f"`{args[0]}` wurde erfolgreich entfernt."
                await ctx.send(embed=e)
            else:
                await ctx.send(embed=simple_embed(ctx.author, "Diese Nachricht befindet sich nicht in deinen Nachrichten.", color=discord.Color.red()))

        else:
            await ctx.send(embed=simple_embed(ctx.author, "Du hast keine eigenen Nachrichten eingestellt.", color=discord.Color.red()))

    @commands.command(aliases=["mm"])
    async def myMessages(self, ctx, *args):
        """Lasse deine eingestellten Nachrichten aufzählen"""
        e = discord.Embed(title="Deine Nachrichten", color=ctx.author.color)
        if str(ctx.author.id) in self.data.keys():
            for k in self.data[str(ctx.author.id)].keys():
                e.add_field(name=str(k), value=str(
                    self.data[str(ctx.author.id)][k]), inline=False)
        else:
            e.description = "Du hast keine eigenen Nachrichten eingestellt."
        await ctx.send(embed=e)

    def read_json(self):
        return public_config.load("userReactions.json", {})

    def add_in_json(self, user, on_msg, bot_reaction_msg):
        if str(user.id) not in self.data.keys():
            self.data[str(user.id)] = {}
        if on_msg not in self.data[str(user.id)].keys():
            self.data[str(user.id)][on_msg] = []
        self.data[str(user.id)][on_msg].append(bot_reaction_msg)
        public_config.dump("userReactions.json", self.data)

    def remove_from_json(self, user, key):
        del self.data[str(user.id)][key]
        public_config.dump("userReactions.json", self.data)


def simple_embed(author, title, description="", image_url="", color=discord.Color.blurple()):
    e = discord.Embed(title=title, description=description)
    if image_url != "":
        e.set_image(url=image_url)
    e.color = color
    e.timestamp = datetime.datetime.now()
    e.set_footer(text=author.name, icon_url=author.avatar)
    return e


async def setup(bot):
    await bot.add_cog(UserMessages(bot))
    print("Cog loaded: UserMessages")
