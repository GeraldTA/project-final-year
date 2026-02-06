import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet-draw/dist/leaflet.draw.css';
import 'leaflet-draw';

// Fix for default marker icons in Leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

interface InteractiveMapProps {
  center?: [number, number];
  zoom?: number;
  onAreaDrawn?: (coordinates: [number, number][]) => void;
  existingAreas?: Array<{
    id: string;
    name: string;
    coordinates: [number, number][];
    monitoring_enabled?: boolean;
  }>;
  onAreaClick?: (areaId: string) => void;
  drawingEnabled?: boolean;
}

const InteractiveMap: React.FC<InteractiveMapProps> = ({
  center = [-19.0154, 29.1549], // Zimbabwe center
  zoom = 7,
  onAreaDrawn,
  existingAreas = [],
  onAreaClick,
  drawingEnabled = true
}) => {
  const mapRef = useRef<L.Map | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const drawnItemsRef = useRef<L.FeatureGroup | null>(null);
  const existingAreasLayerRef = useRef<L.FeatureGroup | null>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawMode, setDrawMode] = useState<string>('');
  const [mousePosition, setMousePosition] = useState<{lat: number, lng: number} | null>(null);
  const [rectanglePoints, setRectanglePoints] = useState<L.LatLng[]>([]);
  const tempLayerRef = useRef<L.Polyline | null>(null);
  const [shouldRefreshAreas, setShouldRefreshAreas] = useState(false);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    // Initialize map with specific options for better drawing
    const map = L.map(mapContainerRef.current, {
      preferCanvas: false,
      zoomControl: true,
      attributionControl: true,
      dragging: true,
      touchZoom: true,
      scrollWheelZoom: true,
      doubleClickZoom: true,
      boxZoom: true,
      keyboard: true,
      tap: true
    }).setView(center, zoom);
    mapRef.current = map;

    // Add tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    // Ensure map container is ready for interaction
    setTimeout(() => {
      map.invalidateSize();
      
      // Force enable pointer events on all panes
      const container = map.getContainer();
      const panes = container.querySelectorAll('.leaflet-pane');
      panes.forEach((pane) => {
        (pane as HTMLElement).style.pointerEvents = 'auto';
      });
    }, 100);

    // Initialize feature group for drawn items (new drawings)
    const drawnItems = new L.FeatureGroup();
    map.addLayer(drawnItems);
    drawnItemsRef.current = drawnItems;

    // Initialize separate layer for existing areas
    const existingAreasLayer = new L.FeatureGroup();
    map.addLayer(existingAreasLayer);
    existingAreasLayerRef.current = existingAreasLayer;

    if (drawingEnabled) {
      // Custom 4-point rectangle drawing
      let points: L.LatLng[] = [];
      let markers: L.CircleMarker[] = [];
      let lines: L.Polyline[] = [];
      
      const startCustomRectangle = () => {
        setIsDrawing(true);
        setDrawMode('4-point rectangle');
        points = [];
        markers = [];
        lines = [];
        
        const handleMapClick = (e: L.LeafletMouseEvent) => {
          points.push(e.latlng);
          
          // Draw marker at clicked point
          const marker = L.circleMarker(e.latlng, {
            radius: 6,
            color: '#4ECDC4',
            fillColor: '#4ECDC4',
            fillOpacity: 1,
            weight: 2
          }).addTo(map);
          markers.push(marker);
          
          // Draw line connecting to previous point
          if (points.length > 1) {
            const line = L.polyline([points[points.length - 2], points[points.length - 1]], { 
              color: '#4ECDC4', 
              weight: 3,
              dashArray: '5, 5'
            }).addTo(map);
            lines.push(line);
          }
          
          setRectanglePoints([...points]);
          
          // When 4 points are clicked, close the shape
          if (points.length === 4) {
            // Draw closing line from point 4 to point 1
            const closingLine = L.polyline([points[3], points[0]], { 
              color: '#4ECDC4', 
              weight: 3,
              dashArray: '5, 5'
            }).addTo(map);
            
            setTimeout(() => {
              // Create final polygon
              const polygon = L.polygon(points, {
                color: '#4ECDC4',
                weight: 4,
                fillOpacity: 0.35,
                fillColor: '#4ECDC4'
              });
              
              drawnItemsRef.current?.addLayer(polygon);
              
              // Extract coordinates for callback
              const coordinates: [number, number][] = points.map(p => [p.lat, p.lng]);
              if (onAreaDrawn) {
                onAreaDrawn(coordinates);
              }
              
              // Clean up temporary markers and lines
              markers.forEach(m => map.removeLayer(m));
              lines.forEach(l => map.removeLayer(l));
              map.removeLayer(closingLine);
              
              // Reset
              map.off('click', handleMapClick);
              setIsDrawing(false);
              setDrawMode('');
              setRectanglePoints([]);
              points = [];
              markers = [];
              lines = [];
            }, 300);
          }
        };
        
        map.on('click', handleMapClick);
      };
      
      // Add custom control button
      const CustomControl = L.Control.extend({
        onAdd: function() {
          const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
          container.style.backgroundColor = 'white';
          container.style.width = '30px';
          container.style.height = '30px';
          container.style.cursor = 'pointer';
          container.innerHTML = '<div style="width:30px;height:30px;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:bold;">□</div>';
          container.title = 'Draw 4-point rectangle';
          
          L.DomEvent.on(container, 'click', (e) => {
            L.DomEvent.stopPropagation(e);
            L.DomEvent.preventDefault(e);
            startCustomRectangle();
          });
          
          return container;
        }
      });
      
      map.addControl(new CustomControl({ position: 'topright' }));
      
      // Add delete/clear button
      const DeleteControl = L.Control.extend({
        onAdd: function() {
          const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
          container.style.backgroundColor = 'white';
          container.style.width = '30px';
          container.style.height = '30px';
          container.style.cursor = 'pointer';
          container.innerHTML = '<div style="width:30px;height:30px;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:bold;color:#e74c3c;">🗑️</div>';
          container.title = 'Delete last drawing';
          
          L.DomEvent.on(container, 'click', (e) => {
            L.DomEvent.stopPropagation(e);
            L.DomEvent.preventDefault(e);
            
            // Remove the last drawn shape
            if (drawnItemsRef.current) {
              const layers = drawnItemsRef.current.getLayers();
              if (layers.length > 0) {
                const lastLayer = layers[layers.length - 1];
                drawnItemsRef.current.removeLayer(lastLayer);
                console.log('🗑️ Deleted last drawing');
              }
            }
          });
          
          return container;
        }
      });
      
      map.addControl(new DeleteControl({ position: 'topright' }));
      
      // Add refresh button
      const RefreshControl = L.Control.extend({
        onAdd: function() {
          const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
          container.style.backgroundColor = 'white';
          container.style.width = '30px';
          container.style.height = '30px';
          container.style.cursor = 'pointer';
          container.innerHTML = '<div style="width:30px;height:30px;display:flex;align-items:center;justify-content:center;font-size:16px;">🔄</div>';
          container.title = 'Refresh map areas';
          
          L.DomEvent.on(container, 'click', (e) => {
            L.DomEvent.stopPropagation(e);
            L.DomEvent.preventDefault(e);
            setShouldRefreshAreas(true);
            console.log('🔄 Refreshing map areas');
          });
          
          return container;
        }
      });
      
      map.addControl(new RefreshControl({ position: 'topright' }));
    }

    // Cleanup
    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Update existing areas on map - ONLY when manually refreshed
  useEffect(() => {
    if (!mapRef.current || !existingAreasLayerRef.current || !shouldRefreshAreas) return;

    // Clear only existing areas layer (not the newly drawn items)
    existingAreasLayerRef.current.clearLayers();

    // Add existing monitored areas to the separate layer
    existingAreas.forEach(area => {
      if (!mapRef.current || !existingAreasLayerRef.current) return;

      const polygon = L.polygon(area.coordinates as L.LatLngExpression[], {
        color: area.monitoring_enabled ? '#22c55e' : '#9ca3af',
        weight: 2,
        fillOpacity: 0.3
      });

      polygon.bindPopup(`
        <div style="min-width: 200px;">
          <strong>${area.name}</strong><br/>
          <small>${area.monitoring_enabled ? '🟢 Monitoring Enabled' : '⚫ Monitoring Disabled'}</small><br/>
          <button 
            onclick="window.dispatchEvent(new CustomEvent('area-click', { detail: '${area.id}' }))"
            style="margin-top: 8px; padding: 4px 12px; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;"
          >
            View Details
          </button>
        </div>
      `);

      existingAreasLayerRef.current.addLayer(polygon);

      // Handle click events
      polygon.on('click', () => {
        if (onAreaClick) {
          onAreaClick(area.id);
        }
      });
    });

    // Fit bounds if there are areas
    if (existingAreas.length > 0 && existingAreasLayerRef.current.getLayers().length > 0) {
      mapRef.current.fitBounds(existingAreasLayerRef.current.getBounds(), {
        padding: [50, 50]
      });
    }
    
    // Reset refresh flag
    setShouldRefreshAreas(false);
  }, [shouldRefreshAreas]); // Only refresh when manually triggered

  // Handle custom area-click events from popup buttons
  useEffect(() => {
    const handleAreaClick = (event: Event) => {
      const customEvent = event as CustomEvent;
      if (onAreaClick && customEvent.detail) {
        onAreaClick(customEvent.detail);
      }
    };

    window.addEventListener('area-click', handleAreaClick as EventListener);
    return () => {
      window.removeEventListener('area-click', handleAreaClick as EventListener);
    };
  }, [onAreaClick]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainerRef} className="w-full h-full rounded-lg" style={{ minHeight: '600px' }} />
      
      {/* Debug Panel */}
      {isDrawing && mousePosition && (
        <div className="absolute bottom-4 left-4 bg-black bg-opacity-75 text-white px-4 py-2 rounded-lg shadow-xl z-[1000] font-mono text-xs">
          <div><strong>Mode:</strong> {drawMode}</div>
          <div><strong>Lat:</strong> {mousePosition.lat.toFixed(6)}</div>
          <div><strong>Lng:</strong> {mousePosition.lng.toFixed(6)}</div>
          <div className="text-green-400 mt-1">✓ Mouse tracking active</div>
        </div>
      )}
      
      {isDrawing && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-3 rounded-lg shadow-xl z-[1000] border-2 border-white">
          <div className="flex items-center gap-2">
            <span className="text-2xl animate-pulse">🖊️</span>
            <div>
              <div className="font-bold text-lg">Click 4 Corners</div>
              <div className="text-sm text-blue-100 mt-1">
                <strong>Points: {rectanglePoints.length}/4</strong><br/>
                Click on the map to place each corner
              </div>
            </div>
          </div>
        </div>
      )}
      {drawingEnabled && !isDrawing && (
        <div className="absolute top-4 right-20 bg-white text-gray-700 px-4 py-2 rounded-lg shadow-lg z-[999] border border-gray-300">
          <div className="text-xs">
            <div className="font-bold mb-1">📍 Draw a Rectangle:</div>
            <div>1. Click the <strong>□</strong> button (top right)</div>
            <div>2. Click <strong>4 corners</strong> on the map</div>
            <div>3. Shape auto-completes after 4th corner</div>
            <div className="mt-2 pt-2 border-t border-gray-300">
              <div className="text-red-600 font-semibold">🗑️ Delete: Click trash icon</div>
              <div className="text-blue-600 font-semibold">🔄 Refresh: Click refresh icon</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default InteractiveMap;
