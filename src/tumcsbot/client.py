#!/usr/bin/env python3

# See LICENSE file for copyright and license details.
# TUM CS Bot - https://github.com/ro-i/tumcsbot

import logging
import typing

from typing import Any, Dict, Iterable, List, Optional, Tuple
from zulip import Client as ZulipClient


'''
Adapt Zulip's Client class to our needs :-)
'''


class Client(ZulipClient):
    def register(
        self,
        event_types: Optional[Iterable[str]] = None,
        narrow: Optional[List[List[str]]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        '''
        Override the parent method in order to register events of all
        public streams.
        See https://zulip.com/api/register-queue#parameter-all_public_streams
        '''
        logging.debug("Client.register - event_types: {}, narrow: {}".format(
            str(event_types), str(narrow)
        ))
        return super().register(
            event_types, narrow, all_public_streams = True,
        )
