import json

import redis


redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True,
)


def publish_tenant_update(
    tenant_id: str,
    event_id: str,
    event_name: str,
    properties: dict,
    occurred_at: str,
    received_at: str,
    count: int,
):
    message = {
        "type": "event",
        "tenant_id": tenant_id,
        "event_id": event_id,
        "event_name": event_name,
        "properties": properties,
        "occurred_at": occurred_at,
        "received_at": received_at,
        "count": count,
    }

    redis_client.publish(
        f"tenant_updates:{tenant_id}",
        json.dumps(message),
    )


def subscribe_to_tenant(tenant_id: str):
    pubsub = redis_client.pubsub()

    pubsub.subscribe(
        f"tenant_updates:{tenant_id}"
    )

    return pubsub