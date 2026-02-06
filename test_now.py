import requests
import json
import time

# Test with real area ID
area_id = "80aa81c2-a728-4524-867a-061475d9c251"
url = f"http://127.0.0.1:8001/api/monitored-areas/{area_id}/detect"

# Custom dates
payload = {
    "before_date": "2023-06-01",
    "after_date": "2023-08-01"
}

print("Sending POST request to:", url)
print("Payload:", json.dumps(payload, indent=2))
print("\nWaiting for response...\n")

try:
    response = requests.post(url, json=payload, timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"ERROR: {e}")
