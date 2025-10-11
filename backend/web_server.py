"""
Simple web server to host the deforestation visualization map.
This will serve your map on a local web server that you can access from any browser.
"""

import http.server
import socketserver
import webbrowser
import os
from pathlib import Path
import threading
import time

def start_web_server(port=8080):
    """Start a web server to host the deforestation maps."""
    
    # Change to the deforestation_maps directory
    maps_dir = Path('deforestation_maps')
    if not maps_dir.exists():
        print("Error: deforestation_maps directory not found")
        print("Run 'python deforestation_visualizer.py' first")
        return
    
    os.chdir(maps_dir)
    
    # Set up the server
    Handler = http.server.SimpleHTTPRequestHandler
    
    try:
        with socketserver.TCPServer(("", port), Handler) as httpd:
            print(f"🌐 Starting web server...")
            print(f"📍 Serving deforestation maps at: http://localhost:{port}")
            print(f"📊 Main map: http://localhost:{port}/deforestation_map.html")
            print(f"📋 Report: http://localhost:{port}/deforestation_report.json")
            print(f"📍 Coordinates: http://localhost:{port}/deforestation_coordinates.json")
            print()
            print("🖱️ Opening map in your default browser...")
            print("⏹️ Press Ctrl+C to stop the server")
            
            # Open the map in browser after a short delay
            def open_browser():
                time.sleep(2)
                webbrowser.open(f'http://localhost:{port}/deforestation_map.html')
            
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()
            
            # Start serving
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {port} is already in use")
            print(f"💡 Try a different port: python web_server.py --port 8081")
        else:
            print(f"❌ Server error: {e}")

def main():
    """Main function."""
    import sys
    
    port = 8080
    
    # Check for custom port
    if len(sys.argv) > 1:
        if sys.argv[1] == '--port' and len(sys.argv) > 2:
            try:
                port = int(sys.argv[2])
            except ValueError:
                print("Invalid port number")
                return
    
    print("🗺️ DEFORESTATION MAP WEB SERVER")
    print("=" * 50)
    
    start_web_server(port)

if __name__ == "__main__":
    main()
