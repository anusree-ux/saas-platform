"""
Sends events to the running API and checks:

1. A normal event is accepted and counted.
2. Re-sending the same idempotency_key does NOT double-count
   (tests the idempotency guard in app/tasks/events.py).
3. A burst of concurrent DIFFERENT events for the same event_name
   all land in the aggregate (tests the atomic upsert fix in
   app/tasks/events.py — this is what would have silently lost
   increments under the old read-then-write code).

Usage:
    TEST_API_KEY=sk_... python test_create_event.py

Get a key first if you don't have one:
    curl -X POST http://127.0.0.1:8000/tenants/ \
        -H "Content-Type: application/json" \
        -d '{"name": "test-tenant"}'
"""

import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

API_KEY = os.environ["TEST_API_KEY"]
BASE_URL = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:8000")

HEADERS = {"X-API-Key": API_KEY}

# All events in this run share this timestamp, so they land in the
# same hourly aggregate bucket (see app/tasks/events.py). Suffixing
# event_name with a fresh run ID keeps each run's aggregates
# isolated from any previous run's leftover counts in that bucket.
RUN_ID = uuid.uuid4().hex[:8]


def post_event(idempotency_key: str, event_name: str = "user.purchase") -> requests.Response:
    return requests.post(
        f"{BASE_URL}/events/",
        json={
            "event_name": event_name,
            "idempotency_key": idempotency_key,
            "properties": {
                "user_id": "123",
                "amount": 49.99,
                "currency": "USD",
            },
            "occurred_at": "2026-08-14T12:00:00Z",
        },
        headers=HEADERS,
    )


def get_count(event_name: str) -> int:
    response = requests.get(
        f"{BASE_URL}/analytics/events",
        params={"since": "24h"},
        headers=HEADERS,
    )
    response.raise_for_status()

    for row in response.json()["events"]:
        if row["event_name"] == event_name:
            return row["count"]

    return 0


def wait_for_worker(seconds: float = 2.0):
    """Events are processed async by Celery; give it a moment."""
    time.sleep(seconds)


def post_event_with_retry(
    idempotency_key: str,
    event_name: str,
    max_attempts: int = 5,
) -> requests.Response:
    """
    The API has a token-bucket rate limiter (10 capacity, refills
    at 10/sec — see app/rate_limiter.py). A burst of concurrent
    requests can legitimately hit 429s that have nothing to do with
    the aggregate-counting logic this test is actually checking.
    Retry those with a short backoff instead of failing on them.
    """
    for attempt in range(max_attempts):
        response = post_event(idempotency_key, event_name)

        if response.status_code != 429:
            return response

        time.sleep(0.3 * (attempt + 1))

    return response


def test_single_event_is_accepted():
    print("\n[1] Sending a single event...")

    key = f"single-{uuid.uuid4()}"
    event_name = f"test.single.{RUN_ID}"
    response = post_event(key, event_name=event_name)

    assert response.status_code == 202, (
        f"Expected 202, got {response.status_code}: {response.text}"
    )

    print("    Accepted:", response.json())

    wait_for_worker()

    count = get_count(event_name)
    assert count == 1, f"Expected count=1, got count={count}"

    print(f"    PASS — count is {count}")


def test_duplicate_idempotency_key_is_not_double_counted():
    print("\n[2] Sending the same idempotency_key twice...")

    key = f"dup-{uuid.uuid4()}"
    event_name = f"test.duplicate.{RUN_ID}"

    post_event(key, event_name=event_name)
    post_event(key, event_name=event_name)  # exact duplicate

    wait_for_worker()

    count = get_count(event_name)
    assert count == 1, (
        f"Expected count=1 (duplicate should be dropped), got count={count}"
    )

    print(f"    PASS — count stayed at {count} despite duplicate send")


def test_concurrent_events_all_land_in_aggregate():
    """
    This is the one that would have caught the original race
    condition: many workers processing distinct events for the
    same event_name/time_bucket concurrently used to lose
    increments under read-then-write. With the atomic upsert,
    every one of these should be counted.
    """
    print("\n[3] Sending 20 concurrent distinct events...")

    event_name = f"test.concurrent.{RUN_ID}"
    n = 20

    # Cap in-flight requests below the rate limiter's bucket
    # capacity so we're testing the aggregate upsert, not the
    # rate limiter itself.
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [
            pool.submit(
                post_event_with_retry,
                f"concurrent-{uuid.uuid4()}",
                event_name,
            )
            for _ in range(n)
        ]

        for future in as_completed(futures):
            response = future.result()
            assert response.status_code == 202, response.text

    # Give Celery time to work through the burst.
    wait_for_worker(seconds=4.0)

    count = get_count(event_name)
    assert count == n, (
        f"Expected count={n}, got count={count} "
        f"(lost {n - count} increments — race condition regressed!)"
    )

    print(f"    PASS — all {n} concurrent events counted correctly")


if __name__ == "__main__":
    test_single_event_is_accepted()
    test_duplicate_idempotency_key_is_not_double_counted()
    test_concurrent_events_all_land_in_aggregate()

    print("\nAll checks passed.")