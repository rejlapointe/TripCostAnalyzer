from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

import db
import models
import vehicles as veh


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=db.engine)
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


@app.delete("/api/my-vehicles/{vehicle_id}")
async def delete_my_vehicle(vehicle_id: int, session: Session = Depends(db.get_db)):
    v = session.query(models.MyVehicle).filter(models.MyVehicle.id == vehicle_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found.")
    session.delete(v)
    session.commit()
    return {"status": "deleted"}
