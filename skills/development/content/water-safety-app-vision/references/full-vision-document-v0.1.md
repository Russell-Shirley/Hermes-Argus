# SafeWade — Water Safety & Hypothermia Predictor
## Full Product Vision Document (v0.1)

---

## 1. Product Vision

**SafeWade** is a mobile-first water safety application that helps users understand how long they can safely stay in a body of water before hypothermia becomes a risk. It combines GPS location, real-time weather data, and detailed physical profiles of everyone in the group to calculate personalized safe-water-time estimates.

> *"Know before you go. Know while you're in."*

### Target Users
- Parents at lakes and beaches watching their children
- Groups swimming in cold water (mountain lakes, northern beaches)
- Kayakers, paddleboarders, and watersports enthusiasts
- Families on vacation at unfamiliar water bodies
- Outdoor youth groups and camp counselors

---

## 2. Core Features (MVP)

### 2.1 Location Detection
- **Auto-detect** via device GPS
- **Tap-to-select** nearby water body (list from OpenStreetMap data)
- **Manual entry** of location name (cache results)
- **Fallback:** User types water body name, app remembers for future visits

### 2.2 Water Body Identification
- Query Overpass API for named water bodies near current GPS coordinates
- Return name, type (lake, river, ocean, reservoir), approximate area
- Show on map with tap-to-select UX
- Cache results locally to reduce API calls

### 2.3 Current Weather Conditions
- Pull from Open-Meteo at user's GPS coordinates
- Display: temperature (°F default, °C toggle), humidity, dew point, wind speed
- Recalculate every 15 minutes while session is active
- Cache weather data for 5 minutes (avoids redundant API calls in unstable areas)

### 2.4 Group Profile Setup
- **User's own profile** (age, height, weight, cold tolerance level, clothing)
- **Add people** to the group with: name/nickname (optional), age (required), height and weight (required), cold tolerance (slider: 1-5), activity level (still/swimming/active)
- **Default profile** for returning users
- **Quick-add presets** ("Child 5-10", "Teen", "Adult", "Elderly")

### 2.5 Hypothermia Calculation Engine
- Calculates safe water time per person based on:
  - Water temperature (from weather API or manual input)
  - Air temperature, wind chill, humidity
  - Age (children cool faster, elderly lose heat regulation ability)
  - Body mass (smaller = faster heat loss)
  - Clothing/insulation (wetsuit, swimsuit, clothing)
  - Activity level (swimming increases heat loss, treading water still)
  - Individual cold tolerance (self-reported on 1-5 scale)
  - Wind exposure (body above water surface wind chill factor)
- **Group limit** = lowest safe time across all members
- **Real-time timer** counts down from the group limit

### 2.6 Warning System
- **Green zone:** >50% time remaining
- **Yellow zone:** 25-50% time remaining — "Getting cold, consider heading in"
- **Red zone:** <25% time remaining — "Risk of hypothermia, get out now!"
- **Alert:** Push notification when entering yellow zone
- **Emergency alert:** Sound + vibration when entering red zone
- **Weather change:** Dynamic recalculation if conditions worsen (wind picks up, temperature drops)

### 2.7 Analytics & Feedback
- **Anonymous aggregate:** All sessions recorded (no PII) to PostHog
- **Company dashboard:** Popular water bodies, average safe times, usage patterns
- **Post-session survey:** "Did anyone get too cold? How was the prediction?"
- **Learning loop:** Feedback used to calibrate the hypothermia model over time

### 2.8 Unit System Toggle
- Default: Fahrenheit (°F)
- Toggle to Celsius (°C) via settings
- Threshold warnings auto-convert to adjacent equivalent

---

## 3. Technical Architecture

### Frontend
- **Framework:** React Native + Expo
- **Maps:** react-native-maps (free, no Mapbox key needed at basic level)
- **Local storage:** AsyncStorage for user preferences + cached weather/locations
- **Push notifications:** Expo Push Notifications (free)
- **State management:** Zustand (lightweight, no boilerplate)
- **Navigation:** Expo Router (file-based routing)

### Backend & Infrastructure
- **Auth:** Supabase Auth (email/password + optional Google/Apple SSO)
- **Database:** Supabase PostgreSQL (free tier: 500MB)
- **Edge Functions:** Supabase Edge Functions (Deno) for weather API proxying
- **Analytics:** PostHog (free tier: 1M events/month)
- **Body-of-water IDs:** Overpass API (OpenStreetMap, free, no key)
- **Weather:** Open-Meteo (free, no API key)

### Hypothermia Model (Calculation Detail)

#### Base Heat Loss Rate (minutes of safe exposure in 50°F/10°C water)
Base times derived from US Coast Guard cold water survival tables:

| Water Temp °F | Temp °C | Average Adult (150-180lb) Safe Time |
|:-------------:|:-------:|:----------------------------------:|
| <32.5         | <0.3    | <2 min                             |
| 32.5 - 40     | 0.3-4.4 | 2-15 min                           |
| 40 - 50       | 4.4-10  | 15-30 min                          |
| 50 - 60       | 10-15.6 | 30-60 min                          |
| 60 - 70       | 15.6-21 | 1-3 hrs                            |
| 70 - 80       | 21-26.7 | 3-12 hrs                           |
| >80           | >26.7   | Safe (no practical hypothermia risk) |

#### Multipliers Applied

| Factor | Condition | Multiplier |
|--------|-----------|:----------:|
| **Age** | Child (<12) | ×0.3 |
| | Teen (12-17) | ×0.7 |
| | Adult (18-60) | ×1.0 |
| | Elderly (>60) | ×0.6 |
| **Weight** | <100 lb | ×0.5 |
| | 100-150 lb | ×0.75 |
| | 150-200 lb | ×1.0 |
| | >200 lb | ×1.15 |
| **Clothing** | Swimsuit | ×0.7 |
| | Light clothing | ×0.85 |
| | Full clothing | ×1.0 |
| | Wetsuit | ×2.0 |
| | Dry suit | ×4.0 |
| **Activity** | Still/resting | ×1.0 |
| | Treading water | ×0.8 |
| | Swimming | ×0.6 |
| **Wind** | Calm (<5mph) | ×1.0 |
| | Light breeze (5-15mph) | ×0.85 |
| | Moderate (15-25mph) | ×0.7 |
| | Strong (>25mph) | ×0.5 |
| **Cold Tolerance** | Very low (1) | ×0.7 |
| | Low (2) | ×0.85 |
| | Average (3) | ×1.0 |
| | High (4) | ×1.15 |
| | Very high (5) | ×1.3 |

#### Formula
```
safe_minutes = base_time(water_temp) × age_mult × weight_mult × clothing_mult × activity_mult × wind_mult × tolerance_mult
```

#### Example Calculation
- 8-year-old child (age mult: 0.3), 70 lb (weight mult: 0.5)
- Water temp: 55°F (base: 30-60 min, use mid ~45 min)
- Wearing swimsuit (clothing mult: 0.7)
- Swimming (activity mult: 0.6)
- Wind: 10 mph (wind mult: 0.85)
- Cold tolerance: Average (mult: 1.0)

**Result:** 45 × 0.3 × 0.5 × 0.7 × 0.6 × 0.85 × 1.0 = **2.4 minutes**

This is intentionally conservative — the goal is to prevent hypothermia, not to push limits.

---

## 4. UX Design Principles

1. **Default to simple, expand to powerful**
   - Default view: Just show the timer with current conditions
   - Tap to configure: People, clothing, etc.
   
2. **One-tap session start**
   - Open app → auto-detect location → tap water body → add people → start timer
   - Minimum viable flow: 3 taps

3. **Glanceable readings**
   - Large countdown timer
   - Color-coded safety zones (green → yellow → red)
   - Current conditions displayed compactly

4. **Group-first calculations**
   - The weakest link sets the limit
   - Clear who is the limiting factor (name + their safe time)

5. **Offline-first**
   - Cache weather data and water body info
   - Timer runs offline once session starts
   - Sync data when connection returns

---

## 5. Screen Map

| Screen | Purpose | Key UI Elements |
|--------|---------|-----------------|
| **Home** | Quick session start | Map with GPS dot + nearby water bodies, "Start Session" button |
| **Water Body Select** | Choose or confirm water body | Card list of nearby bodies, manual search input, map view |
| **Add People** | Build group profile | Profile cards, quick-add presets, "Add Person" button, "Use Previous Profile" |
| **Person Detail** | Configure one person | Age slider (years), height/weight inputs, cold tolerance slider, clothing picker, activity picker |
| **Session Active** | Live countdown and conditions | Large timer (minutes:seconds), color-coded background, group breakdown (who-safe-for-how-long), weather overlay, "End Session" button |
| **Session Summary** | Post-swim review | Actual time in water, prediction vs reality, log conditions, optional cold-report feedback |
| **Settings** | Preferences | Unit toggle (°F/°C), notification preferences, default profile, privacy settings |
| **Analytics (Company)** | Aggregate data | Dashboard: popular locations, average times, cold reports, usage by geography |

---

## 6. Cost & Scaling Model

| Tier | Users | Revenue | Monthly Cost | Key Services | Platform Split |
|:----:|:-----:|:-------:|:------------:|:------------:|:--------------:|
| **Launch** | 0-1K MAU | Free | **$0/mo** | Supabase Free, PostHog Free, Open-Meteo Free, Overpass Free, Expo Free | 60% iOS, 40% Android |
| **Growth** | 1-10K MAU | Free | **~$25/mo** | Supabase Pro ($25), PostHog Free, Open-Meteo Free, Overpass Free, Expo Free | 60% iOS, 40% Android |
| **Scale** | 10-100K MAU | Tiered/premium | **~$100/mo** | Supabase Team ($99), PostHog Growth (free tier), Open-Meteo Free | 60% iOS, 40% Android |
| **Enterprise** | 100K+ MAU | B2B white-label | $500+/mo | Supabase Enterprise, custom infrastructure | N/A |

**Revenue model (proposed):**
- Free: Basic timer (30-min daily limit), 1-profile
- Premium ($3.99/mo): Unlimited sessions, group profiles, weather alerts, cold history

---

## 7. Development Timeline

| Phase | Duration | Deliverables |
|:-----:|:--------:|:------------|
| **Week 1-2** | Foundation | React Native/Expo setup, GPS integration, weather API integration, basic UI framework |
| **Week 3** | Water body ID | Overpass API integration, map view, location selection flow |
| **Week 4** | Hypothermia engine | Calculation model implementation, testing against reference data, group limit logic |
| **Week 5** | Session flow | Timer UI, color-coded safety zones, notifications, end-session summary |
| **Week 6** | Users & polish | Auth system, profile persistence, settings, unit toggle, analytics integration |
| **Week 7+** | Hardening | Offline mode, error states, edge case handling, App Store/Play Store prep |

**Total MVP: ~6 weeks**

---

## 8. Risk & Limitations

### Known Limitations
- **Water temp is inferred from air temp + body type** (no direct water temperature measurement without sensor data)
- **Model is conservative** by design — better to warn too early than too late
- **GPS accuracy varies** — expect ~16ft on modern phones
- **No water quality data** — only hypothermia risk, not pollution/algae/drowning

### Mitigations
- Allow manual water temperature input (user buys $10 thermometer)
- Use local weather station data as fallback if GPS weather is unreliable
- Clear disclaimers: "This is a prediction tool, not a guarantee of safety"
- "Know your limits" warning on first launch
- Medical/cold-water safety sources cited in-app

---

## 9. Open Questions (For Product Owner)

1. **Monetization:** Free ad-supported? Freemium tiered? One-time purchase?
2. **Social features:** Share "my safe time" with friends? Group invites?
3. **Water temp crowdsourcing:** Let users submit measured water temps for accuracy?
4. **Apple Watch / Wear OS:** Companion app on wrist for glanceable timer?
5. **B2B angle:** Sell to summer camps, swim schools, tour operators?
6. **Seasonal usage:** Primarily spring/summer — how to maintain engagement year-round?
7. **Liability:** How do we legally protect against misuse? Terms of Service language.

---

## 10. Appendices

### A. API Endpoints (for development reference)

**Open-Meteo (weather)**
```
GET https://api.open-meteo.com/v1/forecast
  ?latitude=39.0997
  &longitude=-120.0383
  &current=temperature_2m,relative_humidity_2m,dew_point_2m,wind_speed_10m,apparent_temperature
  &temperature_unit=fahrenheit
```

**Overpass (water body query)**
```
[out:json][timeout:25];
(
  nwr["natural"="water"](around:500,39.0997,-120.0383);
  nwr["water"="lake"](around:500,39.0997,-120.0383);
  nwr["water"="river"](around:500,39.0997,-120.0383);
);
out center name;
```

### B. Hypothermia Reference Sources
- US Coast Guard Cold Water Survival Tables
- NIOSH/Cold Stress Calculator
- Wilderness Medical Society Clinical Practice Guidelines for Hypothermia

---

*Document generated 2026-05-22 by Argus Panoptes for Bridge and Bolt*
