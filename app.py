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

import csv
import signal
import sys
from datetime import datetime
from types import FrameType

from flask import Flask, request, Response, make_response

from utils.logging import logger

import logging
import socket

from google.cloud import datastore

app = Flask(__name__)


def is_ipv6(addr):
    """Checks if a given address is an IPv6 address."""
    try:
        socket.inet_pton(socket.AF_INET6, addr)
        return True
    except socket.error:
        return False


# # [START gae_flex_datastore_app]
# @app.route('/')
# def index():
#     ds = datastore.Client()

#     user_ip = request.remote_addr

#     # Keep only the first two octets of the IP address.
#     if is_ipv6(user_ip):
#         user_ip = ':'.join(user_ip.split(':')[:2])
#     else:
#         user_ip = '.'.join(user_ip.split('.')[:2])

#     entity = datastore.Entity(key=ds.key('visit'))
#     # print(dir(entity))
#     # entity.update({
#     #     'user_ip': user_ip,
#     #     'timestamp': datetime.datetime.now(tz=datetime.timezone.utc)
#     # })

#     # ds.put(entity)
#     query = ds.query(kind='visit', order=('-timestamp',))

#     results = []
#     for x in query.fetch(limit=10):
#         try:
#             results.append('Time: {timestamp} Addr: {user_ip}'.format(**x))
#         except KeyError:
#             print("Error with result format, skipping entry.")

#     output = 'Last 10 visits:\n{}'.format('\n'.join(results))

#     return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}
# # [END gae_flex_datastore_app]


# @app.route('/user')
# def generate_1000():
#     ds = datastore.Client()
#     entity = datastore.Entity(key=ds.key('User'))
#     entity.update({
#         'first': 'Tabitha',
#         'last': 'Amenueveve',
#         'bio': 'I am a doc',
#         'dob': datetime.datetime.now(tz=datetime.timezone.utc),
#         'height': 5.10,
#         'salary': 20000,
#         'verified': True,
#         'posts': 'nice'
       
#     })

#     res = []
#     query = ds.query(kind='User')
#     for x in query.fetch(limit=5):
#         res.append(x)

#     output = f"{res}"
#     return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/')
def index():
    output = f"Welcome"
    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/create')
def create_entity():
    client = datastore.Client()
    user = datastore.Entity(client.key("User"))
    user.update({
        'first': 'New',
        'last': 'Boateng',
        'bio': 'Software Engineer',
        'dob': datetime(2022, 12, 28),
        'height': 5.6,
        'salary': 2000,
        'verified': True,
        'posts': ['nice', 'loved it']
    })

    client.put(user)

    output = f"Hope they were created"
    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/remove')
def delete_entities():
    client = datastore.Client()
    key = client.key('User')
    client.delete(key)

    output = f"Hope they were deleted"
    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/csv')
def generate_csv():
    client = datastore.Client()
    query = client.query(kind="User")

    users = query.fetch()

    # users = [
    #     {"name":"mick", "age":100},
    #     {"wow":"tab", "age":100},
    # ]

    csv_data = ''
    for user in users:
        csv_data += f"""
        {user['first']}, 
        {user['last']}, 
        {user['bio']}, 
        {user['dob']}, 
        {user['height']}, 
        {user['salary']}, 
        {user['verified']}, 
        {user['posts']}, 
        """


    response = make_response(csv_data)
    response.headers['Content-Disposition'] = 'attachment; filename=data.csv'
    response.headers['Content-Type'] = 'text/csv'

    # Return the response object
    return response



@app.route('/update-entity')
def update_an_entity_from_another():
    client = datastore.Client()
    query = client.query(kind="User")

    entity = datastore.Entity(key=client.key('info'))


    for user in query.fetch():
        entity.update({
            'first': user['first'],
            'bio': user['bio'],
        })
        client.put(entity)

    output = f"Hope it did."
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
