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
  const [isDrawing, setIsDrawing] = useState(false);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    // Initialize map
    const map = L.map(mapContainerRef.current).setView(center, zoom);
    mapRef.current = map;

    // Add tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    // Initialize feature group for drawn items
    const drawnItems = new L.FeatureGroup();
    map.addLayer(drawnItems);
    drawnItemsRef.current = drawnItems;

    if (drawingEnabled) {
      // Add drawing control
      const drawControl = new L.Control.Draw({
        position: 'topright',
        draw: {
          polygon: {
            allowIntersection: false,
            drawError: {
              color: '#e74c3c',
              message: '<strong>Error:</strong> Shape edges cannot cross!'
            },
            shapeOptions: {
              color: '#3388ff',
              weight: 3,
              fillOpacity: 0.2
            }
          },
          rectangle: {
            shapeOptions: {
              color: '#3388ff',
              weight: 3,
              fillOpacity: 0.2
            }
          },
          circle: false,
          circlemarker: false,
          marker: false,
          polyline: false
        },
        edit: {
          featureGroup: drawnItems,
          remove: true
        }
      });
      map.addControl(drawControl);

      // Handle polygon creation
      map.on(L.Draw.Event.CREATED, (event: any) => {
        const layer = event.layer;
        drawnItems.addLayer(layer);

        // Extract coordinates
        const coordinates: [number, number][] = [];
        if (event.layerType === 'polygon' || event.layerType === 'rectangle') {
          const latLngs = layer.getLatLngs()[0];
          latLngs.forEach((latLng: L.LatLng) => {
            coordinates.push([latLng.lat, latLng.lng]);
          });
        }

        if (onAreaDrawn && coordinates.length > 0) {
          onAreaDrawn(coordinates);
        }

        setIsDrawing(false);
      });

      map.on(L.Draw.Event.DRAWSTART, () => {
        setIsDrawing(true);
      });

      map.on(L.Draw.Event.DRAWSTOP, () => {
        setIsDrawing(false);
      });
    }

    // Cleanup
    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Update existing areas on map
  useEffect(() => {
    if (!mapRef.current || !drawnItemsRef.current) return;

    // Clear existing layers
    drawnItemsRef.current.clearLayers();

    // Add existing monitored areas
    existingAreas.forEach(area => {
      if (!mapRef.current || !drawnItemsRef.current) return;

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

      drawnItemsRef.current.addLayer(polygon);

      // Handle click events
      polygon.on('click', () => {
        if (onAreaClick) {
          onAreaClick(area.id);
        }
      });
    });

    // Fit bounds if there are areas
    if (existingAreas.length > 0 && drawnItemsRef.current.getLayers().length > 0) {
      mapRef.current.fitBounds(drawnItemsRef.current.getBounds(), {
        padding: [50, 50]
      });
    }
  }, [existingAreas, onAreaClick]);

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
      {isDrawing && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-blue-600 text-white px-4 py-2 rounded-lg shadow-lg z-[1000]">
          🖊️ Click on the map to draw your monitoring area
        </div>
      )}
    </div>
  );
};

export default InteractiveMap;
