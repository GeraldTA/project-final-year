"""
Quick test to verify monitored areas API is working
Run this to check if the database is set up correctly
"""
import requests
import json

API_URL = "http://127.0.0.1:8001"

def test_api():
    print("=" * 60)
    print("Testing Monitored Areas API")
    print("=" * 60)
    
    # Test 1: Check API is running
    print("\n1. Checking if API is running...")
    try:
        res = requests.get(f"{API_URL}/api/monitored-areas", timeout=5)
        print(f"   ✓ API is running (Status: {res.status_code})")
        
        if res.status_code == 200:
            data = res.json()
            print(f"   ✓ Found {len(data.get('areas', []))} existing areas")
        else:
            print(f"   ✗ Unexpected status code: {res.status_code}")
            print(f"   Response: {res.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("   ✗ ERROR: Cannot connect to API")
        print("   Please start the backend server:")
        print("   cd backend")
        print("   python start_api.py")
        return False
    except Exception as e:
        print(f"   ✗ ERROR: {e}")
        return False
    
    # Test 2: Try creating a test area
    print("\n2. Creating test area...")
    test_area = {
        "name": "Test Area",
        "description": "Test area for debugging",
        "coordinates": [
            [31.05, -17.82],
            [31.06, -17.82],
            [31.06, -17.83],
            [31.05, -17.83],
            [31.05, -17.82]
        ]
    }
    
    try:
        res = requests.post(
            f"{API_URL}/api/monitored-areas",
            json=test_area,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if res.status_code == 200:
            data = res.json()
            area = data.get('area', {})
            print(f"   ✓ Area created successfully!")
            print(f"   ID: {area.get('id')}")
            print(f"   Name: {area.get('name')}")
            return True
        else:
            print(f"   ✗ Failed to create area (Status: {res.status_code})")
            print(f"   Response: {res.text}")
            
            # Check if it's a database error
            if "database" in res.text.lower() or "mysql" in res.text.lower():
                print("\n   💡 Database Error Detected!")
                print("   Please initialize the database:")
                print("   1. Make sure MySQL is running")
                print("   2. Update password in backend/config/config.yaml")
                print("   3. Run: cd backend/database && python init_database.py")
            
            return False
    except Exception as e:
        print(f"   ✗ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_api()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nYour monitored areas API is working correctly!")
    else:
        print("\n" + "=" * 60)
        print("❌ TESTS FAILED")
        print("=" * 60)
        print("\nPlease check the errors above and:")
        print("1. Ensure backend server is running (python backend/start_api.py)")
        print("2. Check MySQL is running and configured")
        print("3. Initialize database if needed")
