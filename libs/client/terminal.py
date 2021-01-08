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
    Terminal
    ~~~~~~~~

    Local User
"""

from dimp import ID, EVERYONE
from dimp import Envelope, InstantMessage
from dimp import Content, Command
from dimsdk import HandshakeCommand, LoginCommand
from dimsdk import Station, CompletionHandler

from libs.common import CommonFacebook

from .connection import Connection
from .cpu import HandshakeDelegate

from .messenger import ClientMessenger


class Terminal(HandshakeDelegate):

    def __init__(self):
        super().__init__()
        self.__messenger: ClientMessenger = None
        # station connection
        self.station: Station = None
        self.session: str = None
        self.connection: Connection = None

    def __del__(self):
        self.disconnect()

    def info(self, msg: str):
        print('\r##### %s > %s' % (self.facebook.current_user, msg))

    def error(self, msg: str):
        print('\r!!!!! %s > %s' % (self.facebook.current_user, msg))

    def disconnect(self) -> bool:
        if self.connection:
            # if self.messenger.delegate == self.connection:
            #     self.messenger.delegate = None
            self.connection.disconnect()
            self.connection = None
            return True

    def connect(self, station: Station) -> bool:
        conn = Connection()
        conn.connect(server=station)
        mess = self.messenger
        mess.set_context('station', station)
        # delegate for processing received data package
        conn.messenger = mess
        # delegate for sending out data package
        if mess.delegate is None:
            mess.delegate = conn
        self.connection = conn
        self.station = station
        return True

    @property
    def messenger(self) -> ClientMessenger:
        return self.__messenger

    @messenger.setter
    def messenger(self, value: ClientMessenger):
        self.__messenger = value

    @property
    def facebook(self) -> CommonFacebook:
        return self.messenger.facebook

    def send_command(self, cmd: Command) -> bool:
        """ Send command to current station """
        return self.messenger.send_content(sender=None, receiver=self.station.identifier, content=cmd)

    def broadcast_content(self, content: Content, receiver: ID) -> bool:
        content.group = EVERYONE
        return self.messenger.send_content(sender=None, receiver=receiver, content=content)

    def handshake(self):
        user = self.facebook.current_user
        assert user is not None, 'current user not set yet'
        server = self.messenger.station
        cmd = HandshakeCommand.start()
        env = Envelope.create(sender=user.identifier, receiver=server.identifier)
        msg = InstantMessage.create(head=env, body=cmd)
        msg = self.messenger.sign_message(self.messenger.encrypt_message(msg=msg))
        # carry meta for first handshake
        msg.meta = user.meta
        data = self.messenger.serialize_message(msg=msg)
        # send out directly
        handler: CompletionHandler = None
        self.messenger.delegate.send_package(data=data, handler=handler)

    #
    #   HandshakeDelegate (Client)
    #
    def handshake_success(self):
        user = self.facebook.current_user
        self.info('handshake success: %s' % user.identifier)
        if isinstance(user, Station):
            return None
        # post current profile to station
        # post contacts(encrypted) to station
        # broadcast login command
        login = LoginCommand(identifier=user.identifier)
        login.agent = 'DIMP/0.4 (Server; Linux; en-US) DIMCoreKit/0.9 (Terminal) DIM-by-GSP/1.0'
        login.station = self.station
        self.messenger.broadcast_content(content=login)
