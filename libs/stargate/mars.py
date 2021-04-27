# -*- coding: utf-8 -*-
#
#   Star Gate: Interfaces for network connection
#
#                                Written in 2021 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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

import time
import weakref
from typing import Optional

from tcp import Connection

from .protocol import NetMsg, NetMsgHead

from .base import Gate, StarShip, ShipDelegate
from .dock import Docker


def seq_to_sn(seq: int) -> bytes:
    return seq.to_bytes(length=4, byteorder='big')


class MarsShip(StarShip):
    """ Star Ship with Mars Package """

    def __init__(self, package: NetMsg, priority: int = 0, delegate: Optional[ShipDelegate] = None):
        super().__init__()
        self.__package = package
        self.__priority = priority
        # retry
        self.__timestamp = 0
        self.__retries = 0
        # callback
        if delegate is None:
            self.__delegate = None
        else:
            self.__delegate = weakref.ref(delegate)

    # Override
    @property
    def delegate(self) -> Optional[ShipDelegate]:
        """ Get request handler """
        if self.__delegate is not None:
            return self.__delegate()

    # Override
    @property
    def priority(self) -> int:
        return self.__priority

    # Override
    @property
    def time(self) -> int:
        return self.__timestamp

    # Override
    @property
    def retries(self) -> int:
        return self.__retries

    # Override
    def update(self):
        self.__timestamp = int(time.time())
        self.__retries += 1
        return self

    @property
    def package(self) -> NetMsg:
        """ Get request will be sent to remote star """
        return self.__package

    # Override
    @property
    def sn(self) -> bytes:
        return seq_to_sn(seq=self.package.head.seq)

    # Override
    @property
    def payload(self) -> bytes:
        return self.package.body


class MarsDocker(Docker):
    """ Docker for Mars packages """

    def __init__(self, gate: Gate):
        super().__init__(gate=gate)
        # time for checking heartbeat
        self.__heartbeat_expired = int(time.time())

    @classmethod
    def parse_head(cls, buffer: bytes) -> Optional[NetMsgHead]:
        head = NetMsgHead.parse(data=buffer)
        if head is not None:
            if head.version != 200:
                return None
            if head.cmd not in [NetMsgHead.SEND_MSG, NetMsgHead.NOOP, NetMsgHead.PUSH_MESSAGE]:
                return None
            return head

    @classmethod
    def check(cls, connection: Connection) -> bool:
        # 1. check received data
        buffer = connection.received()
        if buffer is not None:
            return cls.parse_head(buffer=buffer) is not None

    # Override
    def send(self, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> bool:
        req_head = NetMsgHead.new(cmd=NetMsgHead.PUSH_MESSAGE, body_len=len(payload))
        req_pack = NetMsg.new(head=req_head, body=payload)
        req_ship = MarsShip(package=req_pack, priority=priority, delegate=delegate)
        return self.dock.put(ship=req_ship)

    def __send_package(self, pack: NetMsg) -> int:
        conn = self.connection
        if conn is None:
            # connection lost
            return -1
        return conn.send(data=pack.data)

    def __receive_package(self) -> Optional[NetMsg]:
        conn = self.connection
        if conn is None:
            # connection lost
            return None
        # 1. check received data
        data = conn.received()
        if data is None:
            # received nothing
            return None
        data_len = len(data)
        head = self.parse_head(buffer=data)
        if head is None:
            # not a MTP package?
            if data_len < NetMsgHead.MIN_HEAD_LEN:
                # wait for more data
                return None
            pos = data.find(NetMsgHead.MAGIC_CODE, NetMsgHead.MAGIC_CODE_OFFSET+1)
            if pos > NetMsgHead.MAGIC_CODE_OFFSET:
                # found next head, skip data before it
                conn.receive(length=pos-NetMsgHead.MAGIC_CODE_OFFSET)
            else:
                # skip the whole data
                conn.receive(length=data_len)
            # take it as NOOP
            head = NetMsgHead.new(cmd=NetMsgHead.NOOP)
            return NetMsg.new(head=head)
        # 2. receive data with 'head.length + body.length'
        body_len = head.body_length
        if body_len < 0:
            # should not happen
            body_len = data_len - head.length
        pack_len = head.length + body_len
        if pack_len > data_len:
            # waiting for more data
            return None
        # receive package
        data = conn.receive(length=pack_len)
        if body_len > 0:
            body = data[head.length:]
        else:
            body = None
        return NetMsg(data=data, head=head, body=body)

    # Override
    def _handle_income(self) -> bool:
        income = self.__receive_package()
        if income is None:
            # no more package now
            return False
        head = income.head
        body = income.body
        # check data cmd
        cmd = head.cmd
        if cmd == NetMsgHead.NOOP:
            priority = StarShip.SLOWER
        else:
            priority = StarShip.NORMAL
        # check body
        if body is None:
            res = b''
        elif body == ping_body:
            # PING -> PONG
            res = pong_body
        elif body == pong_body:
            # just ignore
            return True
        elif body == noop_body:
            # NOOP -> NOOP
            res = noop_body
        else:
            res = None
            delegate = self.delegate
            if delegate is not None and len(body) > 0:
                # process received data
                res = delegate.gate_received(gate=self.gate, payload=body)
            if res is None:
                res = b''
        # respond with same cmd & seq
        res_head = NetMsgHead.new(cmd=cmd, seq=head.seq, body_len=len(res))
        res_pack = NetMsg.new(head=res_head, body=res)
        res_ship = MarsShip(package=res_pack, priority=priority)
        self.dock.put(ship=res_ship)
        return True

    # Override
    def _handle_outgo(self) -> bool:
        # get next new task (time == 0)
        ship = self.dock.pop()
        if ship is None:
            # no more new task now, get any expired task
            ship = self.dock.any()
            if ship is None:
                # no task expired now
                return False
            elif ship.expired:
                # remove an expired task
                delegate = ship.delegate
                if delegate is not None:
                    error = TimeoutError('Request timeout')
                    delegate.ship_sent(ship=ship, payload=ship.payload, error=error)
                return True
        assert isinstance(ship, MarsShip), 'outgo ship error: %s' % ship
        outgo = ship.package
        # check data type
        # if outgo.head.cmd == NetMsgHead.PUSH_MESSAGE:
        #     # put back for response
        #     self.dock.put(ship=ship)
        # send out request data
        res = self.__send_package(pack=outgo)
        if res != outgo.length:
            # callback for sent failed
            delegate = ship.delegate
            if delegate is not None:
                error = ConnectionError('Socket error')
                delegate.ship_sent(ship=ship, payload=ship.payload, error=error)
        return True

    # Override
    def _handle_heartbeat(self):
        pass


#
#  const
#

ping_body = b'PING'
pong_body = b'PONG'
noop_body = b'NOOP'