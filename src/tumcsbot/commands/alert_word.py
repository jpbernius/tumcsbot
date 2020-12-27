#!/usr/bin/env python3

# See LICENSE file for copyright and license details.
# TUM CS Bot - https://github.com/ro-i/tumcsbot

"""Manage reactions on certain words or phrases with emojis.

Use the Zulip facility, see https://zulip.com/help/add-an-alert-word.
Provide also an interactive command so administrators are able to
change the alert words and specify the emojis to use for the reactions.
"""

import re

from inspect import cleandoc
from typing import Any, Dict, List, Match, Optional, Pattern, Sequence, Tuple, Union

import tumcsbot.command as command
import tumcsbot.lib as lib

from tumcsbot.client import Client


class Command(command.CommandInteractive):
    name: str = 'alert_word'
    syntax: str = ('alert_word add <alert phrase>\\n<emoji> '
                   'or alert_word remove <alert phrase> '
                   'or alert_word list')
    description: str = cleandoc(
        """
        Add an alert word / phrase together with the emoji the bot \
        should use to react on messages containing the corresponding \
        alert phrase. 
        Internally, \
        [this Zulip service](https://zulip.com/help/add-an-alert-word) \
        is used.
        [administrator rights needed]
        """
    )
    _search_sql: str = 'select a.Emoji from Alerts a where a.Phrase = ? collate nocase'
    _update_sql: str = 'update Alerts set Emoji = ? where Phrase = ? collate nocase'
    _insert_sql: str = 'insert into Alerts values (?,?)'
    _remove_sql: str = 'delete from Alerts where Phrase = ? collate nocase'
    _list_sql: str = 'select * from Alerts'

    def __init__(self, **kwargs: Any) -> None:
        self._pattern = re.compile(
            r'\s*alert_word\s*(?:add *.+\n.+|remove *.+|list\s*)', re.I
        )
        self._pattern_add: Pattern[str] = re.compile(
            r'\s*alert_word\s*(add) *(.+)\n(.+)', re.I
        )
        self._pattern_remove: Pattern[str] = re.compile(
            r'\s*alert_word\s*(remove) *(.+)', re.I
        )
        self._pattern_list: Pattern[str] = re.compile(
            r'\s*alert_word\s*(list)\s*', re.I
        )
        # get own database connection
        self._db = lib.DB()
        # check for database table
        self._db.checkout_table(
            table = 'Alerts',
            schema = '(Phrase varchar, Emoji varchar)'
        )

    def handle_message(
        self,
        client: Client,
        message: Dict[str, Any],
        **kwargs: Any
    ) -> Union[lib.Response, List[lib.Response]]:
        result_sql: List[Tuple[Any, ...]]

        if not client.get_user_by_id(message['sender_id'])['user']['is_admin']:
            return lib.Response.admin_err(message)

        # Get command and parameters.
        match: Optional[Match[str]] = (
            self._pattern_add.match(message['command'])
            or self._pattern_remove.match(message['command'])
            or self._pattern_list.match(message['command'])
        )

        if not match:
            return lib.Response.command_not_found(message)
        args: Union[Sequence[str], Any] = match.groups()

        # Receive the alert words from the server storage.
        result = client.get_alert_words()
        if result['result'] != 'success':
            return lib.Response.error(message)
        alert_phrases: List[str] = result['alert_words']

        if args[0] == 'list':
            result_sql = self._db.execute(Command._list_sql)
            response: str = 'Alert word or phrase | Emoji\n---- | ----'
            for (phrase, emoji) in result_sql:
                if phrase not in alert_phrases:
                    response += '\n~~{0}~~ | {1} :{1}:'.format(phrase, emoji)
                else:
                    response += '\n{0} | {1} :{1}:'.format(phrase, emoji)
            # Get all phrases stored in the database.
            db_phrases: List[str] = [ phrase for (phrase, emoji) in result_sql ]
            # Append alert words without emoji binding.
            for phrase in alert_phrases:
                if phrase not in db_phrases:
                    response += '\n{} | -'.format(phrase)
            return lib.Response.build_message(message, response)

        # search for identifier in database table
        result_sql = self._db.execute(Command._search_sql, args[1].strip())

        # Get alert phrase for all subsequent commands.
        alert_phrase: str = args[1].strip()

        if args[0] == 'add':
            emoji = args[2].strip()
            # Add alert word to server storage.
            if client.add_alert_words([alert_phrase])['result'] != 'success':
                return lib.Response.error(message)
            # Add binding to database or update it.
            if result_sql:
                self._db.execute(
                    Command._update_sql, emoji, alert_phrase, commit = True
                )
            else:
                self._db.execute(
                    Command._insert_sql, alert_phrase, emoji, commit = True
                )
        elif args[0] == 'remove':
            if not result_sql:
                return lib.Response.no(message)
            if alert_phrase in alert_phrases:
                if client.remove_alert_words([alert_phrase])['result'] != 'success':
                    return lib.Response.error(message)
            self._db.execute(Command._remove_sql, alert_phrase, commit = True)

        return lib.Response.ok(message)