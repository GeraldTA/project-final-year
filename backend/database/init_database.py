"""
Database initialization script
Run this to set up the MySQL database for the deforestation detection system
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database.db_manager import get_db_manager
import yaml


def load_config():
    """Load database configuration"""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config.get('database', {})


def main():
    """Initialize the database"""
    print("=" * 60)
    print("Deforestation Detection System - Database Setup")
    print("=" * 60)
    
    # Load config
    db_config = load_config()
    print(f"\n📋 Database Configuration:")
    print(f"   Host: {db_config.get('host', 'localhost')}")
    print(f"   Port: {db_config.get('port', 3306)}")
    print(f"   Database: {db_config.get('database', 'deforestation_db')}")
    print(f"   Username: {db_config.get('username', 'root')}")
    
    # Test connection
    print("\n🔌 Testing database connection...")
    db_manager = get_db_manager()
    
    if not db_manager.test_connection():
        print("\n❌ ERROR: Could not connect to MySQL database")
        print("\nPossible issues:")
        print("  1. MySQL server is not running")
        print("  2. Incorrect username/password in config.yaml")
        print("  3. Database access permissions")
        print("\nPlease check your configuration and try again.")
        return 1
    
    print("✓ Connection successful")
    
    # Initialize schema
    print("\n📦 Initializing database schema...")
    try:
        db_manager.initialize_database()
        print("✓ Database schema created successfully")
    except Exception as e:
        print(f"\n❌ ERROR: Failed to initialize schema: {e}")
        return 1
    
    # Verify tables
    print("\n✅ Verifying tables...")
    try:
        with db_manager.get_cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"   Found {len(tables)} tables:")
            for table in tables:
                table_name = list(table.values())[0]
                print(f"     ✓ {table_name}")
    except Exception as e:
        print(f"   Warning: Could not verify tables: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Database setup completed successfully!")
    print("=" * 60)
    print("\nYou can now start the API server:")
    print("   cd backend")
    print("   python start_api.py")
    print("\n")
    
    return 0


if __name__ == "__main__":
    exit(main())
