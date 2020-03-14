#! /usr/bin/env python3
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

"""
    Group bot: 'assistant'
    ~~~~~~~~~~~~~~~~~~~~~~

    Bot for collecting and responding group member list
"""

import sys
import os
from typing import Optional

from dimp import ID
from dimp import Content, ForwardContent
from dimp import InstantMessage, ReliableMessage
from dimsdk import ReceiptCommand

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
sys.path.append(os.path.join(rootPath, 'libs'))

from libs.common import Storage

from libs.client import ClientMessenger

from robots.config import g_facebook, g_keystore, g_station, g_database
from robots.config import load_user, create_client
from robots.config import chat_bot, assistant_id


class GroupKeyCache(Storage):

    def __init__(self):
        super().__init__()
        self.__cache = {}  # group => (sender => (member => key str))

    # path: '/data/.dim/protected/{GROUP_ADDRESS}/group-keys-{SENDER_ADDRESS).json'
    @staticmethod
    def __path(group: ID, sender: ID) -> str:
        filename = 'group-keys-%s.js' % str(sender.address)
        return os.path.join(g_database.base_dir, 'protected', str(group.address), filename)

    def __load_keys(self, sender: ID, group: ID) -> dict:
        path = self.__path(group=group, sender=sender)
        self.info('Loading group keys from: %s' % path)
        return self.read_json(path=path)

    def __save_keys(self, keys: dict, sender: ID, group: ID) -> bool:
        path = self.__path(group=group, sender=sender)
        self.info('Saving group keys into: %s' % path)
        return self.write_json(container=keys, path=path)

    def update_keys(self, keys: dict, sender: ID, group: ID):
        table = self.__cache.get(group)
        if table is None:
            # no keys for this group yet
            table = {}
            self.__cache[group] = table
        key_map = table.get(sender)
        if key_map is None:
            # no keys from this sender yet
            table[sender] = keys
            dirty = True
        else:
            dirty = False
            # update key map with member
            for (member, key) in keys.items():
                if key is None or len(key) == 0:
                    # empty key
                    continue
                key_map[member] = key
                dirty = True
            keys = key_map
        if dirty:
            self.__save_keys(keys=keys, sender=sender, group=group)

    def get_keys(self, sender: ID, group: ID) -> dict:
        # get table for all members in this group
        table = self.__cache.get(group)
        if table is None:
            # try to load keys
            keys = self.__load_keys(sender=sender, group=group)
            if keys is None:
                keys = {}
            # cache keys
            table = {sender: keys}
            self.__cache[group] = table
        else:
            # get keys from the sender
            keys = table.get(sender)
            if keys is None:
                # try to load keys
                keys = self.__load_keys(sender=sender, group=group)
                if keys is None:
                    keys = {}
                # cache keys
                table[sender] = keys
        return keys

    def get_key(self, sender: ID, member: ID, group: ID) -> Optional[str]:
        key_map = self.get_keys(sender=sender, group=group)
        assert key_map is not None, 'key map error: %s -> %s' % (sender, group)
        key = key_map.get(member)
        if key is None:
            self.error('failed to get key for: %s (%s => %s)' % (member, sender, group))
        return key


class AssistantMessenger(ClientMessenger):

    def __init__(self):
        super().__init__()
        self.__key_cache = GroupKeyCache()

    # Override
    def process_reliable(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        receiver = g_facebook.identifier(string=msg.envelope.receiver)
        if receiver.is_group:
            # process group message
            return self.__process_group_message(msg=msg)
        # try to decrypt and process message
        return super().process_reliable(msg=msg)

    def __process_group_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        s_msg = self.verify_message(msg=msg)
        if s_msg is None:
            # signature error?
            return None
        sender = g_facebook.identifier(msg.envelope.sender)
        receiver = g_facebook.identifier(msg.envelope.receiver)
        if not g_facebook.exists_member(member=sender, group=receiver):
            if not g_facebook.is_owner(member=sender, group=receiver):
                # not allow
                return None
        # check 'keys'
        keys = msg.get('keys')
        if keys is None:
            # keys not found, split with group members
            members = g_facebook.members(receiver)
            if members is None:
                raise LookupError('failed to get group members: %s' % receiver)
        else:
            # update key map
            self.__key_cache.update_keys(keys=keys, sender=sender, group=receiver)
            # use IDs in 'keys' as members list
            members = list(keys.keys())
        # split and forward group message
        res = self.__split_group_message(msg=msg, members=members)
        # pack response
        if res is not None:
            sender = g_facebook.current_user.identifier
            receiver = msg.envelope.sender
            i_msg = InstantMessage.new(content=res, sender=sender, receiver=receiver)
            s_msg = self.encrypt_message(msg=i_msg)
            return self.sign_message(msg=s_msg)

    def __split_group_message(self, msg: ReliableMessage, members: list) -> Optional[Content]:
        """ Split group message for each member """
        messages = msg.split(members=members)
        success_list = []
        failed_list = []
        for item in messages:
            if self.__forward_group_message(msg=item):
                success_list.append(item.envelope.receiver)
            else:
                failed_list.append(item.envelope.receiver)
        response = ReceiptCommand.new(message='Message split and delivering')
        if len(success_list) > 0:
            response['success'] = success_list
        if len(failed_list) > 0:
            response['failed'] = failed_list
        return response

    def __forward_group_message(self, msg: ReliableMessage) -> bool:
        receiver = g_facebook.identifier(msg.envelope.receiver)
        if msg.get('key') is None:
            # get key from cache
            sender = g_facebook.identifier(msg.envelope.sender)
            group = g_facebook.identifier(msg.envelope.group)
            msg['key'] = self.__key_cache.get_key(sender=sender, member=receiver, group=group)
        forward = ForwardContent.new(message=msg)
        return self.send_content(content=forward, receiver=receiver)


"""
    Messenger for Group Assistant robot
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
g_messenger = AssistantMessenger()
g_messenger.barrack = g_facebook
g_messenger.key_cache = g_keystore

# chat bot
g_messenger.context['bots'] = [chat_bot('tuling'), chat_bot('xiaoi')]
# current station
g_messenger.set_context('station', g_station)

g_facebook.messenger = g_messenger


if __name__ == '__main__':

    user = load_user(assistant_id)
    client = create_client(user=user, messenger=g_messenger)
