# MySQL Migration Plan - Data Storage Areas

## ✅ Already Migrated to MySQL

### 1. **Monitored Areas** (COMPLETED)
- **Current**: `backend/data/monitored_areas.json`
- **Status**: ✅ Migrated to `monitored_areas` table
- **Location**: `backend/services/area_manager.py`

### 2. **Detection History** (COMPLETED)
- **Current**: Embedded in monitored_areas.json
- **Status**: ✅ Migrated to `detection_history` table
- **Location**: `backend/services/area_manager.py`

---

## 🔄 Needs Migration to MySQL

### 3. **ML Detection Results** (HIGH PRIORITY)
- **Current**: `backend/data/ml_detections/detection_*.json` files
- **Table**: `ml_detections` (already created in schema)
- **Location**: `backend/src/ml/api_integration.py`
- **Lines**: 125-127 (saving), 401-410 (loading list), 464-482 (loading specific)
- **Impact**: Currently creates separate JSON file per detection
- **Benefits**: 
  - Query detections by date, area, confidence
  - Aggregate statistics across all detections
  - Faster retrieval than scanning files

### 4. **Deforestation Coordinates** (HIGH PRIORITY)
- **Current**: `deforestation_maps/deforestation_coordinates.json`
- **Table**: `deforestation_coordinates` (already created in schema)
- **Locations**:
  - `backend/api_server.py` lines 161-167, 333-367, 783-829, 843-857
  - `backend/realistic_photo_processor.py` lines 101-108
  - `backend/realistic_photo_processor_fixed.py` lines 101-108
- **Impact**: Map visualization data, deforestation hotspots
- **Benefits**:
  - Spatial queries for coordinates
  - Link to monitored areas
  - Filter by severity, date

### 5. **Deforestation Reports** (MEDIUM PRIORITY)
- **Current**: `deforestation_maps/deforestation_report.json`
- **Table**: Could use `system_metadata` or create new table
- **Locations**:
  - `backend/api_server.py` lines 334-367, 773-793, 844-857, 961-967
  - `backend/realistic_photo_processor.py` lines 102-108
- **Impact**: Analysis reports and statistics
- **Benefits**:
  - Historical report tracking
  - Version history
  - Metadata queries

### 6. **NDVI Tile URLs** (MEDIUM PRIORITY)
- **Current**: `backend/fresh_tile_urls.json`
- **Table**: `system_metadata` with key='ndvi_tiles'
- **Locations**:
  - `backend/api_server.py` lines 299-301, 317-320, 417-420, 652-655
  - `backend/automated_updater.py` lines 21, 61
- **Impact**: Map tile URLs for visualization
- **Benefits**:
  - Track tile generation history
  - Cache management
  - Automatic cleanup

### 7. **Monitored Locations Config** (MEDIUM PRIORITY)
- **Current**: `backend/config/monitored_locations.json`
- **Table**: Could merge with `monitored_areas` or use `system_metadata`
- **Location**: `backend/api_server.py` lines 976-1006
- **Impact**: Legacy location monitoring system
- **Benefits**: Unified location management

### 8. **Processing History Metadata** (LOW PRIORITY)
- **Current**: 
  - `backend/data/metadata/download_history.json`
  - `backend/data/metadata/processing_history.json`
  - `backend/data/metadata/change_detection_history.json`
- **Table**: Create `processing_history` table or use `system_metadata`
- **Locations**: `backend/src/main.py` lines 124-143, 244-264, 362-382, 465-491
- **Impact**: Historical tracking of batch operations
- **Benefits**:
  - Query processing status
  - Performance metrics
  - Error tracking

### 9. **Scheduler State** (LOW PRIORITY)
- **Current**: `backend/data/metadata/last_run.json`
- **Table**: `system_metadata` with key='scheduler_state'
- **Location**: `backend/src/utils/scheduler.py` lines 46, 239, 257
- **Impact**: Tracks last scheduler execution time
- **Benefits**:
  - Better scheduler state management
  - Concurrent access safety

### 10. **Last Update Tracking** (LOW PRIORITY)
- **Current**: `backend/last_update.json`
- **Table**: `system_metadata` with key='last_update'
- **Location**: `backend/automated_updater.py` lines 22, 72, 89
- **Impact**: Tracks automated update timestamps
- **Benefits**: Centralized update tracking

---

## 🚫 Should NOT Migrate to MySQL

### 11. **Training History & Metrics** (KEEP AS FILES)
- **Current**: 
  - `models/training_history.json`
  - `models/test_metrics.json`
- **Locations**: `backend/src/ml/training.py` lines 340-343, 468-475
- **Reason**: ML model artifacts, should stay with model files

### 12. **ML Analysis Reports** (KEEP AS FILES)
- **Current**: Generated analysis reports
- **Location**: `backend/src/ml/postprocessing.py` line 270
- **Reason**: One-time analysis outputs, not operational data

### 13. **GEE Export Metadata** (KEEP AS FILES)
- **Current**: Sentinel-2 band export metadata
- **Location**: `backend/src/ml/gee_export.py` line 135
- **Reason**: Tied to specific satellite image files

---

## 📊 Migration Priority Summary

### Phase 1 - Critical (Do First)
1. ✅ Monitored Areas (DONE)
2. ✅ Detection History (DONE)
3. 🔄 ML Detection Results
4. 🔄 Deforestation Coordinates

### Phase 2 - Important (Do Next)
5. 🔄 Deforestation Reports
6. 🔄 NDVI Tile URLs
7. 🔄 Monitored Locations Config

### Phase 3 - Nice to Have (Do Later)
8. 🔄 Processing History Metadata
9. 🔄 Scheduler State
10. 🔄 Last Update Tracking

---

## 🎯 Recommended Next Steps

**Highest Impact**: Migrate **ML Detection Results** and **Deforestation Coordinates**
- These are frequently queried
- Need relational queries (filter by area, date, severity)
- Currently scattered across many JSON files
- Would benefit most from database indexing and joins

**Implementation Order**:
1. Create database models for ML detections
2. Migrate deforestation coordinates table
3. Update API endpoints to use database
4. Create migration script for existing JSON files
5. Add database indexes for performance
6. Update frontend if needed

Would you like me to implement the migration for ML Detection Results and Deforestation Coordinates?
