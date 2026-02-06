# Date Range Selection & Continuous Monitoring - Quick Guide

## ✅ What's New

You can now:
1. **Select custom date ranges** for each monitored area
2. **Receive alerts** when deforestation is detected
3. **View detection history** for each area
4. **Track continuous monitoring** status

---

## 🗓️ Date Range Selection

### How to Use:
1. Navigate to your monitored area card
2. Click **"Select Date Range"** button
3. Choose your dates:
   - **Before Date**: Start of comparison period
   - **After Date**: End of comparison period
4. Click **"Run Detection Now"**

### Default Dates:
- **Before**: 2 months ago
- **After**: Today

### Tips:
- Compare same seasons (e.g., Jan → Jan) to avoid false positives
- Longer gaps show more change but may miss gradual deforestation
- Shorter gaps (1-2 months) catch recent changes

---

## 🚨 Deforestation Alerts

### Alert System:
When deforestation is detected in your monitored areas, you'll see:

1. **Red Alert Panel** at the top showing:
   - Number of affected areas
   - Area names with detection counts
   - Last detection timestamp

2. **Alert Badge** on area cards:
   - Shows "⚠️ X detections"
   - Red text for visibility

3. **Pulsing Green Indicator**:
   - Shows "Continuous monitoring active"
   - Indicates area is being tracked

### Managing Alerts:
- **View Details**: Click on alert to see full detection results
- **Dismiss Alert**: Click "Dismiss" to clear notification
  - Alert is hidden but detection count remains
  - Can be re-enabled in area settings

---

## 📊 Detection History

Every time you run detection on an area, it's saved in the history.

### What's Tracked:
- ✅ Timestamp of detection
- ✅ Date range analyzed (before → after)
- ✅ Deforestation status (detected or not)
- ✅ Forest loss percentage (if detected)
- ✅ Vegetation trend (growth/decline/stable)

### Viewing History:
1. Select a monitored area
2. Run detection or view previous results
3. Scroll through "Detection History" section
4. See timeline of all checks (last 50 runs)

### History Display:
- **Red background**: Deforestation detected
- **Gray background**: No change detected
- **Most recent first**: Newest at top
- **Scrollable**: Up to 50 records

---

## 🌳 Continuous Monitoring

### What It Does:
- Areas are marked for ongoing surveillance
- Alerts trigger when deforestation is found
- Green pulsing indicator shows active status
- Enabled by default for new areas

### How It Works:
1. Draw and save an area
2. Continuous monitoring is **automatically enabled**
3. Run detection periodically (manual for now)
4. Get alerts when deforestation is detected

### Future Enhancements (Planned):
- ⏰ Automatic scheduled checks (weekly/monthly)
- 📧 Email notifications when deforestation is detected
- 📱 Push notifications for mobile
- 📈 Trend analysis and predictions

---

## 💡 Example Workflow

### Monitoring a Forest Reserve:

1. **Initial Setup** (Day 1):
   ```
   - Draw polygon around forest area
   - Name: "Eastern Forest Reserve"
   - Save with continuous monitoring enabled
   ```

2. **First Check** (Day 1):
   ```
   - Click "Select Date Range"
   - Before: 2 months ago
   - After: Today
   - Run Detection
   - Result: ✅ No deforestation
   ```

3. **Regular Monitoring** (Weekly):
   ```
   - Click "Run Detection Now"
   - Uses same date range or update as needed
   - System tracks each check in history
   ```

4. **Alert Received** (Week 4):
   ```
   🚨 Alert appears:
   - "Eastern Forest Reserve"
   - "1 deforestation event detected"
   - Last detected: [timestamp]
   ```

5. **Investigate**:
   ```
   - Click alert to view details
   - See forest loss: 2.3%
   - Check detection history
   - Review before/after imagery
   - Take action if needed
   ```

6. **After Investigation**:
   ```
   - Dismiss alert to clear notification
   - Detection count remains for records
   - Continue monitoring for future changes
   ```

---

## 🎯 Best Practices

### Date Selection:
✅ **Do:**
- Compare same seasons (Jan-Jan, Jun-Jun)
- Use 1-3 month intervals for recent changes
- Adjust dates based on rainy/dry seasons

❌ **Don't:**
- Compare different seasons (causes false positives)
- Use very short intervals (<2 weeks)
- Mix rainy season with dry season

### Monitoring Strategy:
✅ **Do:**
- Check areas weekly or bi-weekly
- Review detection history for patterns
- Act on alerts promptly
- Keep areas active for long-term tracking

❌ **Don't:**
- Ignore repeated detections
- Dismiss alerts without investigation
- Disable monitoring without reason
- Delete areas with detection history

### Alert Management:
✅ **Do:**
- Investigate all alerts thoroughly
- Document findings externally
- Keep detection history as evidence
- Re-run detection if uncertain

❌ **Don't:**
- Dismiss alerts blindly
- Assume one clear result means no issues
- Ignore vegetation trend warnings
- Delete areas after first detection

---

## 📈 Understanding Results

### Detection Outcomes:

**✅ No Deforestation Detected**
- Forest cover stable or increasing
- Vegetation trend: Growth or Stable
- Safe to dismiss alert

**⚠️ Deforestation Detected**
- Forest cover decreased
- Vegetation trend: Decline
- **Action required!**

### Key Metrics:

1. **Forest Cover Before/After**:
   - Shows forest percentage at each time
   - Example: 45.23% → 45.17%

2. **Forest Loss (Absolute)**:
   - Percentage points lost
   - Example: 0.06% loss

3. **Forest Loss (Relative)**:
   - Percent of original forest lost
   - Example: 0.13% of existing forest

4. **Vegetation Trend**:
   - **Growth**: Greener, healthier
   - **Decline**: Less vegetation
   - **Stable**: Minimal change

---

## 🔧 Technical Details

### Data Storage:
```json
{
  "id": "area-uuid",
  "name": "Forest Area",
  "continuous_monitoring": true,
  "alert_enabled": true,
  "detection_count": 3,
  "detection_history": [
    {
      "timestamp": "2026-02-01T10:30:00",
      "before_date": "2025-12-01",
      "after_date": "2026-02-01",
      "deforestation_detected": true,
      "forest_loss_percent": 2.3,
      "vegetation_trend": "decline"
    }
  ]
}
```

### API Endpoints:

**Run Detection with Custom Dates:**
```bash
POST /api/monitored-areas/{id}/detect
{
  "before_date": "2025-12-01",
  "after_date": "2026-02-01"
}
```

**Dismiss Alert:**
```bash
PATCH /api/monitored-areas/{id}
{
  "alert_enabled": false
}
```

---

## 🆘 Troubleshooting

### "No imagery available"
- Extend date range (try 3 months)
- Check area has satellite coverage
- Avoid very cloudy seasons

### "Detection failed"
- Verify API server is running
- Check Google Earth Engine authentication
- Review browser console for errors

### "Alert not showing"
- Ensure `alert_enabled: true`
- Check if deforestation was actually detected
- Refresh page to reload alerts

### "Date picker not appearing"
- Click "Select Date Range" button
- Ensure you're in drawing mode
- Try different area if issue persists

---

## 📞 Quick Reference

| Feature | Button/Action |
|---------|--------------|
| Select dates | Click "Select Date Range" |
| Run detection | Click "Run Detection Now" |
| View history | Select area, scroll down |
| Dismiss alert | Click "Dismiss" in alert panel |
| View details | Click on alert or area |
| Delete area | Click trash icon (🗑️) |

---

**Start monitoring your forests with custom date ranges today! 🌲📅**
