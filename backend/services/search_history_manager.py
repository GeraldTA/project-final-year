"""
Service for managing search history
Handles storing and retrieving location search records
"""
import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from database.db_manager import get_db_manager


class SearchHistoryManager:
    """Manages search history in MySQL database"""
    
    def __init__(self):
        self.db = get_db_manager()
    
    def add_search(
        self, 
        query: str, 
        results_count: int,
        search_type: str = "location",
        country: str = None,
        user_ip: str = None,
        user_agent: str = None,
        latitude: float = None,
        longitude: float = None,
        selected_result: Dict = None
    ) -> int:
        """
        Add a search record to history
        
        Returns:
            int: The ID of the inserted search record
        """
        sql = """
            INSERT INTO search_history 
            (search_query, search_type, country, results_count, user_ip, user_agent,
             latitude, longitude, selected_result)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        selected_json = json.dumps(selected_result) if selected_result else None
        
        with self.db.get_cursor() as cursor:
            cursor.execute(sql, (
                query,
                search_type,
                country,
                results_count,
                user_ip,
                user_agent,
                latitude,
                longitude,
                selected_json
            ))
            return cursor.lastrowid
    
    def get_recent_searches(self, limit: int = 50) -> List[Dict]:
        """Get recent search history"""
        sql = """
            SELECT id, search_query, search_type, country, results_count, 
                   timestamp, latitude, longitude
            FROM search_history
            ORDER BY timestamp DESC
            LIMIT %s
        """
        
        searches = self.db.execute_query(sql, (limit,))
        
        # Convert datetime to ISO format
        for search in searches:
            if search.get('timestamp'):
                search['timestamp'] = search['timestamp'].isoformat()
        
        return searches
    
    def get_popular_searches(self, limit: int = 10, days: int = 30) -> List[Dict]:
        """Get most popular search queries in the last N days"""
        sql = """
            SELECT search_query, COUNT(*) as search_count,
                   MAX(timestamp) as last_searched,
                   AVG(results_count) as avg_results
            FROM search_history
            WHERE timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY search_query
            ORDER BY search_count DESC
            LIMIT %s
        """
        
        popular = self.db.execute_query(sql, (days, limit))
        
        # Convert datetime to ISO format
        for item in popular:
            if item.get('last_searched'):
                item['last_searched'] = item['last_searched'].isoformat()
        
        return popular
    
    def get_search_stats(self) -> Dict:
        """Get overall search statistics"""
        sql = """
            SELECT 
                COUNT(*) as total_searches,
                COUNT(DISTINCT search_query) as unique_queries,
                COUNT(DISTINCT DATE(timestamp)) as days_with_searches,
                AVG(results_count) as avg_results_per_search,
                MIN(timestamp) as first_search,
                MAX(timestamp) as last_search
            FROM search_history
        """
        
        stats = self.db.execute_query(sql)
        
        if stats and len(stats) > 0:
            stat = stats[0]
            # Convert datetime to ISO format
            if stat.get('first_search'):
                stat['first_search'] = stat['first_search'].isoformat()
            if stat.get('last_search'):
                stat['last_search'] = stat['last_search'].isoformat()
            return stat
        
        return {}
    
    def search_by_location(self, latitude: float, longitude: float, radius_km: float = 10) -> List[Dict]:
        """
        Find searches near a location
        
        Args:
            latitude: Latitude of the center point
            longitude: Longitude of the center point
            radius_km: Search radius in kilometers
        """
        # Approximate conversion: 1 degree = 111 km
        degree_radius = radius_km / 111.0
        
        sql = """
            SELECT id, search_query, search_type, timestamp, 
                   latitude, longitude, results_count,
                   (6371 * acos(cos(radians(%s)) * cos(radians(latitude)) * 
                    cos(radians(longitude) - radians(%s)) + 
                    sin(radians(%s)) * sin(radians(latitude)))) AS distance_km
            FROM search_history
            WHERE latitude IS NOT NULL 
              AND longitude IS NOT NULL
              AND latitude BETWEEN %s AND %s
              AND longitude BETWEEN %s AND %s
            HAVING distance_km <= %s
            ORDER BY distance_km ASC
            LIMIT 50
        """
        
        searches = self.db.execute_query(sql, (
            latitude, longitude, latitude,
            latitude - degree_radius, latitude + degree_radius,
            longitude - degree_radius, longitude + degree_radius,
            radius_km
        ))
        
        # Convert datetime to ISO format
        for search in searches:
            if search.get('timestamp'):
                search['timestamp'] = search['timestamp'].isoformat()
        
        return searches
    
    def clear_old_history(self, days: int = 90) -> int:
        """Delete search history older than N days"""
        sql = """
            DELETE FROM search_history
            WHERE timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)
        """
        
        rows_deleted = self.db.execute_query(sql, (days,), fetch=False)
        return rows_deleted
