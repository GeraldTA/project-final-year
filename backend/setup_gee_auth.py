"""
Google Earth Engine Authentication Setup Script

This script helps you authenticate with Google Earth Engine interactively.
Run this once to set up your credentials.
"""

import ee
from pathlib import Path

def setup_gee_authentication():
    """Set up Google Earth Engine authentication."""
    
    print("=" * 60)
    print("Google Earth Engine Authentication Setup")
    print("=" * 60)
    
    # Read project ID
    project_file = Path("gee_project_id.txt")
    if not project_file.exists():
        print("\n❌ ERROR: gee_project_id.txt not found!")
        print("Please create this file with your GEE project ID first.")
        return False
    
    project_id = project_file.read_text().strip()
    print(f"\n✓ Found project ID: {project_id}")
    
    print("\n📋 Authentication Steps:")
    print("1. A browser window will open")
    print("2. Sign in with your Google account")
    print("3. Grant Earth Engine permissions")
    print("4. Copy the authorization code")
    print("5. Paste it back here")
    
    input("\n Press Enter to continue...")
    
    try:
        # Authenticate
        print("\n🔐 Starting authentication...")
        ee.Authenticate()
        
        # Initialize to verify
        print("\n✅ Initializing Earth Engine...")
        ee.Initialize(project=project_id)
        
        print("\n" + "=" * 60)
        print("✅ SUCCESS! Google Earth Engine is now configured.")
        print("=" * 60)
        print("\nYou can now use the ML Change Detection features!")
        print("Your credentials are saved and will work automatically.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Authentication failed: {e}")
        return False

if __name__ == "__main__":
    success = setup_gee_authentication()
    
    if success:
        print("\n🎉 Setup complete! You can now restart your backend server.")
    else:
        print("\n⚠️ Setup incomplete. Please try again or check the error above.")
