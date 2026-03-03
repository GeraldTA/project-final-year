"""
Service for managing monitored areas
Handles CRUD operations and area metadata using MySQL database,
with automatic fallback to JSON file when MySQL is unavailable.
"""
import json
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional, Any
import uuid
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from database.db_manager import get_db_manager

# JSON fallback file path (relative to backend/)
_JSON_FALLBACK = Path(__file__).parent.parent / "data" / "monitored_areas.json"

# Cache DB availability to avoid repeated slow connection attempts
_db_available_cache: Optional[bool] = None


def _db_available() -> bool:
    """Check whether MySQL is reachable (result cached for the process lifetime)."""
    global _db_available_cache
    if _db_available_cache is None:
        try:
            _db_available_cache = get_db_manager().test_connection()
        except Exception:
            _db_available_cache = False
    return _db_available_cache


class AreaManager:
    def __init__(self):
        self.db = get_db_manager()

    # ------------------------------------------------------------------
    # JSON-file helpers (used when MySQL is offline)
    # ------------------------------------------------------------------

    def _load_json(self) -> List[Dict]:
        """Load areas from the JSON fallback file."""
        try:
            if _JSON_FALLBACK.exists():
                with open(_JSON_FALLBACK, "r") as f:
                    data = json.load(f)
                return data.get("areas", [])
        except Exception as e:
            print(f"[AreaManager] Could not read JSON fallback: {e}")
        return []

    def _save_json(self, areas: List[Dict]) -> None:
        """Persist areas to the JSON fallback file."""
        try:
            _JSON_FALLBACK.parent.mkdir(parents=True, exist_ok=True)
            with open(_JSON_FALLBACK, "w") as f:
                json.dump({"areas": areas}, f, indent=2, default=str)
        except Exception as e:
            print(f"[AreaManager] Could not write JSON fallback: {e}")

    # ------------------------------------------------------------------

    def get_all_areas(self) -> List[Dict]:
        """Get all monitored areas (MySQL → JSON fallback)."""
        if not _db_available():
            return self._sanitize(self._load_json())

        try:
            query = """
                SELECT id, name, description, coordinates, created_at, last_monitored,
                       monitoring_enabled, active_monitoring, monitoring_started_date,
                       monitoring_interval_days, next_scheduled_detection, detection_count
                FROM monitored_areas
                ORDER BY created_at DESC
            """
            areas = self.db.execute_query(query)
            # Use return value of _serialize_area
            areas = [self._serialize_area(a) for a in areas]
            for area in areas:
                area['detection_history'] = self._get_detection_history(area['id'])
            return areas
        except Exception as e:
            print(f"[AreaManager] DB error in get_all_areas, falling back to JSON: {e}")
            return self._sanitize(self._load_json())
    
    def _sanitize(self, areas: List[Dict]) -> List[Dict]:
        """Ensure all values in a list of area dicts are JSON-serializable."""
        return [self._convert_decimals_and_dates(a) for a in areas]

    def _convert_decimals_and_dates(self, obj: Any) -> Any:
        """Recursively convert Decimal, datetime, and date objects to JSON-serializable types"""
        from datetime import date as date_type
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date_type):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._convert_decimals_and_dates(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals_and_dates(item) for item in obj]
        return obj
    
    def _serialize_area(self, area: Dict) -> Dict:
        """Convert datetime and Decimal objects to JSON-serializable formats"""
        if isinstance(area['coordinates'], str):
            area['coordinates'] = json.loads(area['coordinates'])
        
        # Convert all Decimal and datetime objects
        area = self._convert_decimals_and_dates(area)
        
        return area
    
    def get_area(self, area_id: str) -> Optional[Dict]:
        """Get a specific area by ID (MySQL → JSON fallback)"""
        if not _db_available():
            areas = self._load_json()
            return next((self._convert_decimals_and_dates(a) for a in areas if a['id'] == area_id), None)

        try:
            query = """
                SELECT id, name, description, coordinates, created_at, last_monitored,
                       monitoring_enabled, active_monitoring, monitoring_started_date,
                       monitoring_interval_days, next_scheduled_detection, detection_count
                FROM monitored_areas
                WHERE id = %s
            """
            areas = self.db.execute_query(query, (area_id,))
            if not areas:
                return None
            area = self._serialize_area(areas[0])
            area['detection_history'] = self._get_detection_history(area_id)
            return area
        except Exception as e:
            print(f"[AreaManager] DB error in get_area, falling back to JSON: {e}")
            areas = self._load_json()
            return next((self._convert_decimals_and_dates(a) for a in areas if a['id'] == area_id), None)
    
    def _get_detection_history(self, area_id: str) -> List[Dict]:
        """Get detection history for an area"""
        query = """
            SELECT timestamp, before_date, after_date, deforestation_detected,
                   forest_loss_percent, vegetation_trend
            FROM detection_history
            WHERE area_id = %s
            ORDER BY timestamp DESC
            LIMIT 50
        """
        history = self.db.execute_query(query, (area_id,))
        
        # Convert datetime and Decimal objects to JSON-serializable formats
        history = [self._convert_decimals_and_dates(record) for record in history]
        
        return history
    
    def create_area(self, name: str, coordinates: List, description: str = "") -> Dict:
        """Create a new monitored area"""
        area_id = str(uuid.uuid4())
        
        print(f"[AreaManager] Creating area: {name} (ID: {area_id})")
        print(f"[AreaManager] Coordinates count: {len(coordinates)}")
        
        query = """
            INSERT INTO monitored_areas 
            (id, name, description, coordinates, monitoring_interval_days)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        if not _db_available():
            # Persist to JSON fallback
            new_area = {
                "id": area_id,
                "name": name,
                "description": description,
                "coordinates": coordinates,
                "created_at": datetime.now().isoformat(),
                "last_monitored": None,
                "monitoring_enabled": True,
                "active_monitoring": False,
                "monitoring_interval_days": 5,
                "detection_count": 0,
                "detection_history": [],
            }
            areas = self._load_json()
            areas.insert(0, new_area)
            self._save_json(areas)
            print(f"[AreaManager] Area saved to JSON fallback: {area_id}")
            return new_area

        try:
            self.db.execute_query(
                query,
                (area_id, name, description, json.dumps(coordinates), 5),
                fetch=False
            )
            print(f"[AreaManager] Area saved to database: {area_id}")

            result = self.get_area(area_id)
            print(f"[AreaManager] Retrieved saved area: {result is not None}")
            return result
        except Exception as e:
            print(f"[AreaManager] ERROR creating area: {e}")
            raise
    
    def update_area(self, area_id: str, updates: Dict) -> Optional[Dict]:
        """Update an area's properties (MySQL → JSON fallback)"""
        if not _db_available():
            areas = self._load_json()
            for area in areas:
                if area['id'] == area_id:
                    for k, v in updates.items():
                        area[k] = v.isoformat() if isinstance(v, datetime) else v
                    self._save_json(areas)
                    return area
            return None

        # Build dynamic UPDATE query based on provided updates
        allowed_fields = {
            'name', 'description', 'last_monitored', 'monitoring_enabled',
            'active_monitoring', 'monitoring_started_date', 'monitoring_interval_days',
            'next_scheduled_detection', 'detection_count'
        }
        
        update_fields = []
        values = []
        
        for field, value in updates.items():
            if field in allowed_fields:
                update_fields.append(f"{field} = %s")
                # Convert datetime objects to strings
                if isinstance(value, datetime):
                    value = value.isoformat()
                values.append(value)
        
        if not update_fields:
            return self.get_area(area_id)
        
        values.append(area_id)
        query = f"UPDATE monitored_areas SET {', '.join(update_fields)} WHERE id = %s"
        
        self.db.execute_query(query, tuple(values), fetch=False)
        return self.get_area(area_id)
    
    def delete_area(self, area_id: str) -> bool:
        """Delete a monitored area (MySQL → JSON fallback)"""
        if not _db_available():
            areas = self._load_json()
            new_areas = [a for a in areas if a['id'] != area_id]
            if len(new_areas) == len(areas):
                return False
            self._save_json(new_areas)
            return True

        query = "DELETE FROM monitored_areas WHERE id = %s"
        rows_affected = self.db.execute_query(query, (area_id,), fetch=False)
        return rows_affected > 0
    
    def start_active_monitoring(self, area_id: str) -> Optional[Dict]:
        """Enable active monitoring for an area.
        
        Records monitoring_started_date (the reference date for the first scan),
        sets monitoring_interval_days=5 and schedules next_scheduled_detection.
        """
        from datetime import timedelta
        
        area = self.get_area(area_id)
        if not area:
            return None
        
        now = datetime.now()
        interval = area.get('monitoring_interval_days') or 5
        next_detection = now + timedelta(days=interval)
        
        updates = {
            "active_monitoring": True,
            "monitoring_started_date": now,
            "monitoring_interval_days": interval,
            "next_scheduled_detection": next_detection,
        }
        
        return self.update_area(area_id, updates)
    
    def stop_active_monitoring(self, area_id: str) -> Optional[Dict]:
        """Disable active monitoring for an area"""
        updates = {
            "active_monitoring": False,
            "next_scheduled_detection": None
        }
        
        return self.update_area(area_id, updates)
    
    def add_detection_record(self, area_id: str, detection_result: Dict) -> Optional[Dict]:
        """Add a detection result to area's history (MySQL → JSON fallback)"""
        from datetime import timedelta

        area = self.get_area(area_id)
        if not area:
            return None

        now = datetime.now()

        before_info  = detection_result.get('before', {})
        after_info   = detection_result.get('after', {})
        change_info  = detection_result.get('change', {})
        deforested   = detection_result.get('deforestation_detected', False)
        loss_pct     = change_info.get('forest_loss_percent', 0)
        vegetation   = change_info.get('vegetation_trend', 'unknown')

        record = {
            "timestamp":              now.isoformat(),
            "before_date":            before_info.get('date', ''),
            "after_date":             after_info.get('date', ''),
            "deforestation_detected": deforested,
            "forest_loss_percent":    loss_pct,
            "vegetation_trend":       vegetation,
            "forest_cover_before":    before_info.get('forest_cover_percent'),
            "forest_cover_after":     after_info.get('forest_cover_percent'),
        }

        # ── JSON fallback path ────────────────────────────────────────────────
        if not _db_available():
            areas = self._load_json()
            for a in areas:
                if a['id'] == area_id:
                    a.setdefault('detection_history', []).append(record)
                    a['detection_count'] = len(a['detection_history'])
                    a['last_monitored'] = now.isoformat()
                    if a.get('active_monitoring'):
                        interval = a.get('monitoring_interval_days') or 5
                        a['monitoring_interval_days'] = interval  # ensure stored
                        a['next_scheduled_detection'] = (
                            now + timedelta(days=interval)
                        ).isoformat()
                    self._save_json(areas)
                    return a
            return None

        # ── MySQL path ────────────────────────────────────────────────────────
        query = """
            INSERT INTO detection_history
            (area_id, before_date, after_date, deforestation_detected,
             forest_loss_percent, vegetation_trend, forest_cover_before,
             forest_cover_after, change_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            self.db.execute_query(query, (
                area_id,
                record['before_date'] or None,
                record['after_date']  or None,
                deforested,
                loss_pct,
                vegetation,
                before_info.get('forest_cover_percent'),
                after_info.get('forest_cover_percent'),
                json.dumps(change_info)
            ), fetch=False)
        except Exception as e:
            print(f"[AreaManager] DB error inserting detection history: {e}")

        # Update area metadata
        detection_count = area.get('detection_count', 0) + 1
        next_detection  = None
        if area.get('active_monitoring'):
            next_detection = now + timedelta(days=area.get('monitoring_interval_days', 5))

        updates = {
            "last_monitored":          now,
            "detection_count":         detection_count,
            "next_scheduled_detection": next_detection,
        }

        return self.update_area(area_id, updates)
    
    def get_areas_for_scheduled_detection(self) -> List[Dict]:
        """Get areas that need detection based on schedule"""
        query = """
            SELECT id, name, description, coordinates, created_at, last_monitored,
                   monitoring_enabled, active_monitoring, monitoring_started_date,
                   monitoring_interval_days, next_scheduled_detection, detection_count
            FROM monitored_areas
            WHERE active_monitoring = TRUE
              AND next_scheduled_detection IS NOT NULL
              AND next_scheduled_detection <= NOW()
        """
        
        areas = self.db.execute_query(query)
        
        # Parse JSON coordinates and add detection history
        for area in areas:
            if isinstance(area['coordinates'], str):
                area['coordinates'] = json.loads(area['coordinates'])
            area['detection_history'] = self._get_detection_history(area['id'])
        
        return areas
