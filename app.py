# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import signal
import sys
from types import FrameType

from flask import Flask, request

from utils.logging import logger

import logging
import socket

from google.cloud import datastore

app = Flask(__name__)


import datetime



app = Flask(__name__)


def is_ipv6(addr):
    """Checks if a given address is an IPv6 address."""
    try:
        socket.inet_pton(socket.AF_INET6, addr)
        return True
    except socket.error:
        return False


# [START gae_flex_datastore_app]
@app.route('/')
def index():
    ds = datastore.Client()

    user_ip = request.remote_addr

    # Keep only the first two octets of the IP address.
    if is_ipv6(user_ip):
        user_ip = ':'.join(user_ip.split(':')[:2])
    else:
        user_ip = '.'.join(user_ip.split('.')[:2])

    entity = datastore.Entity(key=ds.key('visit'))
    # print(dir(entity))
    # entity.update({
    #     'user_ip': user_ip,
    #     'timestamp': datetime.datetime.now(tz=datetime.timezone.utc)
    # })

    # ds.put(entity)
    query = ds.query(kind='visit', order=('-timestamp',))

    results = []
    for x in query.fetch(limit=10):
        try:
            results.append('Time: {timestamp} Addr: {user_ip}'.format(**x))
        except KeyError:
            print("Error with result format, skipping entry.")

    output = 'Last 10 visits:\n{}'.format('\n'.join(results))

    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}
# [END gae_flex_datastore_app]


@app.route('/user')
def generate_1000():
    ds = datastore.Client()
    entity = datastore.Entity(key=ds.key('User'))
    entity.update({
        'first': 'Tabitha',
        'last': 'Amenueveve',
        'bio': 'I am a doc',
        'dob': datetime.datetime.now(tz=datetime.timezone.utc),
        'height': 5.10,
        'salary': 20000,
        'verified': True,
        'posts': 'nice'
       
    })

    res = []
    query = ds.query(kind='User')
    for x in query.fetch(limit=5):
        res.append(x)

    output = f"{res}"
    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}





@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


def shutdown_handler(signal_int: int, frame: FrameType) -> None:
    logger.info(f"Caught Signal {signal.strsignal(signal_int)}")

    from utils.logging import flush

    flush()

    # Safely exit program
    sys.exit(0)


if __name__ == "__main__":
    # Running application locally, outside of a Google Cloud Environment

    # handles Ctrl-C termination
    signal.signal(signal.SIGINT, shutdown_handler)

    app.run(host="localhost", port=8080, debug=True)
else:
    # handles Cloud Run container termination
    signal.signal(signal.SIGTERM, shutdown_handler)
