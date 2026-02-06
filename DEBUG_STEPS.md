# CRITICAL FIX NEEDED

## Problem Confirmed
The backend logs show it's searching for images from **2026-02-04 to 2026-04-05** (today + 60 days).

This proves the backend is NOT receiving your custom dates from the frontend.

## Root Cause
When you click "Run Detection", one of these is happening:
1. The `areaDates[areaId]` state is undefined/empty
2. The dates aren't being sent in the POST request body  
3. The request body is being lost somewhere in transit

## Solution Steps

### Step 1: Open Browser DevTools
1. Press F12 in your browser
2. Go to the "Console" tab
3. Clear all previous logs (click the "🚫" icon)

### Step 2: Try Again
1. Click on a monitored area
2. Click "Select Date Range"
3. Choose dates (e.g., June 2023 - August 2023)
4. Click "Run Detection Now"

### Step 3: Check Console Output
Look for these exact log lines:
```
=== DETECTION REQUEST START ===
Area ID: <some-id>
Area dates for <area-id>: {before: "2023-06-01", after: "2023-08-01"}
Request URL: /api/monitored-areas/<area-id>/detect
Request params: {
  "before_date": "2023-06-01",
  "after_date": "2023-08-01"
}
```

### Step 4: Check Network Tab
1. Click the "Network" tab in DevTools
2. Find the POST request to `/api/monitored-areas/.../detect`
3. Click on it
4. Go to "Payload" tab
5. Check if you see:
```json
{
  "before_date": "2023-06-01",
  "after_date": "2023-08-01"  
}
```

## What We'll Find

**If Console shows dates but Network Payload is empty:**
- The apiFetch function is broken

**If Console shows undefined dates:**
- The state isn't being set when you select dates
- Or the button is getting a different area ID

**If both show correct dates but backend still uses 2026:**  
- There's a server-side bug ignoring the request body

Please do these steps and tell me what you see in:
1. Console logs
2. Network tab Payload

Then I can give you the exact fix.
