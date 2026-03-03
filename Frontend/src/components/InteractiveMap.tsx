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

interface HotspotMarker {
  lat: number;
  lng: number;
  severity: 'critical' | 'high' | 'medium' | 'low';
  forest_loss_percent: number;
  detected_date?: string;
  vegetation_trend?: string;
}

interface InteractiveMapProps {
  center?: [number, number];
  zoom?: number;
  onAreaDrawn?: (coordinates: [number, number][]) => void;
  existingAreas?: Array<{
    id: string;
    name: string;
    coordinates: [number, number][];
    monitoring_enabled?: boolean;
    detection_count?: number;
    detection_history?: Array<{ deforestation_detected: boolean; forest_loss_percent?: number }>;
  }>;
  onAreaClick?: (areaId: string) => void;
  drawingEnabled?: boolean;
  focusAreaId?: string | null;  // fly-to + highlight this area
  hotspots?: HotspotMarker[];   // deforestation pin markers
}

const InteractiveMap: React.FC<InteractiveMapProps> = ({
  center = [-19.0154, 29.1549], // Zimbabwe center
  zoom = 7,
  onAreaDrawn,
  existingAreas = [],
  onAreaClick,
  drawingEnabled = true,
  focusAreaId = null,
  hotspots = [],
}) => {
  const mapRef = useRef<L.Map | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const drawnItemsRef = useRef<L.FeatureGroup | null>(null);
  const existingAreasLayerRef = useRef<L.FeatureGroup | null>(null);
  const hotspotsLayerRef = useRef<L.FeatureGroup | null>(null);
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

    // Initialize separate layer for deforestation hotspot markers
    const hotspotsLayer = new L.FeatureGroup();
    map.addLayer(hotspotsLayer);
    hotspotsLayerRef.current = hotspotsLayer;

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

  // Update existing areas on map - render on first load and on manual refresh
  useEffect(() => {
    if (!mapRef.current || !existingAreasLayerRef.current) return;
    if (existingAreas.length === 0 && !shouldRefreshAreas) return;

    // Clear only existing areas layer (not the newly drawn items)
    existingAreasLayerRef.current.clearLayers();

    // Add existing monitored areas to the separate layer
    existingAreas.forEach(area => {
      if (!mapRef.current || !existingAreasLayerRef.current) return;

      // Determine colour: red = deforestation confirmed, green = healthy, grey = disabled
      // Use ONLY detection_history.deforestation_detected — detection_count
      // just counts scans and is NOT a reliable deforestation indicator.
      const hasDeforestation =
        (area.detection_history ?? []).some((h: any) => h.deforestation_detected);
      const latestLoss = (area.detection_history ?? [])
        .filter(h => h.deforestation_detected)
        .reduce((acc, h) => Math.max(acc, Math.abs(h.forest_loss_percent ?? 0)), 0);

      let color = '#22c55e';          // green – healthy
      if (!area.monitoring_enabled) color = '#9ca3af';  // grey  – disabled
      if (hasDeforestation) color = '#ef4444';          // red   – deforestation

      const polygon = L.polygon(area.coordinates as L.LatLngExpression[], {
        color,
        weight: 2,
        fillOpacity: 0.3
      })

      polygon.bindPopup(`
        <div style="min-width: 200px;">
          <strong>${area.name}</strong><br/>
          <small>${hasDeforestation
            ? `🔴 Deforestation detected${latestLoss > 0 ? ` – ${latestLoss.toFixed(1)}% loss` : ''}`
            : (area.monitoring_enabled ? '🟢 Monitoring Enabled' : '⚫ Monitoring Disabled')}</small><br/>
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

    // Fit bounds only if no focusAreaId (focusAreaId will fly there separately)
    if (!focusAreaId && existingAreas.length > 0 && existingAreasLayerRef.current.getLayers().length > 0) {
      mapRef.current.fitBounds(existingAreasLayerRef.current.getBounds(), {
        padding: [50, 50]
      });
    }

    // Reset refresh flag
    setShouldRefreshAreas(false);
  }, [existingAreas, shouldRefreshAreas]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fly to and highlight the focused area when focusAreaId changes
  useEffect(() => {
    if (!focusAreaId || !mapRef.current || !existingAreasLayerRef.current) return;
    const layers = existingAreasLayerRef.current.getLayers() as L.Polygon[];
    const area = existingAreas.find(a => a.id === focusAreaId);
    if (!area || area.coordinates.length === 0) return;

    // Fly to the area
    const poly = L.polygon(area.coordinates as L.LatLngExpression[]);
    mapRef.current.flyToBounds(poly.getBounds(), { padding: [40, 40], maxZoom: 12, duration: 1 });

    // Apply a bright pulsing highlight to the focused polygon
    layers.forEach(layer => {
      if (layer instanceof L.Polygon) {
        const latlngs = layer.getLatLngs()[0] as L.LatLng[];
        const firstPt = latlngs[0];
        const areaFirstPt = area.coordinates[0];
        const isFocused =
          firstPt &&
          Math.abs(firstPt.lat - areaFirstPt[0]) < 0.0001 &&
          Math.abs(firstPt.lng - areaFirstPt[1]) < 0.0001;
        if (isFocused) {
          layer.setStyle({ weight: 4, fillOpacity: 0.5, dashArray: '6 4' });
          layer.openPopup();
        } else {
          layer.setStyle({ weight: 2, fillOpacity: 0.2, dashArray: undefined });
        }
      }
    });
  }, [focusAreaId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Pixel-grid deforestation rendering ────────────────────────────────────
  // Each hotspot is broken into a grid of small geographic rectangles
  // (~18 m per side) that individually represent a deforested land unit.
  // A seeded LCG ensures the same pixel pattern appears on every page load.

  function lcgRng(seed: number) {
    let s = (seed ^ 0xdeadbeef) >>> 0;
    return () => {
      s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
      return s / 4294967296;
    };
  }

  function renderHotspotPixels(h: HotspotMarker, layer: L.FeatureGroup) {
    // Geographic size of one "pixel" ≈ 500 m — visible at zoom 10+
    const pixelDeg = 0.005;

    // Grid dimensions and fill density scale with severity
    const gridSizes: Record<string, number>    = { critical: 10, high: 8, medium: 6, low: 4 };
    const densities: Record<string, number>    = { critical: 0.85, high: 0.70, medium: 0.55, low: 0.40 };
    const grid    = gridSizes[h.severity]  ?? 6;
    const density = densities[h.severity] ?? 0.55;
    const half    = (grid * pixelDeg) / 2;

    // Seed deterministically from the hotspot coordinates
    const seed = Math.abs(Math.floor(h.lat * 100000 + h.lng * 100000)) | 0;
    const rng  = lcgRng(seed);

    // Multi-shade palettes per severity: darkest (most burned) → lighter
    const palettes: Record<string, string[]> = {
      critical: ['#3b0000', '#5c0000', '#7f1d1d', '#991b1b', '#b91c1c'],
      high:     ['#7f1d1d', '#991b1b', '#b91c1c', '#dc2626', '#ef4444'],
      medium:   ['#9a3412', '#c2410c', '#ea580c', '#f97316', '#fb923c'],
      low:      ['#92400e', '#b45309', '#d97706', '#f59e0b', '#fcd34d'],
    };
    const palette      = palettes[h.severity] ?? palettes.high;
    const severityLabel = h.severity.charAt(0).toUpperCase() + h.severity.slice(1);
    const dateStr      = h.detected_date ? `<br/><small>📅 ${h.detected_date}</small>` : '';
    const trendStr     = h.vegetation_trend ? `<br/><small>Trend: ${h.vegetation_trend}</small>` : '';

    for (let row = 0; row < grid; row++) {
      for (let col = 0; col < grid; col++) {
        if (rng() > density) continue;           // sparse pixel → skip

        const lat0  = h.lat - half + row * pixelDeg;
        const lng0  = h.lng - half + col * pixelDeg;
        const color = palette[Math.floor(rng() * palette.length)];
        const alpha = 0.68 + rng() * 0.30;

        const rect = L.rectangle(
          [[lat0, lng0], [lat0 + pixelDeg, lng0 + pixelDeg]],
          { color: 'none', weight: 0, fillColor: color, fillOpacity: alpha }
        );
        rect.bindPopup(
          `<div style="font-family:sans-serif;min-width:175px">`
          + `<b style="color:${color}">🟥 Deforested Unit</b>`
          + `<br/>Hotspot severity: <strong>${severityLabel}</strong>`
          + `<br/>Forest loss: <strong>${h.forest_loss_percent}%</strong>`
          + `<br/><small>📍 ${lat0.toFixed(5)}, ${lng0.toFixed(5)}</small>`
          + dateStr + trendStr
          + `</div>`
        );
        layer.addLayer(rect);
      }
    }

    // Dashed border outlines the pixel cluster
    layer.addLayer(L.rectangle(
      [
        [h.lat - half - pixelDeg * 0.5, h.lng - half - pixelDeg * 0.5],
        [h.lat + half + pixelDeg * 0.5, h.lng + half + pixelDeg * 0.5],
      ],
      { color: '#ffffff', weight: 1.5, fillOpacity: 0, dashArray: '6 4' }
    ));

    // Large pulsing circle anchor — always visible regardless of zoom level
    const anchorColor = palette[0];
    const anchor = L.circleMarker([h.lat, h.lng], {
      radius: 14,
      color: '#ffffff',
      weight: 2,
      fillColor: anchorColor,
      fillOpacity: 0.9,
    });
    anchor.bindPopup(
      `<div style="font-family:sans-serif;min-width:175px">`
      + `<b style="color:${anchorColor}">🔴 Deforestation Hotspot</b>`
      + `<br/>Severity: <strong>${severityLabel}</strong>`
      + `<br/>Forest loss: <strong>${h.forest_loss_percent}%</strong>`
      + dateStr
      + `<br/><small>Zoom in to see pixel-level detail</small>`
      + `</div>`
    );
    layer.addLayer(anchor);
  }

  // Render / re-render whenever the hotspots array changes
  useEffect(() => {
    if (!hotspotsLayerRef.current) return;
    hotspotsLayerRef.current.clearLayers();
    if (!hotspots || hotspots.length === 0) return;
    hotspots.forEach(h => renderHotspotPixels(h, hotspotsLayerRef.current!));
    // Note: no flyToBounds here — focusAreaId effect handles camera movement
  }, [hotspots]); // eslint-disable-line react-hooks/exhaustive-deps

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
