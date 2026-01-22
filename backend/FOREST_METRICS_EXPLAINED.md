# Forest Loss Metrics - Accurate Calculations

## Overview
This document explains how forest loss is calculated and displayed accurately in the deforestation detection system.

## Key Metrics Explained

### 1. **Forest Cover Before/After (Percentage)**
- **What it is**: The percentage of the area covered by forest at each time period
- **Calculation**: `forest_probability × 100`
- **Example**: 
  - Before: 45.23% forest cover
  - After: 45.17% forest cover
- **Display**: Shown as percentage with 2 decimal places

### 2. **Forest Loss (Absolute Percentage)**
- **What it is**: The absolute decrease in forest cover percentage points
- **Calculation**: `(forest_probability_before - forest_probability_after) × 100`
- **Example**: 
  - Before: 45.23%
  - After: 45.17%
  - **Forest Loss: 0.06%** (absolute percentage point decrease)
- **Display**: Red if positive (loss detected), green if zero/negative
- **Important**: This is the ABSOLUTE change in percentage points, not relative to original forest

### 3. **Relative Forest Loss (Percentage of Original)**
- **What it is**: What percentage of the ORIGINAL forest was lost
- **Calculation**: `(forest_drop / forest_probability_before) × 100`
- **Example**: 
  - Before: 45.23% forest cover
  - Loss: 0.06 percentage points
  - **Relative Loss: 0.13%** of the original forest
  - Interpretation: 0.13% of the existing forest was lost
- **Display**: Red if > 5% (significant loss), normal otherwise
- **Important**: This shows the loss RELATIVE to what existed before

## Example Scenario

**Location**: Test area in Zimbabwe
**Time period**: 60 days

### Results:
```
Before (Date: 2024-11-15)
  - Forest Cover: 45.23%
  - NDVI: 0.3886
  - Greenness Score: 0.5054

After (Date: 2025-01-16)
  - Forest Cover: 45.17%
  - NDVI: 0.2771
  - Greenness Score: 0.4603

Change Analysis:
  ✓ Forest Loss (Absolute): 0.06%
    → The area lost 0.06 percentage points of forest cover
  
  ✓ Relative Forest Loss: 0.13% of original
    → 0.13% of the existing forest was removed
  
  ✓ NDVI Decline: 0.1115 (↓ 28.7%)
    → Significant vegetation health decline
  
  ✓ Greenness Decline: 0.0451 (↓ 8.9%)
    → Visual analysis shows vegetation stress
  
  ⚠️ Deforestation Detected: YES
    → All indicators show vegetation decline
```

## Interpretation Guidelines

### Small Forest Loss (< 1% absolute)
- **0.01-0.10%**: Minor clearing, could be natural variation or small-scale activities
- **0.10-0.50%**: Moderate clearing, worth monitoring
- **0.50-1.00%**: Significant clearing, investigation recommended

### Large Forest Loss (> 1% absolute)
- **1-5%**: Major deforestation event, immediate attention needed
- **5-10%**: Severe deforestation, urgent intervention required
- **> 10%**: Catastrophic forest loss, emergency response

### Relative Forest Loss Context
- **< 1%**: Minimal impact on existing forest
- **1-5%**: Noticeable reduction in forest area
- **5-10%**: Significant forest degradation
- **> 10%**: Major forest destruction

## Why Two Metrics?

### Absolute Forest Loss (0.06%)
- **Use case**: Understanding the overall landscape change
- **Answer**: "How much of the TOTAL area changed?"
- **Context**: In a 100 hectare area, 0.06% = 60 square meters lost

### Relative Forest Loss (0.13%)
- **Use case**: Understanding impact on existing forest
- **Answer**: "How much of the EXISTING forest was lost?"
- **Context**: If 45% was forested, losing 0.13% of that forest is the impact

## Supporting Indicators

### NDVI (Normalized Difference Vegetation Index)
- **Range**: -1 to +1
- **Healthy vegetation**: > 0.3
- **Sparse vegetation**: 0.2 - 0.3
- **Very sparse**: 0.1 - 0.2
- **Non-vegetated**: < 0.1

### Greenness Score (RGB Analysis)
- **Calculation**: Green channel / (Red + Blue channels)
- **High greenness**: > 0.5 (healthy vegetation)
- **Moderate**: 0.3 - 0.5
- **Low**: < 0.3

### Vegetation Trend
- **Growth**: Visual greenness or NDVI increased > 5%
- **Decline**: NDVI decreased > 10%
- **Stable**: Changes within ±5%

## Data Quality Notes

1. **Cloud Cover**: Set to 80% maximum to ensure adequate imagery availability
2. **Time Window**: 60 days to capture seasonal changes
3. **Resolution**: 10m Sentinel-2 imagery
4. **Validation**: ML model predictions verified against RGB and NDVI analysis

## Accuracy Improvements

### Priority System
1. **Visual RGB Analysis** (highest priority)
   - Direct observation of green vegetation
   - Resistant to seasonal variations
   
2. **NDVI Verification** (second priority)
   - Standard vegetation health metric
   - Accounts for infrared reflectance
   
3. **ML Model Prediction** (lowest priority)
   - Trained on European forests
   - May misinterpret African savanna patterns
   - Used only when RGB and NDVI are inconclusive

### Override Logic
If visual analysis shows **growth** but ML shows decline:
→ System reports **NO DEFORESTATION** (visual evidence overrides ML)

If NDVI shows **decline** > 10% and visual agrees:
→ System reports **DEFORESTATION DETECTED** (multiple indicators agree)

## API Response Format

```json
{
  "status": "success",
  "deforestation_detected": true,
  "before": {
    "date": "2024-11-15",
    "forest_probability": 0.4523,
    "forest_cover_percent": 45.23,
    "ndvi_mean": 0.3886,
    "greenness_score": 0.5054
  },
  "after": {
    "date": "2025-01-16",
    "forest_probability": 0.4517,
    "forest_cover_percent": 45.17,
    "ndvi_mean": 0.2771,
    "greenness_score": 0.4603
  },
  "change": {
    "forest_drop": 0.0006,
    "forest_drop_percent": 0.06,
    "forest_loss_percent": 0.13,
    "ndvi_drop": 0.1115,
    "greenness_increase": -0.0451,
    "vegetation_trend": "decline",
    "interpretation": "NDVI decreased by 0.112 - possible deforestation"
  }
}
```

## Frontend Display

The UI now shows:
- ✅ **Forest Cover Before**: 45.23%
- ✅ **Forest Cover After**: 45.17%
- ⚠️ **Forest Loss**: 0.06% (absolute change)
- ⚠️ **Relative Forest Loss**: 0.13% of original (impact on existing forest)
- 📊 **NDVI Change**: ↓ 0.112 (decline indicator)
- 🌿 **Greenness Change**: ↓ 0.045 (visual decline indicator)

## Conclusion

The system now provides accurate, human-readable forest loss metrics that clearly distinguish between:
1. **Absolute change** in landscape (percentage points)
2. **Relative impact** on existing forest (percentage of original)

Both metrics are important for understanding deforestation events and are verified by multiple independent indicators (RGB, NDVI, ML) for maximum accuracy.
