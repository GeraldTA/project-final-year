import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Alert, DetectionData, Region } from '../types';
import { generateMockData } from '../utils/mockData';

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

  const refreshData = () => {
    setLoading(true);
    const { alerts: newAlerts, detectionData: newData } = generateMockData(selectedRegion, selectedDate);
    setAlerts(newAlerts);
    setDetectionData(newData);
    setLoading(false);
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