"""
Scheduler service for automatic monitoring.
Every hour the scheduler wakes up and checks which areas are due (next_scheduled_detection ≤ now).
For each due area it:
  1. Sets before_date  = last_monitored  (or monitoring_started_date  if no prior scan)
  2. Sets after_date   = today
  3. Downloads Sentinel-2 imagery for both dates via GEE and runs ML change detection
  4. Saves the result (deforestation_detected, forest_loss_percent, …) to detection history
  5. Advances next_scheduled_detection by monitoring_interval_days (default 5)
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import sys
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.area_manager import AreaManager, _JSON_FALLBACK, _db_available
from src.ml.api_integration import detect_change_auto_internal

logger = logging.getLogger(__name__)


class MonitoringScheduler:
    def __init__(self, check_interval_minutes: int = 60):
        """
        Args:
            check_interval_minutes: How often to poll for due detections (default 60 min).
        """
        self.check_interval_minutes = check_interval_minutes
        self.area_manager = AreaManager()
        self.is_running = False

    # ------------------------------------------------------------------
    # Core detection runner
    # ------------------------------------------------------------------

    async def run_scheduled_detection(self, area: Dict) -> Dict:
        """Run ML change detection for a single area that is due for a scan.

        before_date = last_monitored date (or monitoring_started_date for first scan)
        after_date  = today
        """
        name = area.get('name', area['id'])
        try:
            logger.info(f"[Scheduler] Starting scheduled scan for '{name}' (id={area['id']})")

            # ── Determine date range ───────────────────────────────────────
            today = datetime.now()
            after_str = today.strftime('%Y-%m-%d')

            raw_before = area.get('last_monitored') or area.get('monitoring_started_date')
            if raw_before:
                # Parse ISO string to ensure correct type
                if isinstance(raw_before, str):
                    raw_before = datetime.fromisoformat(raw_before.split('.')[0].replace('Z', ''))
                before_str = raw_before.strftime('%Y-%m-%d')
            else:
                # Fallback: compare against monitoring_interval_days ago
                interval = area.get('monitoring_interval_days') or 5
                before_str = (today - timedelta(days=interval)).strftime('%Y-%m-%d')

            logger.info(f"[Scheduler] Date window: {before_str} → {after_str}")

            # ── Bounding box ───────────────────────────────────────────────
            coords = area['coordinates']
            lats = [c[0] for c in coords]
            lngs = [c[1] for c in coords]

            west  = min(lngs)
            south = min(lats)
            east  = max(lngs)
            north = max(lats)

            # ── Run ML detection ───────────────────────────────────────────
            result = await detect_change_auto_internal(
                before_date=before_str,
                after_date=after_str,
                west=west,
                south=south,
                east=east,
                north=north,
                window_days=15,
                max_cloud_cover=80.0,
            )

            # ── Persist result ─────────────────────────────────────────────
            self.area_manager.add_detection_record(area['id'], result)

            deforested = result.get('deforestation_detected', False)
            loss = result.get('change', {}).get('forest_loss_percent', 0) or 0
            logger.info(
                f"[Scheduler] '{name}' scan complete — "
                f"deforestation={'YES ⚠️' if deforested else 'NO ✅'}, loss={loss:.1f}%"
            )
            return result

        except Exception as e:
            logger.error(f"[Scheduler] Scan failed for '{name}': {e}")
            return {"status": "error", "error": str(e)}

    # ------------------------------------------------------------------
    # Due-area query (MySQL + JSON fallback)
    # ------------------------------------------------------------------

    def _get_due_areas_json(self) -> List[Dict]:
        """Return areas due for detection from the JSON fallback store."""
        try:
            if not _JSON_FALLBACK.exists():
                return []
            with open(_JSON_FALLBACK) as f:
                data = json.load(f)
            now = datetime.now()
            due = []
            for a in data.get('areas', []):
                if not a.get('active_monitoring'):
                    continue
                next_det = a.get('next_scheduled_detection')
                if not next_det:
                    continue
                try:
                    next_dt = datetime.fromisoformat(str(next_det).split('.')[0])
                    if next_dt <= now:
                        due.append(a)
                except Exception:
                    pass
            return due
        except Exception as e:
            logger.error(f"[Scheduler] JSON fallback error in _get_due_areas_json: {e}")
            return []

    def get_due_areas(self) -> List[Dict]:
        """Get all areas whose next_scheduled_detection is overdue."""
        if not _db_available():
            return self._get_due_areas_json()
        try:
            return self.area_manager.get_areas_for_scheduled_detection()
        except Exception as e:
            logger.warning(f"[Scheduler] DB query failed, using JSON fallback: {e}")
            return self._get_due_areas_json()

    # ------------------------------------------------------------------
    # Main loop helpers
    # ------------------------------------------------------------------

    async def check_and_run_detections(self):
        """Check for due areas and run scheduled detections."""
        try:
            due_areas = self.get_due_areas()
            if not due_areas:
                logger.debug("[Scheduler] No areas due for scheduled detection")
                return
            logger.info(f"[Scheduler] {len(due_areas)} area(s) due for detection")
            for area in due_areas:
                await self.run_scheduled_detection(area)
        except Exception as e:
            logger.error(f"[Scheduler] Error in check_and_run_detections: {e}")

    async def start(self):
        """Start the monitoring scheduler loop."""
        self.is_running = True
        logger.info(
            f"[Scheduler] Started — checking every {self.check_interval_minutes} min "
            f"(interval = {self.check_interval_minutes * 60}s)"
        )
        while self.is_running:
            try:
                await self.check_and_run_detections()
            except Exception as e:
                logger.error(f"[Scheduler] Loop error: {e}")
            await asyncio.sleep(self.check_interval_minutes * 60)

    def stop(self):
        """Stop the monitoring scheduler."""
        self.is_running = False
        logger.info("[Scheduler] Stopped")


# Global singleton instance
scheduler = MonitoringScheduler()


async def start_scheduler():
    """Start the global scheduler."""
    await scheduler.start()


def stop_scheduler():
    """Stop the global scheduler."""
    scheduler.stop()


# Global scheduler instance
scheduler = MonitoringScheduler()

async def start_scheduler():
    """Start the global scheduler"""
    await scheduler.start()

def stop_scheduler():
    """Stop the global scheduler"""
    scheduler.stop()
