# Date Handling & Error Display Fixes

## Issues Fixed

### 1. Date Selection Bug ✅
**Problem:** Selected dates (01/03/2021 to 02/03/2026) were not being used correctly. The system was showing "2026-02-03..2026-04-04" instead.

**Root Cause:** Date states were global (`areaBeforeDate`, `areaAfterDate`) instead of per-area. When you selected dates for one area, those same dates were used for ALL areas.

**Solution:**
- Changed date storage from global states to **per-area Map storage**
- Each monitored area now has its own `before` and `after` dates
- Dates are stored as: `Map<areaId, { before: string, after: string }>`
- Each area's dates persist independently

**Code Changes:**
```typescript
// OLD (Global - Wrong)
const [areaBeforeDate, setAreaBeforeDate] = useState('');
const [areaAfterDate, setAreaAfterDate] = useState('');

// NEW (Per-Area - Correct)
const [areaDates, setAreaDates] = useState<Map<string, { before: string; after: string }>>(new Map());
```

### 2. Error Display Improvement ✅
**Problem:** Errors were shown as popup alerts that blocked the screen and didn't provide helpful troubleshooting info.

**Solution:**
- Added **dedicated error display section** below the monitored areas
- Shows clear error messages with context
- Includes troubleshooting tips:
  - Verify date range (before < after)
  - Check satellite imagery availability
  - Cloud cover warnings
  - Date range suggestions
- Dismissible with × button
- Red-themed UI for visibility

## How It Works Now

### Date Selection Flow
1. Click "Select Date Range" on any area
2. Date picker opens **for that specific area only**
3. Default dates auto-populate if empty:
   - Before: 2 months ago
   - After: Today
4. Select custom dates for that area
5. Click "Run Detection Now" - **uses that area's dates**
6. Each area remembers its own dates

### Error Handling Flow
1. Detection runs with area-specific dates
2. If error occurs (e.g., no imagery found):
   - Error displays below monitored areas section
   - Shows specific error message
   - Provides troubleshooting guidance
3. User can:
   - Read error details
   - Check troubleshooting tips
   - Dismiss error with × button
   - Adjust dates and retry

## Technical Details

### Date Parameter Passing
```typescript
const runDetectionOnArea = async (areaId: string) => {
  const params: any = {};
  const dates = areaDates.get(areaId);  // Get THIS area's dates
  if (dates?.before) params.before_date = dates.before;
  if (dates?.after) params.after_date = dates.after;
  
  // Send to API with correct dates
  await apiFetch(`/api/monitored-areas/${areaId}/detect`, {
    method: 'POST',
    body: JSON.stringify(params)
  });
};
```

### Date Storage
```typescript
// Setting dates for area 'abc123'
setAreaDates(new Map(areaDates).set('abc123', {
  before: '2021-03-01',
  after: '2026-02-03'
}));

// Getting dates for area 'abc123'
const dates = areaDates.get('abc123');
// Returns: { before: '2021-03-01', after: '2026-02-03' }
```

### Error State Management
```typescript
// Clear previous errors before running
setAreaError(null);

// If API call fails
if (!res.ok) {
  const error = await res.json();
  setAreaError(`Detection failed for area: ${error.error}`);
}

// Display in UI
{areaError && (
  <div className="error-section">
    <p>{areaError}</p>
    <ul>Troubleshooting tips...</ul>
    <button onClick={() => setAreaError(null)}>×</button>
  </div>
)}
```

## What Changed in the UI

### Before
- ❌ One global date picker affecting all areas
- ❌ Dates would change for all areas when editing one
- ❌ Errors shown as blocking alert() popups
- ❌ No troubleshooting guidance

### After
- ✅ Each area has its own date picker
- ✅ Dates persist per area independently
- ✅ Errors shown inline below areas section
- ✅ Helpful troubleshooting tips provided
- ✅ Dismissible error messages
- ✅ No blocking popups

## Example Usage

### Monitoring Multiple Areas with Different Dates

**Area 1: "Amazon Reserve"**
- Before: 2020-01-01
- After: 2020-12-31
- Purpose: Check 2020 deforestation

**Area 2: "Congo Basin"**
- Before: 2021-03-01
- After: 2026-02-03
- Purpose: Check recent changes

Both areas maintain their own dates independently. When you run detection on Area 1, it uses 2020 dates. When you run detection on Area 2, it uses 2021-2026 dates.

## Error Examples

### No Imagery Found
```
Detection failed for area: 500: No Sentinel-2 images found for 
2021-03-01..2026-02-03 under cloud<80.0%
```

**What to do:**
1. Check if dates are in valid range (Sentinel-2 started April 2015)
2. Try adjusting date range to periods with less cloud cover
3. Consider selecting dry season dates for your region
4. Verify the area has satellite coverage

### Invalid Date Range
```
Detection failed for area: Invalid date range - 'before' date must 
be earlier than 'after' date
```

**What to do:**
1. Verify Before date < After date
2. Check date format is correct (YYYY-MM-DD)
3. Make sure dates are not in the future

## Files Modified

- **Frontend/src/pages/MapViewPage.tsx**
  - Lines 60-62: Changed date states to Map storage
  - Lines 479-515: Updated runDetectionOnArea with per-area dates
  - Lines 1599-1632: Updated date picker inputs
  - Lines 1648-1673: Updated date picker button
  - Lines 1703-1735: Added error display section

## Testing the Fix

1. **Test Per-Area Dates:**
   ```
   - Create Area 1
   - Select dates: 2021-01-01 to 2021-12-31
   - Create Area 2
   - Select dates: 2022-01-01 to 2022-12-31
   - Run detection on Area 1 → Should use 2021 dates
   - Run detection on Area 2 → Should use 2022 dates
   - Verify each area keeps its own dates
   ```

2. **Test Error Display:**
   ```
   - Select dates with no imagery (e.g., future dates)
   - Run detection
   - Verify error appears below areas section
   - Verify troubleshooting tips are shown
   - Click × to dismiss
   - Verify error clears
   ```

## Additional Notes

- Date format must be YYYY-MM-DD (enforced by HTML date input)
- Dates are stored as strings in ISO format
- Backend expects dates in YYYY-MM-DD format
- Default date range is 2 months (for optimal change detection)
- Maximum cloud cover is 80% (configurable in backend)

## Future Enhancements

- [ ] Add date range validation in UI (before < after)
- [ ] Show available date ranges based on satellite coverage
- [ ] Calendar view showing imagery availability
- [ ] Date presets (last month, last quarter, last year)
- [ ] Error retry with suggested date adjustments
