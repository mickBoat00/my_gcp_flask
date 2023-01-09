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

client = datastore.Client()
storage_client = storage.Client()

def generate_entities_with_faker(num_of_entites, kind_name):

    fake = Faker()

    verified_list = [True, False]

    for _ in range(num_of_entites):
        user = datastore.Entity(client.key(kind_name))
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

def query_a_kind(kind_name, limit=None):
    query = client.query(kind=kind_name)
    
    if limit:
        return query.fetch(limit=limit)
    
    return query.fetch()


def delete_entity(kind_name, entity_id):
    key = client.key(kind_name, entity_id)
    client.delete(key)


def generate_csv(filename, query):
    with open(filename, 'w') as csv_file:
        writer = csv.writer(csv_file, delimiter=',')
        writer.writerow(['cloud_id','name','bio', 'dob', 'height', 'salary', 'verified', 'friends', 'grades'])
        for obj in query:
            writer.writerow(
                [
                    obj.key.id, 
                    obj['name'], 
                    obj['bio'], 
                    obj['dob'], 
                    obj['height'], 
                    obj['salary'], 
                    obj['verified'], 
                    obj['friends'],
                    obj['grades'],
                ]
            )
    return csv_file


def storage_object_in_cloud_bucket(bucket_name, source_file_name, destination_blob_name):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)

    return f"File {source_file_name} uploaded to {destination_blob_name}."


@app.route('/')
def index():
    users = query_a_kind('User', 1)
    output = ''
    see = ['cloud']
    see.extend([key for key in user.keys()])

    for user in users:
     output += f"{users} \n{user.key.id} \n{user.keys()} \nlook:{see}"
    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/create')
def create_entity():
    
    generate_entities_with_faker(1000, "User")

    output = f"Hope they were created"
    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}



@app.route('/remove')
def delete_entities():
    users = query_a_kind('User')

    for user in users:
        delete_entity('User', user.key.id)

    infos = query_a_kind('info')

    for info in infos:
        delete_entity('info', info.key.id)

    output = f"Hope they were deleted"
    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/csv')
def generate_csv():
    users = query_a_kind('User')

    source_file_name = 'users.csv'

    csv_file = generate_csv(source_file_name, users)
    
    output = storage_object_in_cloud_bucket('mickeys_store_01', source_file_name, 'new_users_data.csv')

    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/update-entity')
def update_an_entity_from_another():
    query = query_a_kind('User', limit=None)


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