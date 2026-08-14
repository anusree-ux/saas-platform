import requests

API_KEY = "sk_lofsHzUwV_raFiCJftTwuyHPTA2JxfRIzGgycTP02wE"

url = "http://127.0.0.1:8000/events/"

event = {
    "event_name": "user.purchase",
    "idempotency_key": "purchase-test-028",
    "properties": {
        "user_id": "123",
        "amount": 49.99,
        "currency": "USD",
    },
    "occurred_at": "2026-08-13T21:00:00Z",
}

response = requests.post(
    url,
    json=event,
    headers={
        "X-API-Key": API_KEY,
    },
)

print("Status:", response.status_code)
print("Response:")
print(response.json())