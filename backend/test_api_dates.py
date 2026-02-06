#!/usr/bin/env python3
"""Test script to verify the API receives dates correctly"""
import requests
import json

# Test data
test_area_id = "test-area-123"
test_dates = {
    "before_date": "2024-01-01",
    "after_date": "2024-02-01"
}

print("=" * 80)
print("Testing POST /api/monitored-areas/{area_id}/detect endpoint")
print("=" * 80)
print(f"\nArea ID: {test_area_id}")
print(f"Request Body: {json.dumps(test_dates, indent=2)}")
print("\nSending request...")

try:
    response = requests.post(
        f"http://127.0.0.1:8001/api/monitored-areas/{test_area_id}/detect",
        json=test_dates,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    try:
        response_data = response.json()
        print(f"\nResponse Body:\n{json.dumps(response_data, indent=2)}")
    except Exception as e:
        print(f"\nResponse Body (raw text):\n{response.text}")
        
except Exception as e:
    print(f"\nERROR: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
