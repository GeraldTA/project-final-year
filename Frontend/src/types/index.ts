export type Region = 'bulawayo' | 'amazon' | 'congo' | 'borneo';

export type AlertSeverity = 'critical' | 'high' | 'medium' | 'low';

export type ActivityType = 'deforestation' | 'mining' | 'both';

export type AlertStatus = 'active' | 'investigating' | 'resolved';

export interface Alert {
  id: string;
  type: ActivityType;
  severity: AlertSeverity;
  status: AlertStatus;
  location: {
    lat: number;
    lng: number;
    address: string;
  };
  detectedAt: Date;
  area: number; // hectares
  confidence: number; // percentage
  description: string;
  satelliteImage?: string;
}

export interface DetectionData {
  totalArea: number;
  deforestedArea: number;
  miningArea: number;
  activeIncidents: number;
  trendsData: {
    week: string;
    deforestation: number;
    mining: number;
  }[];
  riskZones: {
    id: string;
    name: string;
    riskLevel: 'low' | 'medium' | 'high' | 'critical';
    area: number;
  }[];
}

export interface MapMarker {
  id: string;
  lat: number;
  lng: number;
  type: ActivityType;
  severity: AlertSeverity;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'analyst' | 'viewer' | 'investigator';
  status: 'active' | 'inactive';
  lastLogin: Date;
}

export interface SystemSettings {
  detectionSensitivity: number;
  minAreaThreshold: number;
  scanFrequency: 'daily' | 'weekly' | 'monthly';
  autoAlertThreshold: AlertSeverity;
  dataRetention: number; // months
  apiRateLimit: number; // requests per hour
}