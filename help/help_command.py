from typing import Any
import discord
import datetime
from discord.ext import commands


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
        for name in self.context.bot.cogs:
            c = self.context.bot.cogs[name]
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

        elif page in [self.context.bot.cogs[k] for k in self.context.bot.cogs.keys()]:
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
