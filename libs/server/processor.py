# -*- coding: utf-8 -*-
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

"""
    Server extensions for MessageProcessor
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from typing import Optional

from dimp import SecureMessage, ReliableMessage

from ..common import msg_traced, is_broadcast_message
from ..common import CommonProcessor
from .messenger import ServerMessenger


class ServerProcessor(CommonProcessor):

    @property
    def messenger(self) -> ServerMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, ServerMessenger), 'messenger error: %s' % transceiver
        return transceiver

    # Override
    def process_reliable_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        # check traces
        station = self.messenger.dispatcher.station
        if msg_traced(msg=msg, node=station, append=True) and is_broadcast_message(msg=msg):
            self.error('ignore traced broadcast msg: %s in %s' % (station, msg.get('traces')))
            return None
        receiver = msg.receiver
        if receiver.is_group:
            # verify signature
            s_msg = self.messenger.verify_message(msg=msg)
            if s_msg is None:
                # signature error?
                return None
            # deliver group message
            res = self.messenger.deliver_message(msg=msg)
            if receiver.is_broadcast:
                # if this is a broadcast, deliver it, send back the response
                # and continue to process it with the station.
                # because this station is also a recipient too.
                if res is not None:
                    self.messenger.send_message(msg=res)
            else:
                # or, this is is an ordinary group message,
                # just deliver it to the group assistant
                # and return the response to the sender.
                return res
        # call super to process message
        res = super().process_reliable_message(msg=msg)
        if res is not None:
            group = msg.group
            if (receiver.is_broadcast and receiver.is_user) or (group is not None and group.is_broadcast):
                # if this message sent to 'station@anywhere', or with group ID 'station@everywhere',
                # it means the client doesn't have the station's meta or visa (e.g.: first handshaking),
                # so respond them as message attachments.
                user = self.facebook.user(identifier=res.sender)
                res.meta = user.meta
                res.visa = user.visa
            return res

    # Override
    def process_secure_message(self, msg: SecureMessage, r_msg: ReliableMessage) -> Optional[SecureMessage]:
        try:
            return super().process_secure_message(msg=msg, r_msg=r_msg)
        except LookupError as error:
            if str(error).startswith('receiver error'):
                # not mine? deliver it
                return self.messenger.deliver_message(msg=r_msg)
            else:
                raise error
