#!/usr/bin/env python3
"""
Automated Map Updater - Runs on schedule to keep maps current
Updates NDVI tiles and map visualizations with latest satellite data
"""

import json
import schedule
import time
from datetime import datetime, timedelta
from pathlib import Path
from gee_processor import GEESentinelProcessor
from realistic_photo_processor import RealisticPhotoProcessor

class AutomatedMapUpdater:
    """Automatically updates maps with latest satellite data."""
    
    def __init__(self):
        """Initialize the automated updater."""
        self.backend_dir = Path(__file__).parent
        self.tiles_file = self.backend_dir / "fresh_tile_urls.json"
        self.last_update_file = self.backend_dir / "last_update.json"
        self.gee = GEESentinelProcessor()
        self.photo_processor = RealisticPhotoProcessor()
        
    def update_maps(self):
        """Update maps with latest satellite imagery."""
        try:
            print(f"\n{'='*60}")
            print(f"🌍 Starting Automated Map Update - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}\n")
            
            # Calculate dates for comparison (use safer ranges to ensure data availability)
            # Sentinel-2 has 5-day revisit, but processing takes time
            # Use data from 10-100 days ago for before, and 10 days ago for after
            after_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
            before_date = (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d')
            
            print(f"📅 Fetching imagery:")
            print(f"   Before: {before_date} (90 days ago)")
            print(f"   After:  {after_date} (10 days ago)")
            print(f"   Note: Using slightly older dates to ensure data availability\n")
            
            # Generate fresh NDVI tiles
            print(f"🛰️  Generating fresh NDVI tiles from Google Earth Engine...")
            tiles = self.gee.create_ndvi_map_tiles(
                before_date=before_date,
                after_date=after_date
            )
            
            if not tiles:
                print("❌ Failed to generate tiles")
                print("💡 This may be due to cloud cover or data availability")
                print("💡 Try adjusting dates or check Google Earth Engine status")
                return False
            
            print(f"✅ Successfully generated {len(tiles)} tile layers")
            
            # Save tiles
            with open(self.tiles_file, 'w') as f:
                json.dump(tiles, f, indent=2)
            print(f"💾 Saved tiles to {self.tiles_file}")
            
            # Update last update timestamp
            update_info = {
                'last_update': datetime.now().isoformat(),
                'before_date': before_date,
                'after_date': after_date,
                'tiles_count': len(tiles)
            }
            with open(self.last_update_file, 'w') as f:
                json.dump(update_info, f, indent=2)
            
            print(f"\n{'='*60}")
            print(f"✅ Map Update Complete!")
            print(f"{'='*60}\n")
            return True
            
        except Exception as e:
            print(f"❌ Update failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_last_update_info(self):
        """Get information about the last update."""
        if self.last_update_file.exists():
            with open(self.last_update_file, 'r') as f:
                return json.load(f)
        return None
    
    def start_scheduled_updates(self, interval_days=5):
        """
        Start scheduled automatic updates.
        
        Args:
            interval_days: Number of days between updates (default: 5 days for Sentinel-2 revisit)
        """
        print(f"\n🔄 Starting Automated Map Updater")
        print(f"📅 Update Interval: Every {interval_days} days")
        print(f"🕐 Next update: {interval_days} days from now")
        print(f"\n{'='*60}\n")
        
        # Run initial update
        self.update_maps()
        
        # Schedule future updates
        schedule.every(interval_days).days.do(self.update_maps)
        
        print(f"⏰ Scheduler running... (Press Ctrl+C to stop)")
        
        while True:
            schedule.run_pending()
            time.sleep(3600)  # Check every hour
    
    def force_update_now(self):
        """Force an immediate update regardless of schedule."""
        print(f"\n🔄 Force Update Requested")
        return self.update_maps()


def main():
    """Main entry point for automated updater."""
    import sys
    
    updater = AutomatedMapUpdater()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--now':
            # Run update immediately and exit
            success = updater.force_update_now()
            sys.exit(0 if success else 1)
        elif sys.argv[1] == '--status':
            # Show last update info
            info = updater.get_last_update_info()
            if info:
                print(f"\n📊 Last Update Status:")
                print(f"   Time: {info['last_update']}")
                print(f"   Before Date: {info['before_date']}")
                print(f"   After Date: {info['after_date']}")
                print(f"   Tiles Generated: {info['tiles_count']}")
            else:
                print(f"\n❌ No update history found")
            sys.exit(0)
        elif sys.argv[1] == '--help':
            print(f"\nAutomated Map Updater")
            print(f"{'='*60}")
            print(f"\nUsage:")
            print(f"  python automated_updater.py              Start scheduled updates (every 5 days)")
            print(f"  python automated_updater.py --now        Run update immediately and exit")
            print(f"  python automated_updater.py --status     Show last update information")
            print(f"  python automated_updater.py --help       Show this help message")
            sys.exit(0)
    
    # Default: start scheduled updates
    try:
        updater.start_scheduled_updates(interval_days=5)
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Automated updater stopped by user")
        sys.exit(0)


if __name__ == '__main__':
    main()
