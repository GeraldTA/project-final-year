# Interactive Area Monitoring Guide

## Overview
You can now draw custom areas on the map to monitor specific regions for deforestation. This allows you to:
- Mark exact locations you want to track
- Monitor multiple areas simultaneously  
- Run ML detection on specific regions of interest
- Track detection history for each area

## How to Use

### Step 1: Enable Drawing Mode
1. Navigate to the Map View page
2. Look for the button that says **"Enable Area Drawing"** below the map title
3. Click it to switch to the interactive map

### Step 2: Draw Your Monitoring Area
1. In the top-right corner of the map, you'll see drawing tools (polygon and rectangle icons)
2. Click the **polygon tool** (for irregular shapes) or **rectangle tool** (for square/rectangular areas)
3. **To draw a polygon:**
   - Click on the map to place each corner point
   - Move around the area you want to monitor
   - Click the first point again to complete the shape
4. **To draw a rectangle:**
   - Click and drag on the map to create a rectangular area

### Step 3: Save Your Area
1. After drawing, a dialog will appear asking for area details
2. Enter a **name** for your area (required)
   - Example: "Chirinda Forest East Section"
3. Optionally add a **description** with notes about the area
   - Example: "Protected forest zone near river"
4. Click **"Save Area"** to store it

### Step 4: Run ML Detection
1. Your saved area will appear in the "Your Monitored Areas" section below the map
2. Click on any area card to select it
3. Click the **"Run Detection"** button on the area card
4. Wait for the detection to complete (may take 1-2 minutes)
5. View the results showing:
   - Forest cover before and after
   - Forest loss percentage
   - Vegetation trend (growth/decline/stable)
   - NDVI changes

### Step 5: Manage Your Areas
- **View all areas:** Scroll down to see all your monitored areas
- **Select an area:** Click on any area card to highlight it on the map
- **Delete an area:** Click the trash icon (🗑️) on the area card
- **Track detections:** Areas show detection count and last monitored time

## Features

### Area Information Displayed
Each monitored area shows:
- ✅ **Name and description**
- 📅 **Creation date**
- 🕐 **Last monitored timestamp**  
- ⚠️ **Number of deforestation detections**
- 🟢 **Monitoring status** (enabled/disabled)

### Detection Results
When you run detection on an area, you'll see:
- **Deforestation status**: ⚠️ Detected or ✅ Not detected
- **Vegetation trend**: 🌿 Growth, decline, or stable
- **Forest cover percentages**: Before and after
- **Forest loss metrics**:
  - Absolute loss (percentage points)
  - Relative loss (% of original forest)
- **Supporting data**: NDVI changes, greenness scores

### Map Features
- **Zoom and pan**: Navigate the map freely
- **Existing areas**: Shown as green polygons on the map
- **Click polygons**: View area details in a popup
- **Edit/delete tools**: Available in drawing toolbar

## Tips

### Drawing Accurate Areas
- Zoom in before drawing for better precision
- Use satellite layer to see actual terrain
- Mark boundaries around specific forest patches
- Smaller areas = faster detection processing

### Monitoring Strategy
1. **Start small**: Create a few key areas first
2. **Regular checks**: Run detection weekly or monthly
3. **Seasonal awareness**: Compare same-season imagery to avoid false positives
4. **Multiple areas**: Monitor different forest zones separately

### Interpreting Results
- **Small changes (< 1%)**: May be natural variation or sensor noise
- **Moderate changes (1-5%)**: Worth investigating further
- **Large changes (> 5%)**: Likely genuine deforestation event
- **Visual analysis**: System prioritizes RGB/NDVI over ML model for accuracy

## API Endpoints

If integrating programmatically:

### Get All Monitored Areas
```bash
GET /api/monitored-areas
```

### Add New Area
```bash
POST /api/monitored-areas
Content-Type: application/json

{
  "name": "Forest Area Name",
  "description": "Optional description",
  "coordinates": [[lat1, lng1], [lat2, lng2], ...]
}
```

### Run Detection on Area
```bash
POST /api/monitored-areas/{area_id}/detect
```

### Delete Area
```bash
DELETE /api/monitored-areas/{area_id}
```

## Technical Details

### Data Storage
- Monitored areas are saved in `backend/data/monitored_areas.json`
- Each area includes:
  - Unique ID (UUID)
  - Name and description
  - Polygon coordinates (array of [lat, lng] points)
  - Creation timestamp
  - Last monitored timestamp
  - Detection count

### Detection Process
1. System calculates the **center point** of your polygon
2. Downloads Sentinel-2 imagery for that location
3. Runs ML model on the imagery
4. Validates results with NDVI and RGB analysis
5. Returns comprehensive forest change metrics

### Performance
- **Drawing**: Instant
- **Saving**: < 1 second
- **Detection**: 1-2 minutes (depends on imagery availability)
- **Multiple areas**: Can be monitored independently

## Troubleshooting

### "No imagery available"
- Try increasing the date range
- Check if the location has cloud-free imagery
- Some remote areas may have limited coverage

### Detection taking too long
- Normal for first detection (downloads imagery)
- Subsequent detections are faster (cached data)
- Large areas take longer to process

### Area not showing on map
- Refresh the page
- Check if area was saved successfully
- Make sure you're in drawing mode

### Can't draw on map
- Ensure "Enable Area Drawing" is clicked
- Check that drawing tools appear in top-right corner
- Try refreshing the page

## Example Use Cases

### 1. Protected Forest Monitoring
- Draw polygons around protected forest reserves
- Run monthly detections
- Track any unauthorized clearing

### 2. Reforestation Tracking
- Mark areas undergoing reforestation
- Monitor vegetation growth over time
- Verify restoration progress

### 3. Border Zone Surveillance
- Draw areas along park boundaries
- Detect early signs of encroachment
- Alert rangers to investigate

### 4. Research Study Areas
- Define precise study zones
- Collect time-series data
- Compare changes across seasons

## Future Enhancements

Planned features:
- ⏰ Scheduled automatic detection
- 📧 Email alerts when deforestation is detected
- 📊 Historical trends and charts
- 🗺️ Export areas as GeoJSON/KML
- 📱 Mobile app integration
- 🔔 Real-time notifications

## Support

If you encounter issues or have questions:
1. Check the browser console for error messages
2. Verify the backend API server is running
3. Ensure you have proper GEE authentication
4. Review the backend logs for detailed error information

---

**Start monitoring your forests today! 🌳**
