import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Alert, DetectionData, Region } from '../types';
import { generateMockData } from '../utils/mockData';
import { apiFetch } from '../utils/api';

interface DataContextType {
  selectedRegion: Region;
  setSelectedRegion: (region: Region) => void;
  selectedDate: Date;
  setSelectedDate: (date: Date) => void;
  alerts: Alert[];
  setAlerts: (alerts: Alert[]) => void;
  detectionData: DetectionData | null;
  loading: boolean;
  refreshData: () => void;
}

const DataContext = createContext<DataContextType | undefined>(undefined);

export const useData = () => {
  const context = useContext(DataContext);
  if (context === undefined) {
    throw new Error('useData must be used within a DataProvider');
  }
  return context;
};

interface DataProviderProps {
  children: ReactNode;
}

export const DataProvider: React.FC<DataProviderProps> = ({ children }) => {
  const [selectedRegion, setSelectedRegion] = useState<Region>('bulawayo');
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [detectionData, setDetectionData] = useState<DetectionData | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshData = async () => {
    setLoading(true);
    try {
      // Fetch monitored-areas grouped data and dashboard chart data in parallel
      const [areasRes, chartsRes] = await Promise.all([
        apiFetch('/api/monitored-areas/grouped'),
        apiFetch('/api/dashboard/charts'),
      ]);

      if (areasRes.ok && chartsRes.ok) {
        const areasData  = await areasRes.json();
        const chartsData = await chartsRes.json();

        // Build alerts from deforested areas' detection history
        const convertedAlerts: Alert[] = [];
        for (const area of (areasData.deforested || [])) {
          for (const record of (area.detection_history || [])) {
            if (record.deforestation_detected) {
              convertedAlerts.push({
                id:          `${area.id}-${record.timestamp || record.after_date}`,
                type:        'deforestation',
                severity:    (record.forest_loss_percent || 0) >= 40 ? 'critical'
                              : (record.forest_loss_percent || 0) >= 20 ? 'high'
                              : (record.forest_loss_percent || 0) >= 5  ? 'medium' : 'low',
                location:    area.name,
                description: `Forest loss of ${Math.abs(record.forest_loss_percent || 0).toFixed(1)}% detected`,
                detectedAt:  new Date(record.after_date || record.timestamp || Date.now()),
                status:      'active',
                coordinates: area.coordinates?.[0]
                              ? { lat: area.coordinates[0][1], lng: area.coordinates[0][0] }
                              : undefined,
              } as Alert);
            }
          }
        }

        // Totals from grouped summary
        const totals     = areasData.totals || {};
        const totalAreas = totals.total || 0;

        const newDetectionData: DetectionData = {
          totalArea:       totalAreas * 500,         // rough average 500 ha per area
          deforestedArea:  chartsData.riskZones
                             .filter((z: any) => z.riskLevel === 'critical' || z.riskLevel === 'high')
                             .reduce((sum: number, z: any) => sum + z.area, 0),
          miningArea:      0,
          activeIncidents: convertedAlerts.length,
          trendsData:      chartsData.trendsData,
          riskZones:       chartsData.riskZones,
        };

        setAlerts(convertedAlerts);
        setDetectionData(newDetectionData);
      } else {
        // Fallback to mock data if backend unavailable
        console.warn('Backend unavailable, using mock data');
        const { alerts: newAlerts, detectionData: newData } = generateMockData(selectedRegion, selectedDate);
        setAlerts(newAlerts);
        setDetectionData(newData);
      }
    } catch (error) {
      console.error('Error fetching detection data:', error);
      // Fallback to mock data on error
      const { alerts: newAlerts, detectionData: newData } = generateMockData(selectedRegion, selectedDate);
      setAlerts(newAlerts);
      setDetectionData(newData);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshData();
  }, [selectedRegion, selectedDate]);

  useEffect(() => {
    // Simulate real-time updates every 30 seconds
    const interval = setInterval(() => {
      if (!loading) {
        refreshData();
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [selectedRegion, selectedDate, loading]);

  return (
    <DataContext.Provider value={{
      selectedRegion,
      setSelectedRegion,
      selectedDate,
      setSelectedDate,
      alerts,
      setAlerts,
      detectionData,
      loading,
      refreshData
    }}>
      {children}
    </DataContext.Provider>
  );
};