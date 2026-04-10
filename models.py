from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from db import Base


class MyVehicle(Base):
    """User's selected vehicles (max 3). Fuel data fetched from fueleconomy.gov and stored at time of selection."""
    __tablename__ = "my_vehicles"

    id              = Column(Integer, primary_key=True, index=True)
    fueleconomy_id  = Column(Integer, nullable=False)   # fueleconomy.gov vehicle ID
    year            = Column(Integer, nullable=False)
    make            = Column(String, nullable=False)
    model           = Column(String, nullable=False)
    trim            = Column(String)
    city_l100km     = Column(Float)
    hwy_l100km      = Column(Float)
    combined_l100km = Column(Float, nullable=False)
    tank_size_l     = Column(Float, nullable=True)
    display_order   = Column(Integer, default=0)
    added_at        = Column(DateTime, default=datetime.utcnow)


class Setting(Base):
    """Key/value store for app settings."""
    __tablename__ = "settings"

    key   = Column(String, primary_key=True)
    value = Column(String)


class Location(Base):
    """User's saved trip destinations."""
    __tablename__ = "locations"

    id            = Column(Integer, primary_key=True, index=True)
    label         = Column(String, nullable=False)
    address       = Column(String, nullable=False)
    lat           = Column(Float)
    lng           = Column(Float)
    distance_km   = Column(Float)        # one-way road distance from home
    days_per_week = Column(Integer, default=5)
    added_at      = Column(DateTime, default=datetime.utcnow)


class GasPriceLog(Base):
    """Historical gas price entries."""
    __tablename__ = "gas_price_log"

    id              = Column(Integer, primary_key=True, index=True)
    price_per_litre = Column(Float, nullable=False)
    recorded_at     = Column(DateTime, default=datetime.utcnow)
    notes           = Column(String)


class TripCostHistory(Base):
    """Snapshot of calculated trip costs — one row per location × vehicle × calculation run."""
    __tablename__ = "trip_cost_history"

    id              = Column(Integer, primary_key=True, index=True)
    location_id     = Column(Integer, ForeignKey("locations.id"), nullable=False)
    my_vehicle_id   = Column(Integer, ForeignKey("my_vehicles.id"), nullable=False)
    gas_price       = Column(Float)
    distance_km     = Column(Float)
    combined_l100km = Column(Float)
    cost_per_trip   = Column(Float)
    weekly_cost     = Column(Float)
    monthly_cost    = Column(Float)
    annual_cost     = Column(Float)
    calculated_at   = Column(DateTime, default=datetime.utcnow)
