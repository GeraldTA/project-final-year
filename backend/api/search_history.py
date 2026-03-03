"""
API endpoints for search history
Provides access to search history data and statistics
"""
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from services.search_history_manager import SearchHistoryManager
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/search-history", tags=["Search History"])

# Initialize search history manager
search_history_manager = SearchHistoryManager()


@router.get("/recent")
def get_recent_searches(
    limit: int = Query(50, ge=1, le=100, description="Number of recent searches to retrieve")
):
    """Get recent search history"""
    try:
        searches = search_history_manager.get_recent_searches(limit=limit)
        return JSONResponse({
            "success": True,
            "count": len(searches),
            "searches": searches
        })
    except Exception as e:
        logger.error(f"Error retrieving recent searches: {e}")
        return JSONResponse({
            "success": False,
            "message": str(e)
        }, status_code=500)


@router.get("/popular")
def get_popular_searches(
    limit: int = Query(10, ge=1, le=50, description="Number of popular searches to retrieve"),
    days: int = Query(30, ge=1, le=365, description="Look back period in days")
):
    """Get most popular search queries"""
    try:
        popular = search_history_manager.get_popular_searches(limit=limit, days=days)
        return JSONResponse({
            "success": True,
            "period_days": days,
            "count": len(popular),
            "popular_searches": popular
        })
    except Exception as e:
        logger.error(f"Error retrieving popular searches: {e}")
        return JSONResponse({
            "success": False,
            "message": str(e)
        }, status_code=500)


@router.get("/stats")
def get_search_statistics():
    """Get overall search statistics"""
    try:
        stats = search_history_manager.get_search_stats()
        return JSONResponse({
            "success": True,
            "statistics": stats
        })
    except Exception as e:
        logger.error(f"Error retrieving search stats: {e}")
        return JSONResponse({
            "success": False,
            "message": str(e)
        }, status_code=500)


@router.get("/nearby")
def get_nearby_searches(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius_km: float = Query(10, ge=1, le=100, description="Search radius in kilometers")
):
    """Find searches near a specific location"""
    try:
        searches = search_history_manager.search_by_location(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km
        )
        return JSONResponse({
            "success": True,
            "center": {"latitude": latitude, "longitude": longitude},
            "radius_km": radius_km,
            "count": len(searches),
            "searches": searches
        })
    except Exception as e:
        logger.error(f"Error searching nearby history: {e}")
        return JSONResponse({
            "success": False,
            "message": str(e)
        }, status_code=500)


@router.delete("/cleanup")
def cleanup_old_history(
    days: int = Query(90, ge=30, le=365, description="Delete searches older than this many days")
):
    """Delete old search history (admin endpoint)"""
    try:
        rows_deleted = search_history_manager.clear_old_history(days=days)
        return JSONResponse({
            "success": True,
            "message": f"Deleted {rows_deleted} search records older than {days} days",
            "rows_deleted": rows_deleted
        })
    except Exception as e:
        logger.error(f"Error cleaning up history: {e}")
        return JSONResponse({
            "success": False,
            "message": str(e)
        }, status_code=500)
