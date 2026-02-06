#!/usr/bin/env python3
"""
Test to verify if the FRONTEND is actually sending dates when user clicks Run Detection.
This simulates what the browser would do.
"""

import requests
import json
import time

BACKEND_URL = "http://127.0.0.1:8001"
TEST_AREA_ID = "80aa81c2-a728-4524-867a-061475d9c251"

print("=" * 80)
print("TESTING: Simulating Frontend Run Detection Button Click")
print("=" * 80)

# Test 1: With dates (what should happen)
print("\n[Test 1] Sending request WITH dates (expected behavior):")
test_with_dates = {
    "before_date": "2024-01-01",
    "after_date": "2024-03-01"
}
print(f"  Request body: {json.dumps(test_with_dates, indent=2)}")

try:
    response = requests.post(
        f"{BACKEND_URL}/api/monitored-areas/{TEST_AREA_ID}/detect",
        json=test_with_dates,
        headers={"Content-Type": "application/json"},
        timeout=120
    )
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        print("  ✓ Detection started with custom dates")
    elif response.status_code == 400:
        error = response.json()
        print(f"  ✗ Error 400: {error}")
    else:
        print(f"  ? Unexpected: {response.text[:200]}")
except Exception as e:
    print(f"  ✗ Exception: {e}")

time.sleep(2)

# Test 2: Without dates (what might be happening)
print("\n[Test 2] Sending request WITHOUT dates (bug scenario):")
test_without_dates = {}
print(f"  Request body: {json.dumps(test_without_dates, indent=2)}")

try:
    response = requests.post(
        f"{BACKEND_URL}/api/monitored-areas/{TEST_AREA_ID}/detect",
        json=test_without_dates,
        headers={"Content-Type": "application/json"},
        timeout=5
    )
    print(f"  Status: {response.status_code}")
    if response.status_code == 400:
        error = response.json()
        print(f"  ✓ Correctly rejected: {error.get('error', error.get('detail'))}")
    elif response.status_code == 200:
        print("  ✗ BUG: Backend accepted empty dates (should return 400)")
    else:
        print(f"  ? Unexpected: {response.text[:200]}")
except Exception as e:
    print(f"  Exception: {e}")

time.sleep(2)

# Test 3: Check what the backend logs show
print("\n[Test 3] Checking backend logs...")
print("  Look at the backend terminal for these log lines:")
print("    - 'Raw request body bytes: ...'")
print("    - 'Parsed JSON params: ...'")
print("    - 'Extracted before_date: ..., after_date: ...'")

print("\n" + "=" * 80)
print("NEXT STEP: Check the backend terminal output to see what it received")
print("=" * 80)
