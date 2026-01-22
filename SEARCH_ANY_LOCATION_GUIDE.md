# 🌍 Search Any Location in Zimbabwe - User Guide

## Overview
Your deforestation detection system now supports **free-form location search** just like Google Maps! You can search and analyze **ANY area in Zimbabwe** for deforestation.

## 🎯 Features

### ✅ Universal Search
- Search ANY place in Zimbabwe by name
- Use coordinates for precise locations
- Get multiple results to choose from
- Automatic area bounds calculation (~10km coverage)

### ✅ Search Types Supported

#### 1. **City Names**
```
Harare
Bulawayo
Mutare
Gweru
Masvingo
```

#### 2. **National Parks & Protected Areas**
```
Hwange National Park
Mana Pools National Park
Gonarezhou National Park
Matusadona National Park
Nyanga National Park
```

#### 3. **Geographic Regions**
```
Zambezi Valley
Matabeleland
Manicaland
Eastern Highlands
Lowveld
```

#### 4. **Towns & Villages**
```
Kariba
Chipinge
Chinhoyi
Marondera
Bindura
```

#### 5. **Tourist Locations**
```
Victoria Falls
Chimanimani Mountains
Chinhoyi Caves
Great Zimbabwe Ruins
Lake Kariba
```

#### 6. **Coordinates**
```
-17.8252, 31.0335
-18.9169, 32.6529
```

## 📝 How to Use

### Step 1: Search for a Location
1. Open the **Map View** page
2. Type your location in the search box
3. Press **Enter** or click **Search** button

**Example searches:**
- `Victoria Falls`
- `Mana Pools National Park`
- `Mutare, Manicaland`
- `-17.8252, 31.0335`

### Step 2: Select from Results
- A dropdown will show up to 10 matching locations
- Each result shows:
  - 📍 Full address/name
  - 📐 Coordinates (latitude, longitude)
  - 🏷️ Location type (city, park, village, etc.)
  - 📍 State/province if available
- Click any result to select it

### Step 3: Analyze the Area
Once you've selected a location:

1. **Set Analysis Dates:**
   - Choose a **Before** date (baseline)
   - Choose an **After** date (comparison)
   - Recommended: 6-12 months apart

2. **Run Analysis:**
   - Click **"🗺️ Scan Area for Deforestation (Grid Analysis)"**
   - The system will:
     - Divide the area into a 3×3 grid (9 cells)
     - Download Sentinel-2 satellite imagery
     - Calculate forest cover for each cell
     - Detect deforestation using ML
     - Generate before/after images

3. **Optional - Start Monitoring:**
   - Click **"🛰️ Monitor"** to automatically check this area every 5 days

## 🔍 Search Tips

### For Best Results:
- **Be specific:** `Mana Pools National Park` instead of just `Mana`
- **Include province:** `Mutare, Manicaland` for better accuracy
- **Check spelling:** Use correct place name spelling
- **Try variations:** If no results, try alternate names

### If No Results Found:
- Try a more general search (e.g., nearby city)
- Use coordinates if you know them
- Check for spelling errors
- Include "Zimbabwe" in the search

## 🎨 UI Features

### Search Results Dropdown
- Shows all matching locations
- Click to select any result
- Currently selected location is highlighted in green
- Displays coordinates and location type

### Selected Location Panel
Shows:
- 🗺️ Location name
- 📍 Exact coordinates
- 📏 Coverage area (~10km × 10km)
- Options to Monitor or Scan for deforestation

## 🚀 Technical Details

### Geocoding Service
- Uses **Nominatim** (OpenStreetMap's geocoding service)
- Free and open-source
- No API key required
- Returns detailed address information

### Coverage Area
- Each search creates a **~10km × 10km** monitoring area
- Centered on the searched location
- Suitable for detailed deforestation analysis
- Can be adjusted if needed

### API Endpoints

#### Search Location:
```
GET /api/search/location?query=<place_name>&country=Zimbabwe
```

Returns:
```json
{
  "success": true,
  "query": "Victoria Falls",
  "count": 5,
  "results": [
    {
      "display_name": "Victoria Falls, Zimbabwe",
      "latitude": -17.9243,
      "longitude": 25.8569,
      "type": "city",
      "bounds": {
        "min_lat": -17.9693,
        "max_lat": -17.8793,
        "min_lng": 25.8119,
        "max_lng": 25.9019
      }
    }
  ]
}
```

#### Analyze Location (Coming Soon):
```
POST /api/analyze/location
{
  "latitude": -17.9243,
  "longitude": 25.8569,
  "name": "Victoria Falls",
  "bounds": {...}
}
```

## 📊 Analysis Capabilities

For any searched location, you can:

1. **Grid Scan** - Divide into 3×3 grid, analyze each cell
2. **Change Detection** - Compare forest cover between dates
3. **ML Detection** - Use BigEarthNet model to classify deforestation
4. **Monitoring** - Automatic checks every 5 days
5. **Visual Markers** - See deforestation areas highlighted on images

## 🌟 Example Use Cases

### 1. Protected Area Monitoring
```
Search: "Hwange National Park"
→ Select park boundary result
→ Set dates: 2024-06 (before) vs 2025-01 (after)
→ Run grid scan
→ View deforestation in 9 grid cells
```

### 2. Urban Expansion Analysis
```
Search: "Harare"
→ Select city center
→ Set dates: 2023-01 vs 2025-01
→ See forest loss near city edges
```

### 3. River Valley Deforestation
```
Search: "Zambezi Valley"
→ Select specific valley section
→ Compare seasonal changes
→ Detect illegal logging
```

### 4. Coordinate-Based Search
```
Search: "-17.8252, 31.0335"
→ Analyzes exact GPS location
→ Useful for field reports
```

## 🛠️ Troubleshooting

### "No results found"
- **Solution:** Try broader search terms or nearby locations
- Check spelling and use official place names

### "Search failed"
- **Solution:** Check internet connection
- Wait a moment and try again (rate limiting)

### "Select a location using Search first"
- **Solution:** Complete a search and click a result before running analysis

### Dates not working
- **Solution:** Ensure Before date is earlier than After date
- Use dates when Sentinel-2 imagery is available (2015+)

## 💡 Pro Tips

1. **Search once, analyze many times** - Change dates without re-searching
2. **Bookmark locations** - Use monitoring to save favorite areas
3. **Combine with grid scan** - Get detailed cell-by-cell analysis
4. **Export coordinates** - Share exact locations with team
5. **Use seasonal dates** - Compare same season (e.g., Jan vs Jan) for best results

## 🔗 Related Features

- [ML Detection Guide](backend/src/ml/README.md)
- [Implementation Complete](backend/IMPLEMENTATION_COMPLETE.md)
- [Quick Start Guide](backend/ML_QUICK_START.md)

---

**Now you can analyze deforestation anywhere in Zimbabwe, just like searching on Google Maps! 🎉**
