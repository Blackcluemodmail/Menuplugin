import asyncio
import copy

import discord
from discord.ext import commands
from discord.ext.commands.view import StringView

from core import checks
from core.models import DummyMessage, PermissionLevel
from core.utils import normalize_alias


class Menu(commands.Cog):
    """Reaction-based menu for threads"""
    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.plugin_db.get_partition(self)

    @commands.Cog.listener()
    async def on_thread_ready(self, thread, creator, category, initial_message):
        """Sends out menu to user"""
        menu_config = await self.db.find_one({'_id': 'config'})
        if menu_config:
            message = DummyMessage(copy.copy(initial_message))
            message.author = self.bot.modmail_guild.me
            message.content = menu_config['content']
            msgs, _ = await thread.reply(message)
            main_recipient_msg = None

            for m in msgs:
                if m.channel.recipient == thread.recipient:
                    main_recipient_msg = m
                    break

            for r in menu_config['options']:
                await main_recipient_msg.add_reaction(r)
                await asyncio.sleep(0.3)

            config = await self.db.find_one({"_id": "config"})
            re = config.get("reaction-emojis")
            if re:
                for r2 in re.get("emojis", []):
                    await main_recipient_msg.add_reaction(
                    discord.utils.get(message.guild.emojis, id=r2)
               )

            try:
                reaction, _ = await self.bot.wait_for('reaction_add', check=lambda r, u: r.message == main_recipient_msg and u == thread.recipient and str(r.emoji) in menu_config['options'], timeout=120)
            except asyncio.TimeoutError:
                message.content = 'No reaction received in menu... timing out'
                await thread.reply(message)
            else:
                alias = menu_config['options'][str(reaction.emoji)]
  
            try:
                reaction2, _ = await self.bot.wait_for('reaction_add', check=lambda r2, u: r2.message == main_recipient_msg and u == thread.recipient and str(r2.emoji) in menu_config['ooptions'], timeout=120)
            except asyncio.TimeoutError:
                message.content = 'No reaction received in menu... timing out'
                await thread.reply(message)
            else:
                message = DummyMessage(copy.copy(initial_message))
                message.author = self.bot.modmail_guild.me
                message.content = menu_config['content']
                msgs, _ = await thread.reply(message)
                main_recipient_msg = None

                ctxs = []
                if alias is not None:
                    ctxs = []
                    aliases = normalize_alias(alias)
                    for alias in aliases:
                        view = StringView(self.bot.prefix + alias)
                        ctx_ = commands.Context(prefix=self.bot.prefix, view=view, bot=self.bot, message=message)
                        ctx_.thread = thread
                        discord.utils.find(view.skip_string, await self.bot.get_prefix())
                        ctx_.invoked_with = view.get_word().lower()
                        ctx_.command = self.bot.all_commands.get(ctx_.invoked_with)
                        ctxs += [ctx_]
 
                for ctx in ctxs:
                    if ctx.command:
                        old_checks = copy.copy(ctx.command.checks)
                        ctx.command.checks = [checks.has_permissions(PermissionLevel.INVALID)]

                        await self.bot.invoke(ctx)

                        ctx.command.checks = old_checks
                        continue

    @checks.has_permissions(PermissionLevel.MODERATOR)
    @commands.command()
    async def configmenu(self, ctx):
        """Creates a new menu"""
        config = {}

        try:
            await ctx.send('What is the menu message?')
            m = await self.bot.wait_for('message', check=lambda x: ctx.message.channel == x.channel and ctx.message.author == x.author, timeout=300)
            config['content'] = m.content

            await ctx.send('How many options are available?')
            m = await self.bot.wait_for('message', check=lambda x: ctx.message.channel == x.channel and ctx.message.author == x.author and x.content.isdigit(), timeout=300)
            options_len = int(m.content)
            config['options'] = {}

            for _ in range(options_len):
                await ctx.send('What is the option emoji?')
                while True:
                    m = await self.bot.wait_for('message', check=lambda x: ctx.message.channel == x.channel and ctx.message.author == x.author, timeout=300)
                    try:
                        await m.add_reaction(m.content)
                    except discord.HTTPException:
                        await ctx.send('Invalid emoji. Send another.')
                    else:
                        emoji = m.content
                        break

                await ctx.send('What is the option command? (e.g. `reply Transferring && move 1238343847384`)')
                m = await self.bot.wait_for('message', check=lambda x: ctx.message.channel == x.channel and ctx.message.author == x.author, timeout=300)
                config['options'][emoji] = m.content
        except asyncio.TimeoutError:
            await ctx.send('Timeout. Re-run the command to create a menu.')
        else:
            await self.db.find_one_and_update({'_id': 'config'}, {'$set': config}, upsert=True)
            await ctx.send('Success')

    @checks.has_permissions(PermissionLevel.MODERATOR)
    @commands.command()
    async def clearmenu(self, ctx):
        """Removes an existing menu"""
        await self.db.find_one_and_delete({'_id': 'config'})
        await ctx.send('Success')

    @checks.has_permissions(PermissionLevel.MODERATOR)
    @commands.command()
    async def configothermenu(self, ctx):
        """Creates an other menu"""
        config = {}

        try:
            await ctx.send('What is the other menu message?')
            om = await self.bot.wait_for('message', check=lambda x: ctx.message.channel == x.channel and ctx.message.author == x.author, timeout=300)
            config['ocontent'] = om.content

            await ctx.send('How many options are available?')
            om = await self.bot.wait_for('message', check=lambda x: ctx.message.channel == x.channel and ctx.message.author == x.author and x.content.isdigit(), timeout=300)
            options_len = int(om.content)
            config['ooptions'] = {}

            for _ in range(options_len):
                await ctx.send('What is the option emoji?')
                while True:
                    om = await self.bot.wait_for('message', check=lambda x: ctx.message.channel == x.channel and ctx.message.author == x.author, timeout=300)
                    try:
                        await om.add_reaction(om.content)
                    except discord.HTTPException:
                        await ctx.send('Invalid emoji. Send another.')
                    else:
                        emoji = om.content
                        break

                await ctx.send('What is the option command? (e.g. `reply Transferring && move 1238343847384`)')
                om = await self.bot.wait_for('message', check=lambda x: ctx.message.channel == x.channel and ctx.message.author == x.author, timeout=300)
                config['ooptions'][emoji] = om.content
        except asyncio.TimeoutError:
            await ctx.send('Timeout. Re-run the command to create a menu.')
        else:
            await self.db.find_one_and_update({'_id': 'config'}, {'$set': config}, upsert=True)
            await ctx.send('Success')

    @commands.command()
    @checks.has_permissions(PermissionLevel.ADMIN)
    async def setotheremoji(self, ctx, *emojis: discord.Emoji):
        """
        Set other emoji for menu.
        **Usage**:
        [p]setemoji \N{WHITE HEAVY CHECK MARK} \N{CROSS MARK}
        [p]se (custom emojis)
        """
        await self.db.find_one_and_update(
            {"_id": "config"},
            {"$set": {"reaction-emojis": {"emojis": [i.id for i in emojis]}}},
            upsert=True,
        )
        embed = discord.Embed(title=f"Set emojis.", color=0x4DFF73)
        embed.set_author(name="Success!")
        embed.set_footer(text="Task succeeded successfully.")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Menu(bot))
