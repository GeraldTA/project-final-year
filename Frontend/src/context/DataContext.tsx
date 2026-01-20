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
      // Fetch real detection data from backend
      const alertsResponse = await apiFetch('/api/detection/alerts?limit=50');
      const reportResponse = await apiFetch('/api/detection/report');
      
      if (alertsResponse.ok && reportResponse.ok) {
        const alertsData = await alertsResponse.json();
        const reportData = await reportResponse.json();
        
        // Convert backend alert format to frontend Alert type
        const convertedAlerts: Alert[] = alertsData.alerts.map((alert: any) => ({
          ...alert,
          detectedAt: new Date(alert.detectedAt)
        }));
        
        // Build detection data from report
        const stats = reportData.deforestation_statistics;
        const newDetectionData: DetectionData = {
          totalArea: (reportData.coordinates.east - reportData.coordinates.west) * 
                     (reportData.coordinates.north - reportData.coordinates.south) * 12321, // km² to hectares
          deforestedArea: stats.deforestation_area_hectares,
          miningArea: 0, // Not tracked separately in current system
          activeIncidents: alertsData.total_detections,
          trendsData: [], // Would need historical data
          riskZones: [] // Would need risk analysis
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