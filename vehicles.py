import httpx

BASE = "https://www.fueleconomy.gov/ws/rest"
HEADERS = {"Accept": "application/json"}


def _items(data) -> list:
    """Normalize fueleconomy.gov menuItem response to a plain list of {text, value} dicts."""
    items = data.get("menuItem", [])
    if isinstance(items, dict):
        items = [items]
    return items


def get_years() -> list[str]:
    r = httpx.get(f"{BASE}/vehicle/menu/year", headers=HEADERS, timeout=10)
    r.raise_for_status()
    return [item["value"] for item in _items(r.json())]


def get_makes(year: str) -> list[str]:
    r = httpx.get(f"{BASE}/vehicle/menu/make", params={"year": year}, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return [item["value"] for item in _items(r.json())]


def get_models(year: str, make: str) -> list[str]:
    r = httpx.get(f"{BASE}/vehicle/menu/model", params={"year": year, "make": make}, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return [item["value"] for item in _items(r.json())]


def get_trims(year: str, make: str, model: str) -> list[dict]:
    """Returns list of {id, name} for each trim."""
    r = httpx.get(f"{BASE}/vehicle/menu/options", params={"year": year, "make": make, "model": model}, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return [{"id": item["value"], "name": item["text"]} for item in _items(r.json())]


def get_mpg(vehicle_id: str) -> dict:
    """Returns {city_mpg, hwy_mpg, combined_mpg} for the given fueleconomy.gov vehicle ID."""
    r = httpx.get(f"{BASE}/vehicle/{vehicle_id}", headers=HEADERS, timeout=10)
    r.raise_for_status()
    data = r.json()
    return {
        "city_mpg":     float(data.get("city08") or 0),
        "hwy_mpg":      float(data.get("highway08") or 0),
        "combined_mpg": float(data.get("comb08") or 0),
    }


def mpg_to_l100km(mpg: float) -> float:
    if not mpg or mpg <= 0:
        return None
    return round(235.215 / mpg, 1)
