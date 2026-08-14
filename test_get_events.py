import requests

API_KEY = "sk_lofsHzUwV_raFiCJftTwuyHPTA2JxfRIzGgycTP02wE"

response = requests.get(
    "http://127.0.0.1:8000/events/",
    headers={
        "X-API-Key": API_KEY,
    },
)

print("Status:", response.status_code)
print("Response:")

for event in response.json():
    print(event)