"""
API endpoints for monitored area management
Separated from main api_server.py for better organization
"""
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Dict, List, AsyncGenerator
import logging
from datetime import datetime, timedelta
import hashlib
import math
import random
import json as _json

from services.area_manager import AreaManager
from src.ml.api_integration import detect_change_auto_internal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/monitored-areas", tags=["Monitored Areas"])

area_manager = AreaManager()


def _point_in_polygon(lat: float, lng: float, coords: List) -> bool:
    """Ray-casting algorithm to check if a point is inside a polygon."""
    n = len(coords)
    inside = False
    j = n - 1
    for i in range(n):
        yi, xi = coords[i][0], coords[i][1]
        yj, xj = coords[j][0], coords[j][1]
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _generate_hotspots(area: Dict) -> List[Dict]:
    """
    Generate deforestation hotspot markers inside the area polygon.
    Works even without ML detection history by using simulated loss derived
    from the area seed so results are deterministic and reproducible.
    """
    coords = area.get('coordinates', [])
    if not coords or len(coords) < 3:
        return []

    # Bounding box of the polygon
    lats = [c[0] for c in coords]
    lngs = [c[1] for c in coords]
    lat_min, lat_max = min(lats), max(lats)
    lng_min, lng_max = min(lngs), max(lngs)
    lat_span = lat_max - lat_min
    lng_span = lng_max - lng_min

    # Seeded RNG so same area always shows same markers
    area_id = area.get('id', 'default')
    seed = int(hashlib.md5(area_id.encode()).hexdigest(), 16) % (2 ** 32)
    rng = random.Random(seed)

    # Only generate hotspots from confirmed deforestation records.
    # Areas without actual detections return no markers so the map stays
    # consistent with the status label shown in the stats panel.
    history = area.get('detection_history', [])
    deforested = [h for h in history if h.get('deforestation_detected')]
    if not deforested:
        return []

    total_loss = sum(abs(h.get('forest_loss_percent', 0)) for h in deforested)
    n_hotspots = max(3, min(30, int(total_loss / 5) + len(deforested)))
    reference_loss = total_loss / max(1, len(deforested))
    reference_date = deforested[-1].get('after_date') or deforested[-1].get('timestamp', '')[:10]
    reference_trend = deforested[-1].get('vegetation_trend', 'decline')

    hotspots = []
    attempts = 0
    while len(hotspots) < n_hotspots and attempts < n_hotspots * 100:
        attempts += 1
        lat = lat_min + rng.random() * lat_span
        lng = lng_min + rng.random() * lng_span
        if not _point_in_polygon(lat, lng, coords):
            continue

        loss_here = min(100.0, abs(rng.gauss(reference_loss, reference_loss * 0.3)))
        if loss_here >= 40:
            severity = 'critical'
        elif loss_here >= 20:
            severity = 'high'
        elif loss_here >= 10:
            severity = 'medium'
        else:
            severity = 'low'

        hotspots.append({
            'lat': round(lat, 6),
            'lng': round(lng, 6),
            'severity': severity,
            'forest_loss_percent': round(loss_here, 1),
            'detected_date': reference_date,
            'vegetation_trend': reference_trend,
        })

    return hotspots


@router.get("")
async def get_monitored_areas():
    """Get all monitored areas"""
    try:
        areas = area_manager.get_all_areas()
        return JSONResponse(content={"areas": areas})
    except Exception as e:
        logger.error(f"Failed to get monitored areas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/grouped")
async def get_monitored_areas_grouped():
    """
    Return monitored areas split into two groups:

      clean          – areas with active monitoring where **no** detection has ever
                       flagged deforestation_detected=True.
      deforested     – areas where at least one detection record has
                       deforestation_detected=True.
      not_monitoring – areas that have never had monitoring started (no
                       monitoring_started_date).

    Each area also carries a `monitoring_summary` helper object with the
    key dates and counts the frontend needs.
    """
    try:
        areas = area_manager.get_all_areas()
        clean = []
        deforested = []
        not_monitoring = []

        for area in areas:
            history = area.get('detection_history') or []
            ever_deforested = any(r.get('deforestation_detected') for r in history)
            scan_count = len(history)
            last_loss = None
            if history:
                last_loss = history[0].get('forest_loss_percent')

            summary = {
                "monitoring_started_date": area.get('monitoring_started_date'),
                "next_scheduled_detection": area.get('next_scheduled_detection'),
                "monitoring_interval_days": area.get('monitoring_interval_days') or 5,
                "last_monitored": area.get('last_monitored'),
                "scan_count": scan_count,
                "ever_deforested": ever_deforested,
                "latest_forest_loss_percent": last_loss,
                "active_monitoring": area.get('active_monitoring', False),
            }
            area['monitoring_summary'] = summary

            if ever_deforested:
                deforested.append(area)
            elif not area.get('monitoring_started_date'):
                not_monitoring.append(area)
            else:
                clean.append(area)

        return JSONResponse(content={
            "clean": clean,
            "deforested": deforested,
            "not_monitoring": not_monitoring,
            "totals": {
                "total": len(areas),
                "clean": len(clean),
                "deforested": len(deforested),
                "not_monitoring": len(not_monitoring),
            }
        })
    except Exception as e:
        logger.error(f"Failed to get grouped areas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_monitored_area(request: Request):
    """Create a new monitored area"""
    try:
        data = await request.json()
        logger.info(f"Received create area request: {data}")
        
        name = data.get('name')
        coordinates = data.get('coordinates')
        description = data.get('description', '')
        
        if not name or not coordinates:
            logger.error("Missing name or coordinates")
            raise HTTPException(status_code=400, detail="Name and coordinates are required")
        
        logger.info(f"Creating area: {name} with {len(coordinates)} coordinates")
        area = area_manager.create_area(name, coordinates, description)
        logger.info(f"Area created successfully: {area['id']}")
        
        return JSONResponse(content={"area": area})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create monitored area: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auto-scan-progress")
async def auto_scan_progress():
    """
    Server-Sent Events (SSE) endpoint that streams live progress while scanning
    all active-monitoring areas.  The client receives one JSON line per event:

      {"type": "start",    "total": N, "area_names": [...]}
      {"type": "scanning", "index": i, "total": N, "area_name": "...", "area_id": "..."}
      {"type": "result",   "index": i, "total": N, "area_name": "...", "area_id": "...",
                           "deforestation_detected": bool, "forest_loss_percent": float,
                           "severity": str, "before_date": str, "after_date": str,
                           "error": null | str}
      {"type": "done",     "scanned": N, "alerts": [...], "errors": [...], "message": "..."}
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        def sse(data: dict) -> str:
            return f"data: {_json.dumps(data)}\n\n"

        try:
            all_areas = area_manager.get_all_areas()
            active = [a for a in all_areas if a.get('active_monitoring')]

            if not active:
                yield sse({"type": "done", "scanned": 0, "alerts": [], "errors": [],
                            "message": "No areas with active monitoring found."})
                return

            total = len(active)
            yield sse({"type": "start", "total": total,
                        "area_names": [a.get('name', a['id']) for a in active]})

            alerts = []
            errors = []
            scanned = 0
            skipped = 0
            today = datetime.now().date()
            min_next_scan_days = None  # track earliest next scan across skipped areas

            for idx, area in enumerate(active):
                area_id      = area['id']
                area_name    = area.get('name', area_id)
                interval_days = int(area.get('monitoring_interval_days') or 5)

                # Determine date window
                last_str = area.get('last_monitored')
                if last_str:
                    try:
                        last_date = datetime.fromisoformat(str(last_str)).date()
                    except Exception:
                        last_date = today - timedelta(days=interval_days)
                else:
                    last_date = today - timedelta(days=interval_days)

                days_since_last = (today - last_date).days

                # Skip if still within monitoring interval (not due yet)
                if days_since_last < interval_days:
                    skipped += 1
                    days_until_next = interval_days - days_since_last
                    if min_next_scan_days is None or days_until_next < min_next_scan_days:
                        min_next_scan_days = days_until_next
                    yield sse({"type": "result", "index": idx, "total": total,
                                "area_name": area_name, "area_id": area_id,
                                "skipped": True,
                                "reason": f"Scanned {days_since_last}d ago — next scan in {days_until_next}d",
                                "last_scanned": str(last_date),
                                "days_until_next": days_until_next,
                                "deforestation_detected": False, "error": None})
                    continue

                before_date = str(last_date)
                after_date  = str(today)

                coords = area.get('coordinates', [])
                if not coords or len(coords) < 3:
                    errors.append({"area": area_name, "error": "Invalid coordinates"})
                    yield sse({"type": "result", "index": idx, "total": total,
                                "area_name": area_name, "area_id": area_id,
                                "deforestation_detected": False,
                                "error": "Invalid coordinates"})
                    continue

                lats = [c[0] for c in coords]
                lngs = [c[1] for c in coords]
                west, east   = min(lngs), max(lngs)
                south, north = min(lats), max(lats)

                # Signal the client we are about to start this area
                yield sse({"type": "scanning", "index": idx, "total": total,
                            "area_name": area_name, "area_id": area_id,
                            "before_date": before_date, "after_date": after_date})

                try:
                    result = await detect_change_auto_internal(
                        before_date=before_date,
                        after_date=after_date,
                        west=west, south=south, east=east, north=north,
                        max_cloud_cover=80.0,
                        window_days=30,
                        ignore_seasonal_check=True,
                    )
                    scanned += 1
                    area_manager.add_detection_record(area_id, result)

                    deforested   = result.get('deforestation_detected', False)
                    change       = result.get('change', {})
                    loss_pct     = change.get('forest_loss_percent', 0) or 0
                    severity     = (
                        "critical" if abs(loss_pct) >= 40
                        else "high"     if abs(loss_pct) >= 20
                        else "medium"   if abs(loss_pct) >= 10
                        else "low"
                    )

                    if deforested:
                        alerts.append({
                            "area_id": area_id, "area_name": area_name,
                            "before_date": before_date, "after_date": after_date,
                            "forest_loss_percent": loss_pct,
                            "vegetation_trend": change.get('vegetation_trend', 'decline'),
                            "severity": severity,
                            "scanned_at": datetime.now().isoformat(),
                        })

                    yield sse({"type": "result", "index": idx, "total": total,
                                "area_name": area_name, "area_id": area_id,
                                "deforestation_detected": deforested,
                                "forest_loss_percent": loss_pct,
                                "severity": severity,
                                "before_date": before_date, "after_date": after_date,
                                "error": None})

                except Exception as e:
                    err_msg = str(e)
                    logger.error(f"[auto-scan-progress] Failed '{area_name}': {err_msg}")
                    errors.append({"area": area_name, "error": err_msg})
                    yield sse({"type": "result", "index": idx, "total": total,
                                "area_name": area_name, "area_id": area_id,
                                "deforestation_detected": False,
                                "error": "No imagery available for this period" if "No Sentinel-2" in err_msg else err_msg})

            # Build done message
            if alerts:
                done_msg = f"\u26a0\ufe0f Deforestation detected in {len(alerts)} area(s)!"
            elif scanned > 0:
                done_msg = f"\u2705 {scanned} area(s) scanned \u2014 no new deforestation detected."
            elif skipped == total:
                if min_next_scan_days is not None and min_next_scan_days <= 1:
                    next_str = "tomorrow"
                elif min_next_scan_days is not None:
                    next_str = f"in {min_next_scan_days} day(s)"
                else:
                    next_str = "soon"
                done_msg = f"\u2705 All {total} monitored area(s) are up to date. Next scan due {next_str}."
            else:
                done_msg = f"\u2705 Monitoring complete \u2014 {scanned} scanned, {skipped} already up to date."

            yield sse({"type": "done",
                        "scanned": scanned,
                        "skipped": skipped,
                        "alerts": alerts,
                        "errors": errors,
                        "deforestation_found": len(alerts) > 0,
                        "message": done_msg,
                        "scanned_at": datetime.now().isoformat()})

        except Exception as e:
            logger.error(f"[auto-scan-progress] Fatal: {e}")
            yield sse({"type": "error", "message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering if behind proxy
        },
    )


@router.get("/{area_id}")
async def get_monitored_area(area_id: str):
    """Get a specific monitored area"""
    area = area_manager.get_area(area_id)
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")
    return JSONResponse(content={"area": area})


@router.delete("/{area_id}")
async def delete_monitored_area(area_id: str):
    """Delete a monitored area"""
    success = area_manager.delete_area(area_id)
    if not success:
        raise HTTPException(status_code=404, detail="Area not found")
    return JSONResponse(content={"message": "Area deleted successfully"})


@router.post("/{area_id}/active-monitoring/start")
async def start_active_monitoring(area_id: str):
    """
    Start active monitoring for an area
    This will automatically run detection every 5 days
    """
    try:
        area = area_manager.start_active_monitoring(area_id)
        if not area:
            raise HTTPException(status_code=404, detail="Area not found")
        
        logger.info(f"Started active monitoring for area: {area['name']} (ID: {area_id})")
        return JSONResponse(content={
            "message": "Active monitoring started",
            "area": area
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start active monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{area_id}/active-monitoring/stop")
async def stop_active_monitoring(area_id: str):
    """Stop active monitoring for an area"""
    try:
        area = area_manager.stop_active_monitoring(area_id)
        if not area:
            raise HTTPException(status_code=404, detail="Area not found")
        
        logger.info(f"Stopped active monitoring for area: {area['name']} (ID: {area_id})")
        return JSONResponse(content={
            "message": "Active monitoring stopped",
            "area": area
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop active monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{area_id}/detect")
async def run_detection_on_area(area_id: str, request: Request):
    """
    Run detection on a specific monitored area with custom dates
    """
    try:
        data = await request.json()
        before_date = data.get('before_date')
        after_date = data.get('after_date')
        
        if not before_date or not after_date:
            raise HTTPException(status_code=400, detail="Both before_date and after_date are required")
        
        # Get the area
        area = area_manager.get_area(area_id)
        if not area:
            raise HTTPException(status_code=404, detail="Area not found")
        
        # Calculate bounding box from coordinates
        coords = area['coordinates']
        lats = [c[0] for c in coords]
        lngs = [c[1] for c in coords]
        
        west = min(lngs)
        south = min(lats)
        east = max(lngs)
        north = max(lats)
        
        logger.info(f"Running detection for area {area['name']}: {before_date} to {after_date}")
        
        # Run detection
        result = await detect_change_auto_internal(
            before_date=before_date,
            after_date=after_date,
            west=west,
            south=south,
            east=east,
            north=north
        )
        
        # Save detection to history
        updated_area = area_manager.add_detection_record(area_id, result)
        
        return JSONResponse(content={
            "success": True,
            "area": updated_area,
            "detection_result": result
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Detection failed for area {area_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")


@router.get("/{area_id}/detection-history")
async def get_detection_history(area_id: str, limit: int = 50):
    """Get detection history for a specific area"""
    area = area_manager.get_area(area_id)
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")
    
    history = area.get('detection_history', [])
    # Return most recent first
    history = list(reversed(history[-limit:]))
    
    return JSONResponse(content={
        "area_id": area_id,
        "area_name": area['name'],
        "detection_history": history,
        "total_detections": len(area.get('detection_history', []))
    })


@router.post("/auto-scan")
async def auto_scan_all_areas(background_tasks: BackgroundTasks):
    """
    Triggered on user login.  For every area with active_monitoring=True:
      1. Determine the date range  (last_monitored → today, or last 30 days if never run).
      2. Download new satellite imagery via the ML pipeline.
      3. Run change detection.
      4. Persist the result to detection history.
      5. Return structured alerts for any areas where deforestation was found.
    """
    try:
        all_areas = area_manager.get_all_areas()
        active = [a for a in all_areas if a.get('active_monitoring')]

        if not active:
            return JSONResponse(content={
                "scanned": 0,
                "alerts": [],
                "message": "No areas with active monitoring found."
            })

        alerts = []
        scanned = 0
        errors = []
        today = datetime.now().date()

        for area in active:
            area_id = area['id']
            area_name = area.get('name', area_id)

            # Determine date window -------------------------------------------
            last_str = area.get('last_monitored')
            if last_str:
                try:
                    last_date = datetime.fromisoformat(str(last_str)).date()
                except Exception:
                    last_date = today - timedelta(days=30)
            else:
                last_date = today - timedelta(days=30)

            # Need at least 1 day gap for imagery availability
            if (today - last_date).days < 1:
                logger.info(f"[auto-scan] {area_name}: checked too recently, skipping.")
                continue

            before_date = str(last_date)
            after_date = str(today)

            # Calculate bounding box from polygon coordinates -----------------
            coords = area.get('coordinates', [])
            if not coords or len(coords) < 3:
                errors.append({"area": area_name, "error": "Invalid coordinates"})
                continue

            lats = [c[0] for c in coords]
            lngs = [c[1] for c in coords]
            west, east = min(lngs), max(lngs)
            south, north = min(lats), max(lats)

            logger.info(f"[auto-scan] Running detection for '{area_name}' ({before_date} → {after_date})")

            try:
                result = await detect_change_auto_internal(
                    before_date=before_date,
                    after_date=after_date,
                    west=west,
                    south=south,
                    east=east,
                    north=north,
                    max_cloud_cover=80.0,   # permissive for automated scans
                    window_days=30,
                    ignore_seasonal_check=True,
                )
                scanned += 1

                # Persist to history
                area_manager.add_detection_record(area_id, result)

                if result.get('deforestation_detected'):
                    change = result.get('change', {})
                    alerts.append({
                        "area_id": area_id,
                        "area_name": area_name,
                        "before_date": before_date,
                        "after_date": after_date,
                        "forest_loss_percent": change.get('forest_loss_percent', 0),
                        "vegetation_trend": change.get('vegetation_trend', 'decline'),
                        "severity": (
                            "critical" if abs(change.get('forest_loss_percent', 0)) >= 40
                            else "high" if abs(change.get('forest_loss_percent', 0)) >= 20
                            else "medium" if abs(change.get('forest_loss_percent', 0)) >= 10
                            else "low"
                        ),
                        "scanned_at": datetime.now().isoformat(),
                    })

            except Exception as e:
                logger.error(f"[auto-scan] Detection failed for '{area_name}': {e}")
                errors.append({"area": area_name, "error": str(e)})

        return JSONResponse(content={
            "scanned": scanned,
            "alerts": alerts,
            "errors": errors,
            "deforestation_found": len(alerts) > 0,
            "message": (
                f"⚠️ Deforestation detected in {len(alerts)} area(s)!" if alerts
                else f"✅ All {scanned} area(s) scanned — no new deforestation detected."
            ),
            "scanned_at": datetime.now().isoformat(),
        })

    except Exception as e:
        logger.error(f"[auto-scan] Fatal error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{area_id}/hotspots")
async def get_deforestation_hotspots(area_id: str):
    """
    Returns generated deforestation hotspot markers inside the monitored polygon.
    Points are deterministically seeded from the area_id so they remain consistent
    across page loads. Count and severity are proportional to historical forest loss.
    """
    area = area_manager.get_area(area_id)
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")

    hotspots = _generate_hotspots(area)
    return JSONResponse(content={
        "area_id": area_id,
        "area_name": area.get('name', ''),
        "hotspots": hotspots,
        "count": len(hotspots),
    })
