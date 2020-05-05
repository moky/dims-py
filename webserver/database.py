# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2020 Albert Moky
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
    Database module
    ~~~~~~~~~~~~~~~

"""

import os
from typing import Optional

from dimp import ID
from dimp import ReliableMessage
from dimsdk import Facebook

from libs.common import Storage

from webserver.config import usr_path, msg_path, usr_url
from webserver.config import recommended_users


def number_string(number: int):
    string = '%010d' % number
    return string[:3] + '-' + string[3:-4] + '-' + string[-4:]


class UserTable(Storage):

    def __init__(self, facebook: Facebook):
        super().__init__()
        self.facebook = facebook

    def __load_messages(self, address: str) -> list:
        path = usr_path(address=address)
        path = os.path.join(path, 'messages.txt')
        text = self.read_text(path=path)
        if text is None:
            return []
        else:
            return text.splitlines()

    def user_info(self, identifier: ID) -> Optional[dict]:
        identifier = self.facebook.identifier(identifier)
        if identifier is None:
            return None
        user = self.facebook.user(identifier)
        name = user.name
        number = number_string(user.number)
        url = usr_url(identifier=identifier)
        desc = user.profile
        return {
            'ID': identifier,
            'name': name,
            'number': number,
            'link': url,
            'desc': desc,
        }

    def users(self) -> list:
        array = []
        id_list = recommended_users
        for item in id_list:
            identifier = self.facebook.identifier(item)
            info = self.user_info(identifier=identifier)
            if info is None:
                continue
            array.append(info)
        return array

    def messages(self, identifier: ID) -> list:
        address = str(identifier.address)
        return self.__load_messages(address=address)


class MessageTable(Storage):

    def __init__(self, facebook: Facebook):
        super().__init__()
        self.facebook = facebook

    def __load_message(self, signature: str) -> Optional[ReliableMessage]:
        path = msg_path(signature=signature)
        msg = self.read_json(path=path)
        if msg is not None:
            return ReliableMessage(msg)

    def load(self, signature: str) -> Optional[ReliableMessage]:
        return self.__load_message(signature=signature)

    def save(self, msg: ReliableMessage) -> bool:
        signature = msg['signature']
        timestamp = msg.envelope.time
        path = msg_path(signature=signature)
        if not self.write_json(container=msg, path=path):
            return False
        # append msg info to user's messages list
        sender = self.facebook.identifier(msg.envelope.sender)
        path = usr_path(address=sender.address)
        path = os.path.join(path, 'messages.txt')
        text = '%s,%d\n' % (signature, timestamp)
        return self.append_text(text=text, path=path)
