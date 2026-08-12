import json
import redis

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True,
)

def publish_tenant_update(
    tenant_id: str,
    event_name: str,
    count: int,
):
    message = {
        "tenant_id": tenant_id,
        "event_name": event_name,
        "count": count,
    }

    redis_client.publish(
        f"tenant_updates:{tenant_id}",
        json.dumps(message),
    )

def subscribe_to_tenant(tenant_id: str):
    pubsub = redis_client.pubsub()
    pubsub.subscribe(f"tenant_updates:{tenant_id}")

    return pubsub