"""
Simple script to start the API server with better error handling
"""
import uvicorn
import sys
from pathlib import Path

if __name__ == "__main__":
    try:
        print("🚀 Starting FastAPI backend server...")
        print("📍 API will be available at: http://127.0.0.1:8001")
        print("📊 Endpoints:")
        print("   - http://127.0.0.1:8001/api/detection/alerts")
        print("   - http://127.0.0.1:8001/api/detection/report")
        print("   - http://127.0.0.1:8001/api/map/with-detections")
        print("\n⏹️  Press Ctrl+C to stop the server\n")
        
        uvicorn.run(
            "api_server:app",
            host="127.0.0.1",
            port=8001,
            reload=False,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)
