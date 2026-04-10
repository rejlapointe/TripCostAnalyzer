# Trip Cost Analyzer — Build Plan
# Revision: 1.1 | Last updated: 04/10/26

---

## Slices

| Slice | Name | Description |
|---|---|---|
| 1 | Project Setup | Folder structure, FastAPI skeleton, SQLite + SQLAlchemy models, launcher scripts |
| 2 | Vehicle Search | fueleconomy.gov API client, cascade selectors (year→make→model→trim), my_vehicles table |
| 3 | Settings | Home address input, OpenStreetMap geocoding, gas price entry + logging |
| 4 | Locations | Add/search locations, OSRM distance calculation, save to DB |
| 5 | Calculations | Trip cost, cost/100km, monthly, annual per location per vehicle |
| 6 | Locations Table UI | Main table with days/week selector, live recalculation, refresh button |
| 7 | Vehicle Management | my_vehicles table, add/remove vehicles, multi-vehicle comparison columns |
| 8 | Charts | Chart.js — trip cost history per location, gas price history |
| 9 | Trip Cost History | Snapshot logging on every calculation, history stored in DB |
| 10 | Polish | Error handling, empty states, loading indicators, responsive layout |
| 11 | Build & Distribution | build-package.ps1 — strip data, insert demo data, Electron packaging |

---

## Slice 1 — Project Setup

**Goal:** Bare-bones running app. FastAPI serves a page. DB exists with correct schema.

### Tasks
- [ ] Create project folder: `TripCostAnalyzer/`
- [ ] Create folder structure: `web/`, `data/`
- [ ] Create `requirements.txt`: fastapi, uvicorn, sqlalchemy, httpx, openpyxl
- [ ] Create `db.py`: SQLAlchemy engine + session + Base
- [ ] Create `models.py`: all table models — vehicles, my_vehicles, settings, locations, gas_price_log, trip_cost_history
- [ ] Create `server.py`: FastAPI app, startup event (create all tables), static file serving from `web/`
- [ ] Create `web/index.html`: shell page with header, tabs, empty content panels
- [ ] Create `StartApp.bat` + `StartApp.ps1`: launch uvicorn on port 8506, open Chrome
- [ ] Test: app starts, Chrome opens, page loads, DB file created

### Test Criteria
- `trip_data.db` created on first run with all 6 tables
- FastAPI server responds on `http://127.0.0.1:8506`
- `index.html` loads in Chrome

---

## Slice 2 — Vehicle Search

**Goal:** User can search for a vehicle by year/make/model/trim using the fueleconomy.gov API and add it to my vehicles.

### Tasks
- [ ] Create `vehicles.py`: fueleconomy.gov API client with functions:
  - `get_years()` → list of years (1984–present)
  - `get_makes(year)` → list of makes
  - `get_models(year, make)` → list of models
  - `get_trims(year, make, model)` → list of (id, trim_name) tuples
  - `get_mpg(vehicle_id)` → dict with city_mpg, hwy_mpg, combined_mpg
  - `mpg_to_l100km(mpg)` → `round(235.215 / mpg, 1)`
- [ ] Update `models.py`: replace `Vehicle` + `MyVehicle` with single `MyVehicle` table — id, fueleconomy_id, year, make, model, trim, city_l100km, hwy_l100km, combined_l100km, display_order, added_at
- [ ] Add API endpoints:
  - `GET /api/vehicles/years` → proxy fueleconomy.gov years
  - `GET /api/vehicles/makes?year=` → proxy makes
  - `GET /api/vehicles/models?year=&make=` → proxy models
  - `GET /api/vehicles/trims?year=&make=&model=` → proxy trims
  - `POST /api/my-vehicles` → fetch MPG for selected trim, convert to L/100km, save to my_vehicles (max 3)
  - `GET /api/my-vehicles` → return saved vehicles
  - `DELETE /api/my-vehicles/{id}` → remove a vehicle
- [ ] Build Vehicles tab UI: cascade dropdowns (Year → Make → Model → Trim), Add Vehicle button, vehicle cards with remove button
- [ ] Enforce max 3 vehicles (disable Add button when 3 selected)

### Test Criteria
- Cascade populates correctly: selecting a year loads makes, selecting a make loads models, etc.
- Adding a vehicle stores correct L/100km values in DB
- Vehicles persist across server restarts
- Max 3 enforced

---

## Slice 3 — Settings

**Goal:** User can set home address and gas price. Both persist to DB.

### Tasks
- [ ] Create `core.py`: geocode function using OpenStreetMap Nominatim (`httpx` GET request)
- [ ] Add API `GET /api/settings`: return all settings key/value pairs
- [ ] Add API `POST /api/settings/address`: receive address string, geocode it, store address + lat/lng in settings table
- [ ] Add API `POST /api/settings/gas-price`: receive $/L + optional notes, store in settings + append row to gas_price_log
- [ ] Add API `GET /api/settings/gas-log`: return all gas_price_log rows
- [ ] Build Settings tab UI: home address field + save button, gas price field + save & log button, gas price log table
- [ ] On address save: show geocoded confirmation (city, province)
- [ ] On gas price save: update header display

### Test Criteria
- Address geocodes correctly and coordinates stored in DB
- Gas price saves and appears in log table
- Settings persist across server restarts

---

## Slice 4 — Locations

**Goal:** User can search for and save locations. Distance calculated and stored.

### Tasks
- [ ] Create OSRM distance function in `core.py`: given home lat/lng + destination lat/lng → one-way road distance (km) via OSRM public API
- [ ] Add API `GET /api/locations/search?q=`: geocode search query via Nominatim, return top 5 results with address + lat/lng
- [ ] Add API `POST /api/locations`: receive label, address, lat, lng → calculate distance from home → save to locations table
- [ ] Add API `GET /api/locations`: return all saved locations
- [ ] Add API `DELETE /api/locations/{id}`: remove a location
- [ ] Build Add Location modal UI: search input, results list, label field, confirm button
- [ ] Display saved locations in table (no costs yet — placeholder)
- [ ] Test: add 3 locations, verify distances calculated and stored

### Test Criteria
- Location search returns real results
- Distance from home is calculated via road routing (not straight line)
- Locations persist across restarts
- Removing a location removes it from the table

---

## Slice 5 — Calculations

**Goal:** Trip costs calculated for every location using current gas price and selected vehicles.

### Tasks
- [ ] Create `calculations.py`: `calc_costs(dist_km, days_per_week, l100km, gas_price)` → dict with trip_cost, per_100km, monthly, annual
- [ ] Add API `POST /api/calculate`: load all locations + active vehicles + gas price → return full cost table (one row per location, one cost block per vehicle)
- [ ] Wire Refresh button to `POST /api/calculate`
- [ ] Auto-calculate on page load if home address + gas price + at least one vehicle are set
- [ ] Verify formulas match spec exactly:
  - monthly = trip_cost × days_per_week × 4.33
  - annual = trip_cost × days_per_week × 52

### Test Criteria
- Costs match manual calculation for known inputs
- Monthly and annual update when days/week selector changes
- Auto-calculates on page load

---

## Slice 6 — Locations Table UI

**Goal:** Full locations table matching the spec and mockup.

### Tasks
- [ ] Build Tabulator or vanilla HTML table: Location | Distance | Days/Week | [Vehicle cost cols]
- [ ] Days/week column: inline `<select>` 1–7, default 5, triggers immediate recalculation of that row
- [ ] Per-vehicle column group header showing vehicle name + L/100km badge
- [ ] Format: Cost/Trip ($X.XX), Cost/100km ($X.XX), Monthly ($X,XXX), Annual ($X,XXX)
- [ ] Empty state: friendly message when no locations added yet
- [ ] Refresh button: re-fetches costs, updates status bar with timestamp
- [ ] Status bar: shows last calculated timestamp

### Test Criteria
- Days/week change updates monthly and annual instantly
- All columns format correctly
- Table updates after Refresh without page reload

---

## Slice 7 — Vehicle Management

**Goal:** User can add/remove up to 3 vehicles. Comparison columns appear/disappear accordingly.

### Tasks
- [ ] Wire vehicle cards (built in Slice 2) into locations table column groups
- [ ] Locations table: dynamically add/remove vehicle column groups when vehicles change
- [ ] Enforce max 3 vehicles — hide Add button when 3 are selected

### Test Criteria
- Adding a vehicle adds a column group to the locations table
- Removing a vehicle removes its column group
- Vehicle selections persist across restarts
- Max 3 enforced

---

## Slice 8 — Charts

**Goal:** Trip cost history and gas price history charts.

### Tasks
- [ ] Add API `GET /api/charts/trip-cost`: return trip_cost_history grouped by location, ordered by date
- [ ] Add API `GET /api/charts/gas-price`: return all gas_price_log rows ordered by date
- [ ] Build Charts tab with Chart.js:
  - Trip cost line chart: one line per location, x = date, y = cost per trip ($)
  - Gas price line chart: x = date, y = $/L
- [ ] Empty state for charts when no history exists yet
- [ ] Apply dark theme to Chart.js (grid color, label color)

### Test Criteria
- Charts render with correct data
- Each location has its own line in the trip cost chart
- Gas price chart shows all logged entries

---

## Slice 9 — Trip Cost History Logging

**Goal:** Every calculation run is snapshotted to DB for chart history.

### Tasks
- [ ] On every `POST /api/calculate`: for each location × vehicle combination, insert a row into trip_cost_history with: location_id, vehicle_id, gas_price, distance_km, combined_l100km, cost_per_trip, cost_per_100km, monthly_cost, annual_cost, calculated_at (timestamp)
- [ ] Deduplicate: if a snapshot for the same location + vehicle + date already exists, update rather than insert
- [ ] Verify chart data populates correctly after several refreshes

### Test Criteria
- History table grows with each unique calculation
- No duplicate rows for same location + vehicle + same day
- Charts reflect historical data correctly

---

## Slice 10 — Polish

**Goal:** App feels complete and handles edge cases gracefully.

### Tasks
- [ ] Loading spinners on all async operations (geocode, distance fetch, calculate)
- [ ] Error messages for: geocode failure, OSRM unreachable, no home address set, no vehicle selected
- [ ] Warn user if gas price has not been set
- [ ] Empty state on Locations tab when no locations added
- [ ] Responsive layout check (min width ~900px)
- [ ] Confirm dialog before removing a location or vehicle
- [ ] Test full flow end-to-end: fresh DB → set address → set gas price → add vehicle → add 3 locations → calculate → view charts

### Test Criteria
- No unhandled errors in console
- All error states show a useful message
- Full flow works on a fresh database

---

## Slice 11 — Build & Distribution

**Goal:** One script produces a distributable `.exe` with demo data and no personal information.

### Tasks
- [ ] Install Electron + electron-builder as dev dependencies
- [ ] Create Electron `main.js`: launches FastAPI as a child process, opens a BrowserWindow pointing to `http://127.0.0.1:8506`
- [ ] Create `electron-builder.yml`: app name, icon, output dir, files to include
- [ ] Create `build-package.ps1`:
  1. Copy `trip_data.db` → `dist/trip_data.db`
  2. On the copy: DELETE all rows from settings, my_vehicles, locations, gas_price_log, trip_cost_history
  3. INSERT demo settings: address = "123 Main Street, Toronto, ON", lat/lng for that address, gas_price = 1.65
  4. INSERT demo vehicle: insert 2022 Toyota Camry LE directly into my_vehicles with hardcoded fueleconomy_id + L/100km values (looked up once from fueleconomy.gov at build time)
  5. INSERT demo locations: "Toronto Pearson Airport" (~28km) and "Costco North York" (~12km) with coordinates and distances from demo address
  6. INSERT demo gas_price_log: 3 entries (1.55 / Feb, 1.61 / Mar, 1.65 / Apr)
  7. INSERT demo trip_cost_history: 2–3 snapshots per demo location
  8. Run `npx electron-builder` → output `TripCostAnalyzer-Setup.exe` to `/dist`
- [ ] Test built `.exe` on a clean machine (no Python, no dev tools)
- [ ] Verify: personal data from developer's DB is NOT present in the `.exe`

### Test Criteria
- `.exe` launches without installing Python or any runtime
- Demo data visible on first open
- Developer's home address, vehicles, and locations are NOT in the distributed build
- Vehicle search (fueleconomy.gov) works from the built app

---

## File Structure (target end state)

```
TripCostAnalyzer/
├── server.py               # FastAPI backend
├── models.py               # SQLAlchemy table models
├── db.py                   # DB engine + session
├── core.py                 # Geocoding, OSRM distance, utility functions
├── calculations.py         # Trip cost formulas
├── vehicles.py             # fueleconomy.gov API client
├── requirements.txt        # Python dependencies
├── trip_data.db            # SQLite database (gitignored)
├── web/
│   ├── index.html          # Main UI
│   └── app.js              # All frontend JS
├── electron/
│   ├── main.js             # Electron entry point
│   └── electron-builder.yml
├── build-package.ps1       # Distribution build script
├── StartApp.bat            # Dev launcher
├── StartApp.ps1            # Dev launcher (PS1)
├── readme.txt              # End-user guide
├── spec.md                 # Specification
└── BUILDPLAN.md            # This file
```

---

## Revision Log

| Rev | Date | Changes |
|---|---|---|
| 1.0 | 2026-04-10 | Initial build plan — 11 slices, all tasks, file structure |
| 1.1 | 2026-04-10 | Replaced Slice 2 (NRCan Import) with fueleconomy.gov live vehicle search; removed vehicles reference table; updated Slice 7 and Slice 11 accordingly |
