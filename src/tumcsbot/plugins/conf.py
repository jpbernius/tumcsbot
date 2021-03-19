#!/usr/bin/env python3

# See LICENSE file for copyright and license details.
# TUM CS Bot - https://github.com/ro-i/tumcsbot

import logging

from inspect import cleandoc
from typing import Any, Dict, Iterable, Optional, Tuple, Union

from tumcsbot.lib import CommandParser, DB, Response
from tumcsbot.plugin import CommandPlugin, PluginContext


class Conf(CommandPlugin):
    plugin_name = 'conf'
    syntax = cleandoc(
        """
        conf set <key> <value>
          or conf remove <key>
          or conf list
        """
    )
    description = cleandoc(
        """
        Set/get/remove bot configuration variables.
        [administrator rights needed]
        """
    )
    _list_sql: str = 'select * from Conf'
    _remove_sql: str = 'delete from Conf where Key = ?'
    _update_sql: str = 'replace into Conf values (?,?)'

    def __init__(self, plugin_context: PluginContext, **kwargs: Any) -> None:
        super().__init__(plugin_context)
        self._db = DB()
        self._db.checkout_table('Conf', '(Key text primary key, Value text not null)')
        self.command_parser: CommandParser = CommandParser()
        self.command_parser.add_subcommand('list')
        self.command_parser.add_subcommand('set', {'key': str, 'value': str})
        self.command_parser.add_subcommand('remove', {'key': str})

    def handle_message(
        self,
        message: Dict[str, Any],
        **kwargs: Any
    ) -> Union[Response, Iterable[Response]]:
        result: Optional[Tuple[str, CommandParser.Args]]

        if not self.client.get_user_by_id(message['sender_id'])['user']['is_admin']:
            return Response.admin_err(message)

        result = self.command_parser.parse(message['command'])
        if result is None:
            return Response.command_not_found(message)
        command, args = result

        if command == 'list':
            response: str = 'Key | Value\n ---- | ----'
            for key, value in self._db.execute(self._list_sql):
                response += f'\n{key} | {value}'
            return Response.build_message(message, response)
        elif command == 'remove':
            self._db.execute(self._remove_sql, args.key, commit = True)
            return Response.ok(message)
        elif command == 'set':
            try:
                self._db.execute(self._update_sql, args.key, args.value, commit = True)
            except Exception as e:
                logging.exception(e)
                return Response.build_message(message, 'Failed: %s' % str(e))
            return Response.ok(message)

        return Response.command_not_found(message)