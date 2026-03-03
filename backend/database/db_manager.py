"""
Database connection manager for MySQL
Handles connection pooling and database operations
"""
import pymysql
from pymysql import cursors
from contextlib import contextmanager
from typing import Optional, Dict, Any
import yaml
from pathlib import Path


class DatabaseManager:
    """Manages MySQL database connections and operations"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Try multiple paths
            possible_paths = [
                "config/config.yaml",  # When running from backend/
                "backend/config/config.yaml",  # When running from project root
                Path(__file__).parent.parent / "config" / "config.yaml"  # Relative to this file
            ]
            for path in possible_paths:
                if Path(path).exists():
                    config_path = str(path)
                    break
            else:
                config_path = "config/config.yaml"  # Default fallback
        
        self.config = self._load_config(config_path)
        self.connection_params = {
            'host': self.config.get('host', 'localhost'),
            'port': self.config.get('port', 3306),
            'user': self.config.get('username', 'root'),
            'password': self.config.get('password', ''),
            'database': self.config.get('database', 'deforestation_db'),
            'charset': self.config.get('charset', 'utf8mb4'),
            'cursorclass': cursors.DictCursor,
            'autocommit': False
        }
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load database configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                full_config = yaml.safe_load(f)
                return full_config.get('database', {})
        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {e}")
            return {}
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = pymysql.connect(**self.connection_params)
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: tuple = None, fetch: bool = True):
        """Execute a SQL query and optionally fetch results"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params or ())
            if fetch:
                return cursor.fetchall()
            return cursor.rowcount
    
    def execute_many(self, query: str, params_list: list):
        """Execute multiple queries with different parameters"""
        with self.get_cursor() as cursor:
            cursor.executemany(query, params_list)
            return cursor.rowcount
    
    def initialize_database(self):
        """Initialize database schema from SQL file"""
        schema_path = Path(__file__).parent / "schema.sql"
        
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        
        with open(schema_path, 'r') as f:
            sql_script = f.read()
        
        # Split by semicolons and execute each statement
        statements = [s.strip() for s in sql_script.split(';') if s.strip()]
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for statement in statements:
                # Strip leading comment lines before deciding whether to skip
                lines = [l for l in statement.splitlines() if not l.strip().startswith('--')]
                clean = '\n'.join(lines).strip()
                if clean:
                    cursor.execute(clean)
            cursor.close()
        
        print("✓ Database schema initialized successfully")
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    return result is not None
        except Exception as e:
            print(f"Database connection test failed: {e}")
            return False


# Singleton instance
_db_manager: Optional[DatabaseManager] = None

def get_db_manager() -> DatabaseManager:
    """Get or create database manager singleton"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
