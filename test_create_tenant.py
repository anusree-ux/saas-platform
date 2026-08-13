import requests

response = requests.post(
    "http://127.0.0.1:8000/tenants/",
    json={
        "name": "Tenant B",
    },
)

print("Status:", response.status_code)
print("Response:")
print(response.json())