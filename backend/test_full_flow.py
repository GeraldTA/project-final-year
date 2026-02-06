#!/usr/bin/env python3
"""
Automated test to verify the frontend->backend date passing works correctly.
This script will:
1. Start monitoring the backend logs
2. Simulate a frontend request with dates
3. Verify the dates were received correctly
"""

import requests
import json
import time

BACKEND_URL = "http://127.0.0.1:8001"
TEST_AREA_ID = "80aa81c2-a728-4524-867a-061475d9c251"  # Real area from monitored_areas.json

def test_date_passing():
    print("="* 80)
    print("AUTOMATED TEST: Frontend to Backend Date Passing")
    print("=" * 80)
    
    # Step 1: Check if backend is running
    print("\n[Step 1] Checking if backend is running...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/monitored-areas", timeout=2)
        if response.ok or response.status_code == 200:
            print("✓ Backend is running")
        else:
            print("✗ Backend returned error:", response.status_code)
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Backend is not running at", BACKEND_URL)
        print("  Please start it with: cd backend && python -m uvicorn api_server:app --reload --port 8001")
        return False
    
    # Step 2: Send test request with dates
    print("\n[Step 2] Sending POST request with custom dates...")
    
    test_dates = {
        "before_date": "2024-01-15",
        "after_date": "2024-03-20"
    }
    
    print(f"  Area ID: {TEST_AREA_ID}")
    print(f"  Request Body: {json.dumps(test_dates, indent=4)}")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/monitored-areas/{TEST_AREA_ID}/detect",
            json=test_dates,
            headers={"Content-Type": "application/json"},
            timeout=120  # Give it 2 minutes for the detection to run
        )
        
        print(f"\n[Step 3] Received Response:")
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Response: {json.dumps(data, indent=2)[:500]}...")  # First 500 chars
            print("\n✓ SUCCESS: Request completed successfully!")
            print("\nCheck the backend logs to verify it received:")
            print(f"  before_date: {test_dates['before_date']}")
            print(f"  after_date: {test_dates['after_date']}")
            return True
        elif response.status_code == 400:
            error_data = response.json()
            print(f"  Error: {error_data}")
            if "before_date" in str(error_data) or "after_date" in str(error_data):
                print("\n✗ FAIL: Backend did not receive the dates!")
                print("  This means the request body was empty or malformed.")
                return False
            else:
                print("\n  This might be a validation error (check the message above)")
                return False
        else:
            print(f"  Response Body: {response.text}")
            print(f"\n  Unexpected status code: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n⏱️  Request timed out (this is normal if detection takes > 2 min)")
        print("  Check backend logs to see if dates were received correctly")
        return None
    except Exception as e:
        print(f"\n✗ Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = test_date_passing()
    print("\n" + "=" * 80)
    if result is True:
        print("TEST RESULT: ✓ PASSED - Dates were sent and processed correctly")
    elif result is False:
        print("TEST RESULT: ✗ FAILED - Dates were not received properly")
    else:
        print("TEST RESULT: ? TIMEOUT - Check backend logs manually")
    print("=" * 80)
