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
import datetime
import random
import csv
from types import FrameType

from flask import Flask

from utils.logging import logger

import logging
import socket

from google.cloud import datastore
from google.cloud import storage

app = Flask(__name__)

from faker import Faker


@app.route('/')
def index():
    client = datastore.Client()
    query = client.query(kind="User")

    users = query.fetch(limit=1)

    output = ''

    for user in users:
     output += f"{user}"
    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/create')
def create_entity():
    client = datastore.Client()

    fake = Faker()

    verified_list = [True, False]

    for _ in range(1000):
        user = datastore.Entity(client.key("User"))
        user.update({
            'name': fake.name(),
            'bio': fake.text(),
            'dob': fake.date_time_between(),
            'height': random.uniform(5.0, 6.0),
            'salary': random.randint(5000,10000),
            'verified': random.choice(verified_list),
            'friends': [fake.name() for _ in range(5)],
            'grades': {
                '100': 3.5,
                '200': 3.9,
                '300': 3.0,
                '400': 3.9,
            }
        })

        client.put(user)

    output = f"Hope they were created"
    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/remove')
def delete_entities():

    client = datastore.Client()
    query = client.query(kind='User')
    users = query.fetch()

    for user in users:
        key = client.key('User')
        client.delete(key)

    output = f"Hope they were deleted"
    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/csv')
def generate_csv():
    client = datastore.Client()
    query = client.query(kind="User")

    users = query.fetch()

    source_file_name = 'users.csv'


    with open(source_file_name, 'w') as csv_file:
        writer = csv.writer(csv_file, delimiter=',')
        writer.writerow(['name', 'bio', 'dob', 'height', 'salary', 'verified', 'friends'])
        for user in users:
            writer.writerow(
                [
                    user['first'], 
                    user['last'], 
                    user['bio'], 
                    user['dob'], 
                    user['height'], 
                    user['salary'], 
                    user['verified'], 
                    user['friends'],
                ]
            )
    
    destination_blob_name = 'users_data.csv'


    storage_client = storage.CLient()
    bucket = storage_client.bucket('mickeys_store_01')
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)

    output = f"File {source_file_name} uploaded to {destination_blob_name}."
    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/update-entity')
def update_an_entity_from_another():
    client = datastore.Client()
    query = client.query(kind="User")


    for user in query.fetch():
        entity = datastore.Entity(key=client.key('info'))
        entity.update({
            'name': user['name'],
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






# users = [
    #     {
    #         'first': 'mike' , 
    #         'last': 'boat', 
    #         'bio': 'a rich engineer', 
    #         'dob': 'November 11, 2000 at 4:35:52 PM UTC+0', 
    #         'height': 5.6, 
    #         'salary': 1000, 
    #         'verified': 'true', 
    #         'friends': ["Stuart Hill","Timothy Spencer","Tracy Obrien","Ms. Carol Cuevas DVM","Sarah Craig"]
    #     },
    #     {
    #         'first': 'new' , 
    #         'last': 'one', 
    #         'bio': 'a rich engineer', 
    #         'dob': 'November 11, 2000 at 4:35:52 PM UTC+0', 
    #         'height': 5.6, 
    #         'salary': 1000, 
    #         'verified': 'true', 
    #         'friends': ["Stuart Hill","Timothy Spencer","Tracy Obrien","Ms. Carol Cuevas DVM","Sarah Craig"]
    #     }
    # ]