import { Alert, DetectionData, Region, ActivityType, AlertSeverity } from '../types';

const regionNames = {
  bulawayo: 'Bulawayo District',
  amazon: 'Amazon Basin',
  congo: 'Congo Basin',
  borneo: 'Borneo Region'
};

const generateRandomCoordinate = (baselat: number, baseLng: number) => ({
  lat: baselat + (Math.random() - 0.5) * 0.1,
  lng: baseLng + (Math.random() - 0.5) * 0.1
});

const regionCoords = {
  bulawayo: { lat: -20.1667, lng: 28.5833 },
  amazon: { lat: -3.4653, lng: -62.2159 },
  congo: { lat: -0.2280, lng: 18.8361 },
  borneo: { lat: 1.5533, lng: 110.3592 }
};

export const generateMockData = (region: Region, date: Date): { alerts: Alert[], detectionData: DetectionData } => {
  const coords = regionCoords[region];
  const regionName = regionNames[region];
  
  // Generate mock alerts
  const alertTypes: ActivityType[] = ['deforestation', 'mining', 'both'];
  const severities: AlertSeverity[] = ['critical', 'high', 'medium', 'low'];
  
  const alerts: Alert[] = Array.from({ length: 15 }, (_, i) => {
    const alertCoords = generateRandomCoordinate(coords.lat, coords.lng);
    const type = alertTypes[Math.floor(Math.random() * alertTypes.length)];
    const severity = severities[Math.floor(Math.random() * severities.length)];
    const detectedAt = new Date(date);
    detectedAt.setHours(detectedAt.getHours() - Math.floor(Math.random() * 168)); // Last week
    
    return {
      id: `alert-${region}-${i + 1}`,
      type,
      severity,
      status: Math.random() > 0.7 ? 'resolved' : Math.random() > 0.5 ? 'investigating' : 'active',
      location: {
        lat: alertCoords.lat,
        lng: alertCoords.lng,
        address: `${regionName} Sector ${String.fromCharCode(65 + i)}, Grid ${Math.floor(Math.random() * 100) + 1}`
      },
      detectedAt,
      area: Math.floor(Math.random() * 75) + 5,
      confidence: Math.floor(Math.random() * 25) + 75,
      description: type === 'deforestation' 
        ? `Significant vegetation loss detected in protected forest area. NDVI analysis shows ${Math.floor(Math.random() * 40) + 60}% reduction in vegetation cover compared to baseline. Spectral analysis indicates clear-cutting patterns consistent with illegal logging operations.`
        : type === 'mining'
        ? `New excavation activity detected through change detection algorithms. Soil exposure patterns consistent with illegal mining operations. Estimated pit diameter: ${Math.floor(Math.random() * 100) + 50}m. Disturbed soil signatures visible in SWIR bands.`
        : `Combined deforestation and mining activity detected. Large-scale land clearing followed by excavation patterns indicate industrial-level illegal operations. Multi-temporal analysis shows progressive expansion over ${Math.floor(Math.random() * 30) + 10} days.`,
      satelliteImage: `sentinel-2-${region}-${i + 1}.jpg`
    };
  });

  // Generate trends data
  const trendsData = Array.from({ length: 8 }, (_, i) => {
    const weekDate = new Date(date);
    weekDate.setDate(weekDate.getDate() - (7 * (7 - i)));
    
    return {
      week: weekDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      deforestation: Math.floor(Math.random() * 40) + 10,
      mining: Math.floor(Math.random() * 25) + 5
    };
  });

  // Generate risk zones
  const riskZones = Array.from({ length: 8 }, (_, i) => ({
    id: `zone-${region}-${i + 1}`,
    name: `${regionName} Zone ${String.fromCharCode(65 + i)}`,
    riskLevel: (['critical', 'high', 'medium', 'low'] as const)[Math.floor(Math.random() * 4)],
    area: Math.floor(Math.random() * 1500) + 200
  }));

  const detectionData: DetectionData = {
    totalArea: 125000 + Math.floor(Math.random() * 50000),
    deforestedArea: 2800 + Math.floor(Math.random() * 800),
    miningArea: 1200 + Math.floor(Math.random() * 400),
    activeIncidents: alerts.filter(alert => alert.status === 'active').length,
    trendsData,
    riskZones
  };

  return { alerts, detectionData };
};