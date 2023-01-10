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
from google.cloud import pubsub_v1
from concurrent.futures import TimeoutError

app = Flask(__name__)

from faker import Faker

client = datastore.Client()
storage_client = storage.Client()
publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()

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

def delete_entities_of_a_query(kind_name, query):
    for obj in query:
        delete_entity(kind_name, obj.key.id)


def create_csv(filename, query):
    csv_header = ['cloud_id']
    # main_query = query
    # first_item = next(query)
    # csv_header.extend([key for key in first_item.keys()])

    count = 1

    with open(filename, 'w') as csv_file:
        writer = csv.writer(csv_file, delimiter=',')
        for obj in query:
            while count < 2:
                csv_header.extend([key for key in obj.keys()])
                writer.writerow(csv_header)
                count += 1

            obj_values = [obj.key.id]
            
            for key in csv_header[2:]:
                obj_values.append(obj[key])

            writer.writerow(obj_values)
    return csv_file


def storage_object_in_cloud_bucket(bucket_name, source_file_name, destination_blob_name):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)

    return f"File {source_file_name} uploaded to {destination_blob_name}."


def send_message_to_pubsub_topic(project_id, topic_id, message):
    topic_path = publisher.topic_path(project_id, topic_id)
    message = message.encode("utf-8")
    publisher.publish(topic_path, message)
    print(f"Published messages to {topic_path}.")


@app.route('/')
def index():
    users = query_a_kind('User', 1)
    output = ''
    first_user = next(users)
    see = ['cloud']
    see.extend([key for key in first_user.keys()])

    
    output += f"{users} \n{first_user.key.id} \n{first_user.keys()} \nlook:{see}"
    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/create')
def create_entity():
    
    generate_entities_with_faker(1000, "User")

    output = f"Hope they were created"
    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}



@app.route('/remove')
def delete_entities():
    users = query_a_kind('User')
    infos = query_a_kind('info')
    delete_entities_of_a_query('User', users)
    delete_entities_of_a_query('info', infos)

    output = f"Hope they were deleted"
    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/csv')
def generate_csv():
    users = query_a_kind('User')

    csv_file = create_csv('users.csv', users)
    
    output = storage_object_in_cloud_bucket('mickeys_store_01', 'users.csv', 'new_users_data.csv')

    output += f'\n\n{csv_file}, type: {type(csv_file)}'

    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/update-entity')
def update_an_entity_from_another():
    query = query_a_kind('User', limit=5)

    project_id = 'serene-coyote-373909'
    topic_id = 'user-modified-messages'

    for user in query:
        entity = datastore.Entity(key=client.key('info'))
        modify_name = f"{user['name']} was modified."
        modify_bio = f"UPDATED {user['bio']}"

        entity.update({
            'name': modify_name,
            'bio': modify_bio,
        })
    
        client.put(entity)

        pubsub_message = f'{modify_name} and {modify_bio}'

        send_message_to_pubsub_topic(project_id, topic_id, pubsub_message)

    output = f"Hope it did."
    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/messages')
def pubsub_sub_messages():
    project_id = 'serene-coyote-373909'
    subscription_id = 'subA'
    timeout = 5.0

    subscription_path = subscriber.subscription_path(project_id, subscription_id)

    def callback(message: pubsub_v1.subscriber.message.Message) -> None:
        print(f"Received {message}.")
        msg = datastore.Entity(client.key('Pub_Messages'))
        msg.update({
            'message': f'{message.data}',
        })
        client.put(msg)
        message.ack()

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    print(f"Listening for messages on {subscription_path}..\n")

    output = 'Done>>'

    with subscriber:
        try:
    
            streaming_pull_future.result(timeout=timeout)
        except TimeoutError:
            streaming_pull_future.cancel()  
            streaming_pull_future.result()  

    # output += f"{streaming_pull_future}."
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