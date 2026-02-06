# How to Select Dates for Area Monitoring

## The Problem
You were selecting dates "01/03/2021 to 02/03/2026" but the system was using default dates "2026-02-03 to 2026-04-04" instead.

## Why This Happened
The dates are stored **per-area** in the frontend. If you don't explicitly set dates for an area using the "Select Date Range" button, the system uses default dates (last 60 days).

## Step-by-Step Solution

### 1. Open Date Picker
Click the **"Select Date Range"** button on your monitored area card.

### 2. Enter Dates
The date inputs use **YYYY-MM-DD** format (international standard):

- **Before Date:** `2021-03-01` (March 1, 2021)
- **After Date:** `2026-02-03` (February 3, 2026)

⚠️ **Important:** Don't use `01/03/2021` format - use `2021-03-01`

### 3. Verify Dates
After entering the dates, you should see a blue box on the area card showing:
```
📅 Selected Dates:
Before: 2021-03-01
After: 2026-02-03
```

### 4. Close Date Picker
Click the **"Close"** button or click "Select Date Range" again to hide the picker.

### 5. Run Detection
Now click **"Run Detection Now"** - it will use YOUR selected dates.

## Visual Workflow

```
┌─────────────────────────────────────┐
│  Area: My Forest Reserve            │
│  Created: 2/3/2026                  │
│                                     │
│  📅 Selected Dates:                 │ ← This confirms dates are set
│  Before: 2021-03-01                 │
│  After: 2026-02-03                  │
│                                     │
│  [Select Date Range]  ← Click here first
│  [Run Detection Now]  ← Then click here
└─────────────────────────────────────┘
```

## Troubleshooting

### "No dates showing in blue box"
**Problem:** You haven't selected dates for this area yet.
**Solution:** Click "Select Date Range" and enter your dates.

### "Wrong dates showing"
**Problem:** The dates were set incorrectly or for a different area.
**Solution:** Click "Select Date Range" again and update the dates.

### "Still getting 2026-02-03..2026-04-04 error"
**Problem:** The dates weren't sent to the backend.
**Solution:** 
1. Open browser Developer Console (F12)
2. Look for console logs showing: `Sending detection request with params: {...}`
3. Verify `before_date` and `after_date` are in the params
4. If they're missing, the dates weren't set - repeat steps above

### "Date format confusion"
**Problem:** HTML date inputs use YYYY-MM-DD format.
**Solution:** Enter dates as:
- ✅ `2021-03-01` (Correct)
- ❌ `01/03/2021` (Wrong - will be interpreted incorrectly)
- ❌ `03/01/2021` (Wrong - will be interpreted incorrectly)

## Date Format Reference

| What You Want | How to Enter It |
|--------------|-----------------|
| March 1, 2021 | `2021-03-01` |
| February 3, 2026 | `2026-02-03` |
| December 31, 2025 | `2025-12-31` |
| January 15, 2020 | `2020-01-15` |

## Behind the Scenes

### What Happens When You Select Dates
1. Dates are stored in browser memory (React state) per area ID
2. Each area has its own date pair: `{ before: '2021-03-01', after: '2026-02-03' }`
3. Dates persist until you refresh the page or update them

### What Happens When You Run Detection
1. Frontend retrieves dates for that specific area from memory
2. Sends POST request to backend with dates in JSON body:
   ```json
   {
     "before_date": "2021-03-01",
     "after_date": "2026-02-03"
   }
   ```
3. Backend uses these dates for satellite image query
4. If no dates sent, backend uses defaults (last 60 days)

## Debugging Tips

### Check Browser Console
Press F12 and look for these logs:
```
Area dates for abc123 : { before: '2021-03-01', after: '2026-02-03' }
Sending detection request with params: { before_date: '2021-03-01', after_date: '2026-02-03' }
```

### Check Backend Logs
Look for:
```
Received params: {'before_date': '2021-03-01', 'after_date': '2026-02-03'}
Using dates: before=2021-03-01, after=2026-02-03
```

If you see:
```
Received params: {}
Using dates: before=2025-12-05, after=2026-02-03
```
This means dates weren't sent from frontend.

## Common Mistakes

1. **Not clicking "Select Date Range" before "Run Detection Now"**
   - Result: Default dates used instead of your dates

2. **Refreshing page after selecting dates**
   - Result: Dates cleared from memory (not saved to backend yet)
   - Solution: Re-select dates after page refresh

3. **Using wrong date format**
   - Result: Dates might be misinterpreted or rejected
   - Solution: Always use YYYY-MM-DD format

4. **Selecting future dates**
   - Result: No satellite imagery available
   - Solution: Use dates in the past (Sentinel-2 started April 2015)

## Valid Date Ranges

- **Minimum Date:** April 2015 (when Sentinel-2 satellites started)
- **Maximum Date:** Today (or a few days ago due to processing delay)
- **Recommended:** At least 30-60 days apart for meaningful change detection

## Need Help?

If you're still having issues:
1. Check the blue "Selected Dates" box on your area card
2. Check browser console (F12) for any error messages
3. Check that dates are in YYYY-MM-DD format
4. Verify the dates are reasonable (between 2015 and today)
5. Make sure "Before" date is earlier than "After" date
