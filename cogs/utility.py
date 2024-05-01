import os
import io
import ast
import typing
import random
import discord
import asyncio
import datetime
import contextlib
import config.public_config as public_config
from PIL import Image
from io import BytesIO
from PIL.ImageOps import invert
from discord.ext import commands
from discord.errors import HTTPException
from pnglatex.pnglatex import _get_fname, Path, _BINARIES, devnull, _cleanup, _run, _get_bin


_TEX_BP = """\\documentclass[a0,landscape]{{a0poster}}
\\usepackage{{mathtools}}
\\usepackage[german]{{babel}}
\\thispagestyle{{empty}}
\\usepackage{{lmodern}}
\\usepackage[left=1cm,right=1cm]{{geometry}}
\\begin{{document}}
{{\\fontsize{{36}}{{43}} \\selectfont

{0}
}}
\\end{{document}}"""


class Utility(commands.Cog):
    """Andere nützliche Commands"""

    def __init__(self, bot):
        self.bot = bot
        self.quotes = self.get_quotes()

    @commands.command()
    async def pfpart(self, ctx, big: typing.Optional[bool] = False):
        """Zeigt dein Discord-Profilbild in ASCII-Art"""
        bites = await ctx.author.avatar.read()
        im = Image.open(io.BytesIO(bites))
        r = im.convert('1')
        res = 64
        if big:
            res = 89
        r.thumbnail((res, res))
        im = r
        pix = r.load()

        def add_dot_position(x, y):
            # https://en.wikipedia.org/wiki/Braille_Patterns
            pos = [["1", "8", ],
                   ["2", "10", ],
                   ["4", "20", ],
                   ["40", "80"]]

            nx = x % 2
            ny = y % 4

            return pos[ny][nx] if pix[x, y] == 255 else "0"

        # returns the position in the array for a pixel at [x y]
        def get_arr_position(x, y):
            return x // 2, y // 4

        dots = []
        for y in range(im.height // 4):
            dots.append(["2800" for _ in range(im.width // 2)])

        for y in range((im.height // 4) * 4):
            for x in range((im.width // 2) * 2):
                nx, ny = get_arr_position(x, y)
                value = hex(int(dots[ny][nx], 16) +
                            int(add_dot_position(x, y), 16))
                dots[ny][nx] = value

        for y in range(len(dots)):
            for x in range(len(dots[0])):
                dots[y][x] = chr(int(dots[y][x], 16))

        e = discord.Embed(title="Dein Icon")
        e.set_footer(text=ctx.author.display_name,
                     icon_url=ctx.author.avatar)
        e.color = ctx.author.color
        e.timestamp = datetime.datetime.now()
        e.description = "{0}x{0}\n```".format(str(res))
        for line in dots:
            e.description += ''.join(line) + "\n"
        e.description += "```"

        await ctx.send(embed=e)

    # https://gist.github.com/nitros12/2c3c265813121492655bc95aa54da6b9 geklaut und überarbeitet
    @commands.is_owner()
    @commands.command(name="eval", aliases=["ev", "evaluate"])
    async def _eval(self, ctx, *, cmd):
        """Führt Code aus und sendet das Ergebnis der letzten Zeile, falls vorhanden.
            Beispiel: 
            ```,ev 
                for i in range(4):
                    await ctx.send(ctx.author.mention)
                "a"```"""
        def insert_returns(body):
            # insert return stmt if the last expression is a expression statement
            if isinstance(body[-1], ast.Expr):
                body[-1] = ast.Return(body[-1].value)
                ast.fix_missing_locations(body[-1])

            # for if statements, we insert returns into the body and the orelse
            if isinstance(body[-1], ast.If):
                insert_returns(body[-1].body)
                insert_returns(body[-1].orelse)

            # for with blocks, again we insert returns into the body
            if isinstance(body[-1], ast.With):
                insert_returns(body[-1].body)

        fn_name = "_eval_expr"

        cmd = cmd.strip("` ")

        # removes discord syntax highlighting if it exists
        if cmd.split("\n")[0] == "py":
            cmd = "\n".join(cmd.split("\n")[1:])

        # add a layer of indentation
        cmd = "\n".join(f"    {i}" for i in cmd.splitlines())

        # wrap in async def body
        body = f"async def {fn_name}():\n{cmd}"

        parsed = ast.parse(body)
        body = parsed.body[0].body

        insert_returns(body)

        env = dict(globals(), **locals())
        env["bot"] = self.bot

        exec(compile(parsed, filename="<ast>", mode="exec"), env)

        result = (await eval(f"{fn_name}()", env))

        with contextlib.suppress(HTTPException):
            if type(result) != discord.message.Message:
                await ctx.send(result)

    def ownpnglatex(self, tex_string, output=None):
        """
        Produce an png based on a input LaTeX snippet.

        @param tex_string: The LaTeX string.
        @param output: The output filename. It can also be a pathlib.Path object.
                    If not provided, this will be randomly generated.

        @return: A Path object of the output file
        @raises ValueError: If the input is empty of something went wrong with
                            the image creation.
        """

        if not tex_string:
            raise ValueError("LaTeX expression cannot be empty!")
        jobname = _get_fname()
        output = output or jobname + '.png'
        tex_string = _TEX_BP.format(tex_string)
        binaries = tuple(_get_bin(b) for b in _BINARIES)

        with _cleanup(jobname), open(devnull, 'w') as null:
            status = _run(tex_string, jobname, output, null, binaries)

        if status != 0:
            with Path(output) as o:
                with contextlib.suppress(FileNotFoundError):
                    o.unlink()
            raise ValueError("Failed to generate png file.")
        return Path(output)

    def latexToImage(self, formula):
        image = Image.open(self.ownpnglatex(
            r"$"+formula+r"$", 'tmpFormula.png'))

        image = invert(image)
        image = image.convert("RGBA")
        datas = image.getdata()

        new_data = []
        for item in datas:
            if item[0] == 0 and item[1] == 0 and item[2] == 0:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)

        image.putdata(new_data)
        return image

    @commands.command()
    async def latex(self, ctx, *, arg):
        """Schickt ein Bild, welches dem angegebenen Latex-Code entspricht.
        [Hier ist eine generelle Hilfe](https://de.wikipedia.org/wiki/Hilfe:TeX), [hier ist eine Liste an Sonderzeichen](https://de.wikibooks.org/wiki/LaTeX-Kompendium:_Sonderzeichen),
        und hier eine ausführlichere und längere [Liste von Zeichen](https://www.caam.rice.edu/~heinken/latex/symbols.pdf)"""
        arg = arg.strip("` ")
        try:
            img = self.latexToImage(arg)
        except ValueError:
            await ctx.send(embed=discord.Embed(title="Ungültige Eingabe", color=discord.Color.red()))
            return
        # img = img.resize((int(img.width * 2), int(img.height * 2)))#, Image.ANTIALIAS)
        with BytesIO() as image_binary:
            if not os.path.exists(os.path.join(os.path.dirname(__file__), "..", "tmp")):
                os.mkdir(os.path.join(os.path.dirname(__file__), "..", "tmp"))
            os.chdir(os.path.join(os.path.dirname(__file__), "..", "tmp"))
            
            img.save(image_binary, 'PNG')
            image_binary.seek(0)
            await ctx.send(file=discord.File(fp=image_binary, filename='image.png'))

    @commands.command()
    async def addzitat(self, ctx, *, arg):
        """Fügt ein Zitat der Zitate-sammlung hinzu"""
        e = discord.Embed(
            title="Möchtest du dieses Zitat speichern?", description=arg)
        msg = await ctx.channel.send(embed=e)
        check = "\N{White Heavy Check Mark}"
        await msg.add_reaction(check)
        cross = "\N{CROSS MARK}"
        await msg.add_reaction(cross)
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=lambda _reaction, _user: _user == ctx.message.author and _reaction.emoji in [check, cross] and _reaction.message == msg)

        except asyncio.TimeoutError:
            e.color = discord.Color.orange()
            await msg.edit(embed=e)
            return
        if reaction.emoji == cross:
            e.color = discord.Color.orange()
            await msg.edit(embed=e)
        elif reaction.emoji == check:
            self.add_quote(arg)
            e.color = discord.Color.green()
            await msg.edit(embed=e)

    @commands.command()
    async def getzitat(self, ctx, *args):
        """Gibt ein zufälliges Zitat aus der Zitatesammlung aus."""
        if len(self.quotes) == 0:
            await ctx.channel.send(embed=discord.Embed(ctx.author, "Es sind keine Zitate vorhanden.", color=discord.Color.red()))
            return
        quote = random.choice(self.quotes)
        random_quote = True
        if args and args[0].isnumeric():
            index = int(args[0])
            if (1 <= index <= len(self.quotes)):
                quote = self.quotes[index - 1]
                random_quote = False

        e = discord.Embed(title=("Zufälliges " if random_quote else "") +
                          "Zitat Nr. " + str(self.quotes.index(quote) + 1), description=quote)
        await ctx.channel.send(embed=e)

    def get_quotes(self):
        return public_config.load("quotes.json", [])

    def add_quote(self, quote):
        self.quotes.append(quote)
        public_config.dump("quotes.json", self.quotes)


async def setup(bot):
    await bot.add_cog(Utility(bot))
    print("Cog loaded: Utility")
