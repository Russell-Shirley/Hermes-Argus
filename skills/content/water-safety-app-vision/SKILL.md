|---
name: water-safety-app-vision
description: |-
  Product vision document for SafeWade — a mobile-first water safety app
  that predicts hypothermia risk using GPS, weather, and personal profiles.
  Covers architecture, cost model, UX flow, and hypothermia calculation engine.
  DO NOT use for: implementation, code generation, or app development.
category: content
domain: product-vision
intent:
  - product-vision
  - app-design
  - hypothermia-modeling
exclusions:
  - implementation
  - code-generation
  - app-development
requires: []
phase: planning
compatible_with: []
conflicts_with: []
handoff_to: []
scope: local-only
data_access:
  mcp_servers: []
  secrets: []
  trust_level: standard
governed_by: []
version: 1.0.0
compatibility:
  min_runtime: hermes-1.0
deprecated: false
deprecation_notes: ""
examples:
  - "What should the SafeWade MVP look like?"
  - "Design the hypothermia risk calculation model"
  - "Plan the zero-cost API stack for SafeWade"
|---

# SafeWade — Water Safety & Hypothermia Predictor
## Product Vision Document v0.1

## Core Architecture

### Free/Cheap API Stack
- **Weather:** Open-Meteo (free, no API key) — temp, humidity, dew point, wind
- **Water body ID:** Overpass API (OpenStreetMap, free) + reverse geocoding fallback
- **Backend:** Supabase (free tier — 500MB DB, 50K users)
- **Push:** Expo Push Notifications (free)
- **Analytics:** PostHog (free tier — 1M events/month)
- **Frontend:** React Native + Expo

### Hypothermia Calculation Engine

**Pattern:** base_time(water_temp) × age × weight × clothing × activity × wind × tolerance

Base times from USCG research:

| Temp °F | Base Time |
|:-------:|:---------:|
| <32.5 | <2 min |
| 32.5-40 | 2-15 min |
| 40-50 | 15-30 min |
| 50-60 | 30-60 min |
| 60-70 | 1-3 hrs |
| 70-80 | 3-12 hrs |
| >80 | Safe |

Multipliers: child ×0.3, <100lb ×0.5, swimsuit ×0.7, wetsuit ×2.0, swimming ×0.6, windy ×0.6

### Verified API Performance (tested 2026-05-22)
- **Open-Meteo:** ✅ Temp, humidity, dew point, wind speed all returned. No API key needed. Lat/lon query works. Response example: 45°F felt like 35°F with 20mph wind. Available at `https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,dew_point_2m,wind_speed_10m,apparent_temperature&temperature_unit=fahrenheit`
- **Overpass API for water body ID:** ⚠️ Variable results. Works well for large named lakes (tested with Lake Tahoe coordinates — found "Lake Tahoe" as a water body). May miss small/unnamed bodies. Combine with manual user selection.
- **Coordinate precision:** Free GPS on phones gets ~16ft accuracy. Reverse geocoding (Nominatim) coarse — tested offset up to 25ft from actual center of a water body.

### Operating Cost: $0/mo (free tier), ~$25/mo at 10K MAU

### Key UX Screens
1. Location (auto GPS + tap water body)
2. Water details (conditions + manual temp input)
3. People setup (group profiles)
4. Live countdown timer (green→yellow→red)
5. Post-session summary

### Key Differentiators
- Group-first design (most vulnerable person sets the limit)
- Weather-aware dynamic recalculation
- Zero operating cost
- Privacy-focused
- Learning loop via post-session feedback
