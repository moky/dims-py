# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==============================================================================

import os
import time
from typing import Optional, Dict

from dimp import NetworkType, ID, ReliableMessage
from dimsdk import LoginCommand

from .storage import Storage


class LoginTable(Storage):

    def __init__(self):
        super().__init__()
        # memory caches
        self.__commands: Dict[ID, LoginCommand] = {}
        self.__messages: Dict[ID, ReliableMessage] = {}
        self.__empty = {'desc': 'just to avoid loading non-exists file again'}

    """
        Login info for Users
        ~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/public/{ADDRESS}/login.js'
    """
    def __path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'public', str(identifier.address), 'login.js')

    def save_login(self, cmd: LoginCommand, msg: ReliableMessage) -> bool:
        sender = msg.sender
        if cmd.identifier != sender:
            self.error('sender error: %s, %s' % (sender, cmd))
            return False
        elif sender.type == NetworkType.STATION:
            self.error('a station should not "login" to another station: %s' % cmd)
            return False
        # check last login time
        old = self.login_command(identifier=sender)
        if old is not None:
            old_time = old.time
            if old_time is None:
                old_time = 0
            new_time = cmd.time
            if new_time is None:
                new_time = 0
            if new_time <= old_time and old_time > 0:
                self.error('expired command, drop it: %s' % cmd)
                return False
        # store into memory cache
        self.__commands[sender] = cmd
        self.__messages[sender] = msg
        # store into local storage
        path = self.__path(identifier=sender)
        self.info('Saving login into: %s' % path)
        dictionary = {'cmd': cmd.dictionary, 'msg': msg.dictionary}
        return self.write_json(container=dictionary, path=path)

    def login_command(self, identifier: ID) -> Optional[LoginCommand]:
        cmd, _ = self.login_info(identifier=identifier)
        return cmd

    def login_message(self, identifier: ID) -> Optional[ReliableMessage]:
        _, msg = self.login_info(identifier=identifier)
        return msg

    def login_info(self, identifier: ID) -> (Optional[LoginCommand], Optional[ReliableMessage]):
        # 1. try from memory cache
        cmd = self.__commands.get(identifier)
        msg = self.__messages.get(identifier)
        if cmd is None or msg is None:
            # 2. try from local storage
            cmd, msg = self.__load_login(identifier=identifier)
            if cmd is None:
                cmd = self.__empty
            if msg is None:
                msg = self.__empty
            # 3. store into memory cache
            self.__commands[identifier] = cmd
            self.__messages[identifier] = msg
        if cmd is self.__empty:
            cmd = None
        else:
            login_time = cmd.time
            if login_time is None:
                login_time = 0
            days = (time.time() - login_time) / 3600 / 24
            if days > 7:
                self.error('login too long ago: %d days, %s' % (days, cmd.identifier))
                return None, None
        if msg is self.__empty:
            msg = None
        return cmd, msg

    def __load_login(self, identifier: ID) -> (Optional[LoginCommand], Optional[ReliableMessage]):
        if identifier.type == NetworkType.STATION:
            self.error('a station would not "login" to another station: %s' % identifier)
            return None, None
        path = self.__path(identifier=identifier)
        self.info('Loading login from: %s' % path)
        dictionary = self.read_json(path=path)
        if dictionary is None:
            return None, None
        cmd = dictionary.get('cmd')
        msg = dictionary.get('msg')
        if cmd is not None:
            cmd = LoginCommand(cmd)
        if msg is not None:
            msg = ReliableMessage.parse(msg=msg)
        return cmd, msg
