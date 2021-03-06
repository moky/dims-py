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
    Web Server Config
    ~~~~~~~~~~~~~~~~~

    Configuration for WWW
"""

from typing import Union
from flask import Flask, Response

from dimp import Address

from etc.cfg_init import *


"""
    Server Config
    ~~~~~~~~~~~~~
"""
WWW_HOST = '0.0.0.0'
WWW_PORT = 9395

# DB_PATH = '/var/dim/dwitter'  # test
DB_PATH = '/data/dwitter'

BASE_URL = '/'


"""
    Data Path
    ~~~~~~~~~
"""


def users_path() -> str:
    return '%s/users' % DB_PATH


def usr_path(address: Union[str, Address]) -> str:
    return '%s/%s' % (users_path(), address)


def msg_path(signature: str) -> str:
    filename = msg_filename(signature=signature)
    return '%s/messages/%s.msg' % (DB_PATH, filename)


def msg_filename(signature: str) -> str:
    start = 0
    length = len(signature)
    while length > 16:
        start += 4
        length -= 4
    if start > 0:
        filename = signature[start:]
    else:
        filename = signature
    return filename.replace('+', '-').replace('/', '_').replace('=', '')


"""
    Web URL
    ~~~~~~~
    
"""


def usr_url(identifier: ID) -> str:
    return '%schannel/%s' % (BASE_URL, identifier.address)


def msg_url(signature: str) -> str:
    filename = msg_filename(signature=signature)
    return '%smessage/%s' % (BASE_URL, filename)


def respond_xml(xml: str) -> Response:
    res = Response(response=xml, status=200, mimetype='application/xml')
    res.headers['Content-Type'] = 'application/xml; charset=UTF-8'
    res.headers['Access-Control-Allow-Origin'] = '*'
    return res


def respond_json(js: str) -> Response:
    res = Response(response=js, status=200, mimetype='application/json')
    res.headers['Content-Type'] = 'application/json; charset=UTF-8'
    res.headers['Access-Control-Allow-Origin'] = '*'
    return res


def respond_js(js: str) -> Response:
    res = Response(response=js, status=200, mimetype='application/javascript')
    res.headers['Content-Type'] = 'application/javascript; charset=UTF-8'
    res.headers['Access-Control-Allow-Origin'] = '*'
    return res


Log.info('======== configuration OK!')

app = Flask(__name__)
