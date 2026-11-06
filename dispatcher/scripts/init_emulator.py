"""Create the topic + subscription on the local Pub/Sub emulator (mirrors infrastructure/gcp/main.tf)."""

import os

from google.api_core.exceptions import AlreadyExists
from google.cloud import pubsub_v1

project = os.environ["PROJECT_ID"]
publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()
topic = publisher.topic_path(project, "user-messages")
dlq = publisher.topic_path(project, "user-messages-dlq")
sub = subscriber.subscription_path(project, "user-messages-dispatcher")

for t in (topic, dlq):
    try:
        publisher.create_topic(name=t)
    except AlreadyExists:
        pass
try:
    subscriber.create_subscription(
        request={
            "name": sub,
            "topic": topic,
            "enable_message_ordering": True,
            "ack_deadline_seconds": 30,
            "dead_letter_policy": {"dead_letter_topic": dlq, "max_delivery_attempts": 10},
        }
    )
except AlreadyExists:
    pass
print(f"emulator ready: {sub}")
