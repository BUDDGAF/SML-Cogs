# -*- coding: utf-8 -*-

"""
The MIT License (MIT)

Copyright (c) 2017 SML

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from .utils.dataIO import dataIO
from __main__ import send_cmd_help
from cogs.utils.chat_formatting import pagify
from discord.ext import commands
from discord.ext.commands import Context
from random import choice
import datetime
import discord
import os


CRDATA_PATH = "data/draftroyale/clashroyale.json"
SETTINGS_PATH = "data/draftroyale/draftroyale.json"


class Draft:
    """Clash Royale drafts."""

    def __init__(self, admin: discord.Member=None):
        """Constructor.

        Args:
          admin (discord.Member): administrator of the draft
        """

        self.admin = admin

class DraftRoyale:
    """Clash Royale drafting bot.

    This cog is written to facilitate draftin in Clash Royale.

    Types of drafts:
    - 4 players (10 cards)
    - 8 players (8 cards)
    - This system however will allow any number of players (2-8)
      with number of cards set to card count // players

    Bans:

    Some drafts have bans. For example, if graveyard is picked as a banned
    card, then no one can pick it.pick

    Drafting order:

    Most drafts are snake drafts. They go from first to last then backwards.
    The first and last player gets two picks in a row.
    1 2 3 4 4 3 2 1 1 2 3 4 etc.

    Required files:

    - data/clashroyale.json: card data
    - data/settings.json: technically not needed but good to
                          have a human-readable history log
    """

    def __init__(self, bot):
        """Constructor."""
        self.bot = bot
        self.crdata_path = CRDATA_PATH
        self.settings_path = SETTINGS_PATH

        self.crdata = dataIO.load_json(self.crdata_path)
        self.settings = dataIO.load_json(self.settings_path)

        # init card data
        self.cards = []
        self.cards_abbrev = {}

        self.min_players = 2
        self.max_players = 8

        self.active_draft = None
        # self.valid_answer = False

    def init_card_data(self):
        """Initialize card data and popularize acceptable abbreviations."""
        for card_key, card_value in self.crdata["Cards"].items():
            self.cards.append(card_key)
            self.cards_abbrev[card_key] = card_key

            if card_key.find('-'):
                self.cards_abbrev[card_key.replace('-', '')] = card_key

            aka_list = card_value["aka"]
            for aka in aka_list:
                self.cards_abbrev[aka] = card_key
                if aka.find('-'):
                    self.cards_abbrev[aka.replace('-', '')] = card_key

    def init(self):
        """Abort all operations."""
        # Stops the interaction loop
        # self.valid_answer = True
        # Get rid of active draft
        self.active_draft = None

    @commands.group(pass_context=True, no_pm=True)
    async def draft(self, ctx: Context):
        """Clash Royale Draft System.

        Full help
        !draft help
        """
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @draft.command(name="init", pass_context=True, no_pm=True)
    async def draft_init(self, ctx:Context):
        """Initialize a draft.

        The author who type this command will be designated as the
        owner / admin of the draft.
        """
        await self.bot.say("Draft Royale")

        self.init()

        if self.active_draft is not None:
            await self.bot.say("An active draft is going on. "
                               "Please finish the current draft "
                               "before starting another.")
            return

        admin = ctx.message.author

        await self.bot.say(f"**Draft Admin** set to {admin.display_name}.")

        self.active_draft = {
            "admin_id": admin.id,
            "players": []
        }

        id = datetime.datetime.utcnow().isoformat()

        if "drafts" not in self.settings:
            self.settings["drafts"] = {}
        self.settings["drafts"][id] = self.active_draft

        # Input: Number of players
        await self.bot.say(
            f"{admin.mention} How many players? "
            f"({self.min_players}-{self.max_players})")
        while True:
            answer = await self.bot.wait_for_message(
                timeout=30.0,
                author=ctx.message.author,
                channel=ctx.message.channel)
            # don’t do interactive prompts if draft was aborted
            if self.active_draft is not None:
                if answer is None:
                    await self.bot.say(f"{admin.mention} Draft aborted.")
                    self.init()
                    # await ctx.invoked_subcommand(self.draft_abort)
                    return
                elif not answer.content.isdigit():
                    await self.bot.say(f"{admin.mention} "
                                       f"You must enter a number.")
                elif int(answer.content) < self.min_players:
                    await self.bot.say(f"{admin.mention} "
                                       f"Number must be at least "
                                       f"{self.min_players}")
                elif int(answer.content) > self.max_players:
                    await self.bot.say(f"{admin.mention} "
                                       f"Number must be no more than "
                                       f"{self.max_players}")
                else:
                    break

            if answer is None:
                self.init()
                await self.bot.say("Timeout. Draft aborted")
                break

        await self.bot.say(f"Number of players: {answer.content}")
        self.active_draft["player_count"] = int(answer.content)

        # Input: Player Mentions

        self.save_settings()


    @draft.command(name="abort", pass_context=True, no_pm=True)
    async def draft_abort(self, ctx:Context):
        """Abort an active draft."""
        self.init()
        await self.bot.say("Draft Royale aborted.")



    def save_settings(self):
        """Save settings to disk."""
        dataIO.save_json(self.settings_path, self.settings)


def check_folder():
    """Check data folders exist. Create if necessary."""
    folders = ["data/draftroyale",
               "data/draftroyale/img",
               "data/draftroyale/img/cards"]
    for f in folders:
        if not os.path.exists(f):
            os.makedirs(f)

def check_files():
    """Check required data files exists."""
    defaults = {}
    f = SETTINGS_PATH
    if not dataIO.is_valid_json(f):
        dataIO.save_json(f, defaults)

def setup(bot):
    """Add cog to bot."""
    check_folder()
    check_files()
    n = DraftRoyale(bot)
    bot.add_cog(n)



