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
    Command Processing Module
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Processors for commands
"""

from .cpu import CPU, processor_classes

from .handshake import HandshakeCommandProcessor
from .meta import MetaCommandProcessor
from .profile import ProfileCommandProcessor

from .login import LoginCommandProcessor
from .search import SearchCommandProcessor
from .users import UsersCommandProcessor
from .contacts import ContactsCommandProcessor
from .mute import MuteCommandProcessor
from .block import BlockCommandProcessor

from .report import ReportCommandProcessor

#
#  register processors
#
processor_classes['handshake'] = HandshakeCommandProcessor
processor_classes['meta'] = MetaCommandProcessor
processor_classes['profile'] = ProfileCommandProcessor

processor_classes['login'] = LoginCommandProcessor
processor_classes['search'] = SearchCommandProcessor
processor_classes['users'] = UsersCommandProcessor
processor_classes['contacts'] = ContactsCommandProcessor
processor_classes['mute'] = MuteCommandProcessor
processor_classes['block'] = BlockCommandProcessor

processor_classes['report'] = ReportCommandProcessor
processor_classes['broadcast'] = ReportCommandProcessor

__all__ = [
    'CPU',
]
