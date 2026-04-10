from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from datetime import datetime

import db
import models
import vehicles as veh
import core
import calculations as calc


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=db.engine)
    # Migrations: add new columns to existing tables if not present
    with db.engine.connect() as conn:
        for sql in [
            "ALTER TABLE my_vehicles ADD COLUMN tank_size_l REAL",
            "ALTER TABLE trip_cost_history ADD COLUMN weekly_cost REAL",
        ]:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass  # column already exists
    yield


app = FastAPI(title="Trip Cost Analyzer", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="web"), name="static")


@app.get("/")
async def root():
    return FileResponse("web/index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── VEHICLE SEARCH (fueleconomy.gov proxy) ────────────────────────────────────

@app.get("/api/vehicles/years")
async def api_years():
    try:
        return {"years": veh.get_years()}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"fueleconomy.gov error: {e}")


@app.get("/api/vehicles/makes")
async def api_makes(year: str):
    try:
        return {"makes": veh.get_makes(year)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"fueleconomy.gov error: {e}")


@app.get("/api/vehicles/models")
async def api_models(year: str, make: str):
    try:
        return {"models": veh.get_models(year, make)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"fueleconomy.gov error: {e}")


@app.get("/api/vehicles/trims")
async def api_trims(year: str, make: str, model: str):
    try:
        return {"trims": veh.get_trims(year, make, model)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"fueleconomy.gov error: {e}")


# ── MY VEHICLES ───────────────────────────────────────────────────────────────

class AddVehicleRequest(BaseModel):
    fueleconomy_id: str
    year: int
    make: str
    model: str
    trim: str


@app.get("/api/my-vehicles")
async def get_my_vehicles(session: Session = Depends(db.get_db)):
    rows = session.query(models.MyVehicle).order_by(models.MyVehicle.display_order).all()
    return {"vehicles": [
        {
            "id":              v.id,
            "fueleconomy_id":  v.fueleconomy_id,
            "year":            v.year,
            "make":            v.make,
            "model":           v.model,
            "trim":            v.trim,
            "city_l100km":     v.city_l100km,
            "hwy_l100km":      v.hwy_l100km,
            "combined_l100km": v.combined_l100km,
            "tank_size_l":     v.tank_size_l,
            "added_at":        v.added_at.isoformat() if v.added_at else None,
        }
        for v in rows
    ]}


@app.post("/api/my-vehicles")
async def add_my_vehicle(req: AddVehicleRequest, session: Session = Depends(db.get_db)):
    count = session.query(models.MyVehicle).count()
    if count >= 3:
        raise HTTPException(status_code=400, detail="Maximum 3 vehicles allowed.")

    try:
        mpg = veh.get_mpg(req.fueleconomy_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch MPG: {e}")

    v = models.MyVehicle(
        fueleconomy_id  = int(req.fueleconomy_id),
        year            = req.year,
        make            = req.make,
        model           = req.model,
        trim            = req.trim,
        city_l100km     = veh.mpg_to_l100km(mpg["city_mpg"]),
        hwy_l100km      = veh.mpg_to_l100km(mpg["hwy_mpg"]),
        combined_l100km = veh.mpg_to_l100km(mpg["combined_mpg"]),
        display_order   = count,
        added_at        = datetime.utcnow(),
    )
    session.add(v)
    session.commit()
    session.refresh(v)
    return {
        "id":              v.id,
        "fueleconomy_id":  v.fueleconomy_id,
        "year":            v.year,
        "make":            v.make,
        "model":           v.model,
        "trim":            v.trim,
        "city_l100km":     v.city_l100km,
        "hwy_l100km":      v.hwy_l100km,
        "combined_l100km": v.combined_l100km,
    }


class UpdateVehicleTankRequest(BaseModel):
    tank_size_l: float


@app.patch("/api/my-vehicles/{vehicle_id}/tank")
async def update_vehicle_tank(vehicle_id: int, req: UpdateVehicleTankRequest, session: Session = Depends(db.get_db)):
    v = session.query(models.MyVehicle).filter(models.MyVehicle.id == vehicle_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found.")
    v.tank_size_l = req.tank_size_l
    session.commit()
    return {"id": v.id, "tank_size_l": v.tank_size_l}


@app.delete("/api/my-vehicles/{vehicle_id}")
async def delete_my_vehicle(vehicle_id: int, session: Session = Depends(db.get_db)):
    v = session.query(models.MyVehicle).filter(models.MyVehicle.id == vehicle_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found.")
    session.delete(v)
    session.commit()
    return {"status": "deleted"}


# ── SETTINGS HELPERS ──────────────────────────────────────────────────────────

def get_setting(session: Session, key: str) -> str | None:
    row = session.query(models.Setting).filter(models.Setting.key == key).first()
    return row.value if row else None


def set_setting(session: Session, key: str, value: str):
    row = session.query(models.Setting).filter(models.Setting.key == key).first()
    if row:
        row.value = value
    else:
        session.add(models.Setting(key=key, value=value))


# ── SETTINGS ENDPOINTS ────────────────────────────────────────────────────────

@app.get("/api/geocode/search")
async def geocode_search(
    street_number: str = "",
    street_name:   str = "",
    city:          str = "",
    state:         str = "",
    country:       str = "Canada",
):
    if not street_name and not city:
        return {"results": []}
    try:
        return {"results": core.search_addresses(street_number, street_name, city, state, country)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Geocoding search failed: {e}")


@app.get("/api/geocode/reverse")
async def geocode_reverse(lat: float, lng: float):
    try:
        return core.reverse_geocode(lat, lng)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Reverse geocode failed: {e}")


@app.get("/api/settings")
async def get_settings(session: Session = Depends(db.get_db)):
    keys = ["home_address", "home_lat", "home_lng", "current_gas_price", "last_gas_price_update"]
    return {k: get_setting(session, k) for k in keys}


class AddressRequest(BaseModel):
    address: str


@app.post("/api/settings/address")
async def save_address(req: AddressRequest, session: Session = Depends(db.get_db)):
    try:
        geo = core.geocode(req.address)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Geocoding failed: {e}")

    set_setting(session, "home_address", req.address)
    set_setting(session, "home_lat",     str(geo["lat"]))
    set_setting(session, "home_lng",     str(geo["lng"]))
    session.commit()
    return {"display_name": geo["display_name"], "lat": geo["lat"], "lng": geo["lng"]}


class GasPriceRequest(BaseModel):
    price: float
    notes: str = ""


@app.post("/api/settings/gas-price")
async def save_gas_price(req: GasPriceRequest, session: Session = Depends(db.get_db)):
    now = datetime.utcnow()
    set_setting(session, "current_gas_price",    str(req.price))
    set_setting(session, "last_gas_price_update", now.isoformat())
    session.add(models.GasPriceLog(
        price_per_litre = req.price,
        recorded_at     = now,
        notes           = req.notes or None,
    ))
    session.commit()
    return {"price": req.price, "recorded_at": now.isoformat()}


@app.get("/api/settings/gas-log")
async def get_gas_log(session: Session = Depends(db.get_db)):
    rows = session.query(models.GasPriceLog).order_by(models.GasPriceLog.recorded_at.desc()).all()
    return {"log": [
        {
            "id":              r.id,
            "price_per_litre": r.price_per_litre,
            "recorded_at":     r.recorded_at.isoformat() if r.recorded_at else None,
            "notes":           r.notes,
        }
        for r in rows
    ]}


# ── LOCATIONS ─────────────────────────────────────────────────────────────────

@app.get("/api/locations/search")
async def locations_search(q: str = ""):
    if not q.strip():
        return {"results": []}
    try:
        return {"results": core.search_places(q)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Place search failed: {e}")


def _location_dict(loc: models.Location) -> dict:
    return {
        "id":            loc.id,
        "label":         loc.label,
        "address":       loc.address,
        "lat":           loc.lat,
        "lng":           loc.lng,
        "distance_km":   loc.distance_km,
        "days_per_week": loc.days_per_week,
        "added_at":      loc.added_at.isoformat() if loc.added_at else None,
    }


@app.get("/api/locations")
async def get_locations(session: Session = Depends(db.get_db)):
    rows = session.query(models.Location).order_by(models.Location.added_at).all()
    return {"locations": [_location_dict(r) for r in rows]}


class AddLocationRequest(BaseModel):
    label:         str
    address:       str
    lat:           float
    lng:           float
    days_per_week: int = 5


@app.post("/api/locations")
async def add_location(req: AddLocationRequest, session: Session = Depends(db.get_db)):
    home_lat = get_setting(session, "home_lat")
    home_lng = get_setting(session, "home_lng")
    if not home_lat or not home_lng:
        raise HTTPException(status_code=400, detail="Home address not set. Go to Settings first.")

    try:
        distance_km = core.get_road_distance(float(home_lat), float(home_lng), req.lat, req.lng)
    except Exception as e:
        msg = str(e)
        if "timed out" in msg.lower() or "timeout" in msg.lower():
            detail = "Routing timed out. Check your internet connection and try again."
        elif "could not find a route" in msg.lower():
            detail = "No road route found between home and that destination. Try a different location."
        else:
            detail = "Could not calculate road distance. The routing service may be temporarily unavailable — try again in a moment."
        raise HTTPException(status_code=502, detail=detail)

    loc = models.Location(
        label         = req.label,
        address       = req.address,
        lat           = req.lat,
        lng           = req.lng,
        distance_km   = distance_km,
        days_per_week = req.days_per_week,
        added_at      = datetime.utcnow(),
    )
    session.add(loc)
    session.commit()
    session.refresh(loc)
    return _location_dict(loc)


@app.delete("/api/locations/{location_id}")
async def delete_location(location_id: int, session: Session = Depends(db.get_db)):
    loc = session.query(models.Location).filter(models.Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found.")
    session.delete(loc)
    session.commit()
    return {"status": "deleted"}


class UpdateLocationRequest(BaseModel):
    days_per_week: int


@app.patch("/api/locations/{location_id}")
async def update_location(location_id: int, req: UpdateLocationRequest, session: Session = Depends(db.get_db)):
    loc = session.query(models.Location).filter(models.Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found.")
    loc.days_per_week = req.days_per_week
    session.commit()
    session.refresh(loc)
    return _location_dict(loc)


# ── CALCULATE ─────────────────────────────────────────────────────────────────

@app.post("/api/calculate")
async def calculate(session: Session = Depends(db.get_db)):
    gas_price_str = get_setting(session, "current_gas_price")
    if not gas_price_str:
        raise HTTPException(status_code=400, detail="Gas price not set. Go to Settings first.")

    gas_price = float(gas_price_str)
    locations = session.query(models.Location).order_by(models.Location.added_at).all()
    vehicles  = session.query(models.MyVehicle).order_by(models.MyVehicle.display_order).all()

    result_locations = []
    for loc in locations:
        costs_by_vehicle = {}
        for v in vehicles:
            if loc.distance_km is None:
                continue
            costs = calc.calc_costs(loc.distance_km, loc.days_per_week, v.combined_l100km, gas_price)
            full_tank_cost = round(v.tank_size_l * gas_price, 2) if v.tank_size_l else None
            costs_by_vehicle[v.id] = {
                "vehicle_id":       v.id,
                "vehicle_label":    f"{v.year} {v.make} {v.model}",
                "full_tank_cost":   full_tank_cost,
                **costs,
            }
        result_locations.append({
            **_location_dict(loc),
            "costs": costs_by_vehicle,
        })

    # ── Slice 9: log history (dedup by location + vehicle + calendar day) ────────
    today = datetime.utcnow().date().isoformat()
    for loc in locations:
        if loc.distance_km is None:
            continue
        for v in vehicles:
            costs = calc.calc_costs(loc.distance_km, loc.days_per_week, v.combined_l100km, gas_price)
            existing = session.query(models.TripCostHistory).filter(
                models.TripCostHistory.location_id   == loc.id,
                models.TripCostHistory.my_vehicle_id == v.id,
                func.date(models.TripCostHistory.calculated_at) == today,
            ).first()
            if existing:
                existing.gas_price    = gas_price
                existing.cost_per_trip = costs["cost_per_trip"]
                existing.weekly_cost   = costs["weekly"]
                existing.monthly_cost  = costs["monthly"]
                existing.annual_cost   = costs["annual"]
                existing.calculated_at = datetime.utcnow()
            else:
                session.add(models.TripCostHistory(
                    location_id    = loc.id,
                    my_vehicle_id  = v.id,
                    gas_price      = gas_price,
                    distance_km    = loc.distance_km,
                    combined_l100km = v.combined_l100km,
                    cost_per_trip  = costs["cost_per_trip"],
                    weekly_cost    = costs["weekly"],
                    monthly_cost   = costs["monthly"],
                    annual_cost    = costs["annual"],
                    calculated_at  = datetime.utcnow(),
                ))
    session.commit()

    return {
        "locations":    result_locations,
        "vehicles":     [
            {
                "id":              v.id,
                "label":           f"{v.year} {v.make} {v.model}",
                "combined_l100km": v.combined_l100km,
                "full_tank_cost":  round(v.tank_size_l * gas_price, 2) if v.tank_size_l else None,
            }
            for v in vehicles
        ],
        "gas_price":     gas_price,
        "calculated_at": datetime.utcnow().isoformat(),
    }


# ── CHARTS ────────────────────────────────────────────────────────────────────

@app.get("/api/charts/trip-cost")
async def charts_trip_cost(session: Session = Depends(db.get_db)):
    from collections import defaultdict
    rows = (
        session.query(models.TripCostHistory, models.Location, models.MyVehicle)
        .join(models.Location,  models.TripCostHistory.location_id   == models.Location.id)
        .join(models.MyVehicle, models.TripCostHistory.my_vehicle_id == models.MyVehicle.id)
        .order_by(models.TripCostHistory.calculated_at)
        .all()
    )
    if not rows:
        return {"labels": [], "datasets": []}

    all_dates = sorted(set(h.calculated_at.strftime("%Y-%m-%d") for h, _, _ in rows))
    labels    = [datetime.strptime(d, "%Y-%m-%d").strftime("%b %d") for d in all_dates]

    series: dict = defaultdict(dict)
    for hist, loc, veh in rows:
        key = f"{loc.label} · {veh.year} {veh.make}"
        series[key][hist.calculated_at.strftime("%Y-%m-%d")] = hist.cost_per_trip

    colors   = ["#2f81f7", "#3fb950", "#f0883e", "#d29922", "#f85149", "#a371f7"]
    datasets = []
    for i, (label, by_date) in enumerate(series.items()):
        color = colors[i % len(colors)]
        datasets.append({
            "label":           label,
            "data":            [by_date.get(d) for d in all_dates],
            "borderColor":     color,
            "backgroundColor": color + "33",
            "spanGaps":        True,
        })

    return {"labels": labels, "datasets": datasets}


@app.get("/api/charts/gas-price")
async def charts_gas_price(session: Session = Depends(db.get_db)):
    rows = session.query(models.GasPriceLog).order_by(models.GasPriceLog.recorded_at).all()
    return {
        "labels": [r.recorded_at.strftime("%b %d, %Y") for r in rows],
        "datasets": [{
            "label":           "Gas Price ($/L)",
            "data":            [r.price_per_litre for r in rows],
            "borderColor":     "#3fb950",
            "backgroundColor": "#3fb95033",
        }],
    }
