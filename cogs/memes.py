import discord
import asyncio
import requests
import validators
import contextlib
import config.public_config as public_config
from discord.ext import commands


class Memes(commands.Cog):
    """Commands zum Votingsystem im Shitpostkanal"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        if message.channel.id == public_config.get("meme_channel_id") and (len(message.attachments) > 0 or validators.url(message.content)):
            await self.addVotes(message)

    async def addVotes(self, message):
        up = get_emoji(self.bot, public_config.get("upvote_emoji"))
        down = get_emoji(self.bot, public_config.get("downvote_emoji"))
        await message.add_reaction(up)
        await message.add_reaction(down)
        cross = "\N{CROSS MARK}"
        await message.add_reaction(cross)

        # don't even know if it does work. Was a extension's suggestion
        with contextlib.suppress(asyncio.exceptions.TimeoutError):
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=lambda _reaction, _user: _user == message.author and _reaction.emoji == cross and _reaction.message == message)
            await message.clear_reaction(up)
            await message.clear_reaction(down)
        # don't even know if it does work. Was a extension's suggestion
        with contextlib.suppress(discord.errors.NotFound):
            await message.clear_reaction(cross)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # check if the channel of the reaction is the specified channel
        if payload.channel_id != public_config.get("meme_channel_id"):
            return
        # get user, message and reaction
        user = self.bot.get_user(payload.user_id)
        msg = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        reaction = None
        for reac in msg.reactions:
            if reac.emoji in [payload.emoji.name, payload.emoji]:
                reaction = reac
        if reaction is None:
            return

        # get up-/downvote emojis
        upvote = get_emoji(self.bot, public_config.get("upvote_emoji"))
        downvote = get_emoji(self.bot, public_config.get("downvote_emoji"))
        if user != self.bot.user:
            # in case the message author tries to up-/downvote their own post
            if reaction.message.author == user and reaction.emoji in [upvote, downvote]:
                await reaction.remove(user)

            # change voting counter
            if reaction.emoji == upvote:
                # pin message when it has the specified amount of upvotes
                if reaction.count - 1 >= public_config.get("upvotes_for_pin"):
                    # await reaction.message.pin(reason="good meme")
                    await self.send_good_meme(reaction.message)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        # check if the channel of the reaction is the specified channel
        if payload.channel_id != public_config.get("meme_channel_id"):
            return
        # get user, message and reaction
        user = self.bot.get_user(payload.user_id)
        msg = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        reaction = None
        for reac in msg.reactions:
            if reac.emoji in [payload.emoji.name, payload.emoji]:
                reaction = reac
        if reaction is None:
            return

    async def send_good_meme(self, msg, force=False):
        if not force:
            memes = public_config.load("goodMemes.json")

            if msg.id in memes:
                return

            memes.append(msg.id)
            public_config.dump("goodMemes.json", memes)

        channel = self.bot.get_channel(
            public_config.get("good_memes_channel_id"))
        e = discord.Embed()
        e.description = f"[Link zur Nachricht]({msg.jump_url})\n"
        if msg.reference != None:
            ref = discord.MessageReference(
                message_id=msg.reference.message_id, channel_id=msg.reference.channel_id)
            e.description += f"[Bezieht sich auf ...]({ref.jump_url})\n"

        e.set_author(name=msg.author,
                     icon_url=msg.author.avatar)
        e.color = msg.guild.get_member(
            msg.author.id).colour
        e.description += "\n" + msg.content
        e.timestamp = msg.created_at
        e.set_footer(text=msg.author.name, icon_url=msg.author.avatar)

        if len(msg.attachments) > 0:
            if is_url_image(msg.attachments[0].url):
                e.set_image(url=msg.attachments[0].url)
                counter = 0
                while e.image is None or e.image.width == 0 and counter < 100:
                    counter += 1
                    e.set_image(url=msg.attachments[0].url)
                await channel.send(embed=e)

            else:
                try:
                    await channel.send(embed=e, file=await msg.attachments[0].to_file())
                except Exception as e:
                    await channel.send(embed=e, file=await msg.attachments[0].url)

        else:
            if (is_url_image(msg.content)):
                e.description = e.description.splitlines()[0]
                e.set_image(url=msg.content)
            await channel.send(embed=e)


def get_emoji(bot, emoji_name):
    return discord.utils.get(bot.emojis, name=emoji_name) or None


def is_url_image(image_url):
    image_formats = ("image/png", "image/jpeg",
                     "image/jpg", "image/gif", "image/webp")
    try:
        r = requests.head(image_url)
        return r.headers["content-type"] in image_formats
    except Exception:
        return False


async def setup(bot):
    await bot.add_cog(Memes(bot))
    print("Cog loaded: Memes")
