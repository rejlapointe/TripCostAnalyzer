# Trip Cost Analyzer — Specification
# Revision: 1.2 | Last updated: 04/10/26

---

## Overview

A local desktop-style web app that calculates the round-trip fuel cost from the user's home to any number of saved locations. The user searches for a vehicle by year/make/model/trim using the fueleconomy.gov API (US Department of Energy), enters the current gas price manually, and the app computes cost per trip, cost per 100km, monthly cost, and annual cost per location. Charts show trip cost history and gas price history over time. The app runs locally in a browser (FastAPI backend) during development and is distributed as a standalone `.exe` (Electron-packaged) requiring no Python install, no API key, and no setup from the end user.

---

## What the App Does

1. **Home Address** — User enters their home address once in Settings. The app geocodes it (lat/lng) using OpenStreetMap and stores the coordinates so it never needs to geocode again.

2. **Location Search** — User searches for a destination by name or address using OpenStreetMap (Nominatim). Selects from results. The app calculates the road distance (km) from home using OSRM and stores the location permanently.

3. **Vehicle Selection** — User searches for a vehicle via the fueleconomy.gov API (free, no key required, covers 1984–present). Selection is a cascade: Year → Make → Model → Trim. The API returns MPG which is converted to L/100km and stored. Up to 3 vehicles can be selected for comparison. Selected vehicles are saved for future sessions.

4. **Gas Price** — User manually enters the current gas price ($/L). The app logs it with a timestamp every time it is updated.

5. **Trip Cost Calculation** — For each saved location, the app calculates:
   - **Round-trip distance** (km × 2)
   - **Fuel used** (L) = distance × L/100km / 100
   - **Cost per trip** ($) = fuel used × $/L
   - **Cost per 100km** ($)
   - **Monthly cost** ($) = cost per trip × days per week × 4.33
   - **Annual cost** ($) = cost per trip × days per week × 52

6. **Days per Week** — Each location has a selector (1–7) representing how many days per week the user travels there. Used to compute monthly and annual costs.

7. **Multi-Vehicle Comparison** — Up to 3 vehicles can be selected simultaneously. The locations table shows one cost column per selected vehicle so the user can compare fuel costs across vehicles (e.g. current car vs. a potential new one).

8. **Locations Table** — Main view. Shows all saved locations with current round-trip costs. Refreshes automatically whenever gas price or vehicle selection changes. Columns: Location | Distance (km) | Days/Week | Cost/Trip | Cost/100km | Monthly | Annual (one set per selected vehicle).

9. **Refresh** — A Refresh button re-runs all calculations using the current gas price and selected vehicles. Calculations also auto-refresh on app open.

10. **Trip Cost History** — Every time a calculation runs, a snapshot is saved: location, vehicle, gas price, distance, cost per trip, monthly cost, annual cost, timestamp. Used for the history graph.

11. **Charts**:
    - **Cost per trip over time** — one line per location (for the active vehicle)
    - **Gas price over time** — all logged gas price entries

12. **Settings** — Home address entry, current gas price entry, vehicle selection.

---

## UI Layout

### Header (sticky)
```
| Trip Cost Analyzer | [Settings] | Gas: $X.XXX/L | Last updated: [date] |
```

### Main Tabs
- **Locations** — locations table with costs
- **Charts** — trip cost history + gas price history
- **Vehicles** — manage selected vehicles (search NRCan DB, add/remove)
- **Settings** — home address, gas price

### Locations Tab
- Table: Location | Distance | Days/Week | [Vehicle A cols] | [Vehicle B cols] | [Vehicle C cols]
- Each vehicle block: Cost/Trip | Cost/100km | Monthly | Annual
- **Days/Week** column: selector (1–7) per row, editable inline
- **+ Add Location** button — opens search panel
- **Refresh** button — recalculates all rows with current gas price
- Click a row to edit days/week or remove location

### Charts Tab
- **Trip Cost History** chart (Chart.js line chart) — cost per trip over time, one line per location
- **Gas Price History** chart (Chart.js line chart) — $/L over time

### Vehicles Tab
- Cascade selectors: Year → Make → Model → Trim (each populated by fueleconomy.gov API)
- **Add Vehicle** button — adds selected trim to my vehicles
- List of currently selected vehicles (max 3) with remove button
- Displayed per vehicle: Year | Make | Model | Trim | City L/100km | Hwy L/100km | Combined L/100km

### Settings Tab
- **Home Address** field — text input, geocoded on save; coordinates stored in DB
- **Gas Price** field — $/L, manual entry; logged to history on save
- **Save** button

---

## Data & Calculations

### Distance
- Geocoding: OpenStreetMap Nominatim API (free, no key required)
- Routing/distance: OSRM public API (free, no key required)
- Stored in DB after first calculation — never re-fetched unless address changes

### Vehicle Fuel Data (fueleconomy.gov API)
- **API base**: `https://www.fueleconomy.gov/ws/rest`
- **Year list**: `GET /vehicle/menu/year`
- **Makes for year**: `GET /vehicle/menu/make?year={year}`
- **Models for make**: `GET /vehicle/menu/model?year={year}&make={make}`
- **Trims for model**: `GET /vehicle/menu/options?year={year}&make={make}&model={model}`
- **Fuel economy**: `GET /vehicle/{id}/mpg` → returns city/highway/combined MPG
- **MPG → L/100km conversion**: `L/100km = 235.215 ÷ MPG`
- Values stored in `my_vehicles` at time of selection — no re-fetch needed unless user re-adds the vehicle
- Covers 1984–present, no API key required

### Fuel Cost
- Round-trip distance = one-way distance (km) × 2
- Fuel used (L) = round-trip distance × (combined L/100km ÷ 100)
- Cost per trip ($) = fuel used × gas price ($/L)
- Cost per 100km ($) = gas price × L/100km ÷ 100 × 100
- Monthly cost ($) = cost per trip × days per week × 4.33
- Annual cost ($) = cost per trip × days per week × 52

### Days per Week Selector
- Range: 1–7 (integer)
- Default: 5
- Stored per location in the database
- Changing the value immediately recalculates monthly and annual costs for that row

---

## Database — trip_data.db

Single SQLite file. All app data lives here. No bundled vehicle database — vehicle data is fetched live from fueleconomy.gov at the time of selection.

### Tables

**my_vehicles** (user's selected vehicles, max 3 — fuel data stored at time of selection)
- id, fueleconomy_id (int — fueleconomy.gov vehicle ID), year, make, model, trim, city_l100km, hwy_l100km, combined_l100km, display_order, added_at

**settings**
- key, value
- Rows: home_address, home_lat, home_lng, current_gas_price, last_gas_price_update

**locations**
- id, label, address, lat, lng, distance_km (one-way), days_per_week (int, default 5), added_at

**gas_price_log**
- id, price_per_litre, recorded_at, notes

**trip_cost_history**
- id, location_id (FK), vehicle_id (FK), gas_price, distance_km, combined_l100km, cost_per_trip, cost_per_100km, monthly_cost, annual_cost, calculated_at

---

## Architecture

### Development Stack
| Layer | Choice | Reason |
|---|---|---|
| Backend | FastAPI + Python | Same pattern as existing projects |
| Database | SQLite (via SQLAlchemy) | File-based, no server required |
| Frontend | Vanilla JS | No framework overhead |
| Charts | Chart.js | Lightweight, clean |
| Maps / Geocoding | OpenStreetMap Nominatim | Free, no API key |
| Routing / Distance | OSRM public API | Free, no API key |
| Vehicle data | fueleconomy.gov API | Free, no key, 1984–present, live search |

### Distribution Stack
| Layer | Choice |
|---|---|
| Packaging | Electron (wraps FastAPI + frontend) |
| Output | `.exe` installer or zip with double-click `.exe` |
| Runtime | Bundled — no Python install required for end user |

### Development Workflow
1. Run FastAPI server locally: `python -m uvicorn server:app --host 127.0.0.1 --port 8506`
2. Open Chrome: `http://127.0.0.1:8506/index.html`
3. Develop and test normally — no Electron involved

### Distribution Workflow
1. Run `build-package.ps1` (build script)
2. Script creates a clean copy of `trip_data.db`
3. Script strips all personal data from the copy (see Build Script below)
4. Script inserts demo data into the copy
5. Electron packages everything into a distributable `.exe`
6. Output: `TripCostAnalyzer-setup.zip` or `.exe` installer

---

## Build Script — build-package.ps1

The build script is the only path to a distributable. It must:

### Step 1 — Strip Personal Data
Copy `trip_data.db` → `dist/trip_data.db`. Then on the copy, delete all rows from:
- `settings` (home address, coordinates, gas price)
- `my_vehicles` (user's selected vehicles)
- `locations` (all saved locations)
- `gas_price_log` (all gas price history)
- `trip_cost_history` (all trip snapshots)

There is no reference data table to preserve — the DB ships empty of vehicle data.

### Step 2 — Insert Demo Data
Insert into the clean copy:
- **Settings**: home_address = "123 Main Street, Toronto, ON", geocoded coordinates for that address, gas_price = 1.65
- **my_vehicles**: 2022 Toyota Camry LE — insert directly with fueleconomy_id, year, make, model, trim, and L/100km values (fetched from fueleconomy.gov once at build time and hardcoded into the script)
- **Locations**: "Toronto Pearson Airport" and "Costco North York" with real coordinates and distances from the demo home address
- **gas_price_log**: 3 entries over the past 3 months (1.55, 1.61, 1.65)
- **trip_cost_history**: a few historical snapshots for the demo locations

### Step 3 — Package
Run Electron build with the clean demo `trip_data.db`. Output to `/dist`.

**The user's real `trip_data.db` is never touched by the build script.**

---

## Files

### Application Code
| File | Purpose |
|---|---|
| `server.py` | FastAPI backend — API endpoints + static file serving |
| `core.py` | Constants, utility functions, cost calculations |
| `data.py` | SQLite access via SQLAlchemy |
| `vehicles.py` | fueleconomy.gov API client — year/make/model/trim cascade + MPG fetch |
| `web/index.html` | Main frontend UI |
| `web/app.js` | All frontend JS logic |
| `requirements.txt` | Python dependencies |

### Data Files
| File | Purpose |
|---|---|
| `trip_data.db` | All app data — generated on first run |

### Distribution
| File | Purpose |
|---|---|
| `build-package.ps1` | Build script — strips data, inserts demo data, packages .exe |
| `StartApp.bat` | Double-click launcher for development |
| `StartApp.ps1` | PowerShell launcher script |
| `readme.txt` | End-user quick-start guide |

### Documentation
| File | Purpose |
|---|---|
| `spec.md` | This file — full specification |
| `BUILDPLAN.md` | Build plan — slices and tasks |

---

## Portability — End User Requirements

The distributed `.exe` requires:
- Windows (10 or 11)
- Internet connection (for OpenStreetMap geocoding, OSRM routing, and fueleconomy.gov vehicle search)
- Nothing else — no Python, no API keys, no setup

The user provides only:
- Their home address (entered in Settings on first run)
- Current gas price (entered in Settings)

---

## Revision Log

| Rev | Date | Changes |
|---|---|---|
| 1.0 | 2026-04-10 | Initial spec — full app definition, stack, DB schema, build/distribution strategy |
| 1.1 | 2026-04-10 | Replaced visit frequency tag with days-per-week selector (1–7, default 5); updated calculations, UI, and DB schema |
| 1.2 | 2026-04-10 | Replaced NRCan CSV with fueleconomy.gov live API (1984–present, no key); removed vehicles reference table; my_vehicles now stores fetched data directly; MPG→L/100km conversion documented |
