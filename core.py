import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {"User-Agent": "TripCostAnalyzer/1.0"}


def search_addresses(street_number: str, street_name: str, city: str, state: str, country: str) -> list:
    """
    Structured address search using OpenStreetMap Nominatim.
    Returns up to 8 results as [{display_name, lat, lng}].
    """
    street = f"{street_number} {street_name}".strip()
    params = {
        "format":  "json",
        "limit":   8,
        "addressdetails": 1,
    }
    if street:    params["street"]  = street
    if city:      params["city"]    = city
    if state:     params["state"]   = state
    if country:   params["country"] = country

    r = httpx.get(
        NOMINATIM_URL,
        params=params,
        headers=NOMINATIM_HEADERS,
        timeout=10,
    )
    r.raise_for_status()
    return [
        {
            "display_name": result["display_name"],
            "lat":          float(result["lat"]),
            "lng":          float(result["lon"]),
        }
        for result in r.json()
    ]


def reverse_geocode(lat: float, lng: float) -> dict:
    """
    Reverse geocode coordinates using OpenStreetMap Nominatim.
    Returns {display_name, lat, lng, street_number, street_name, city, state, country}.
    """
    r = httpx.get(
        "https://nominatim.openstreetmap.org/reverse",
        params={"lat": lat, "lon": lng, "format": "json", "addressdetails": 1},
        headers=NOMINATIM_HEADERS,
        timeout=10,
    )
    r.raise_for_status()
    result = r.json()
    if "error" in result:
        raise ValueError(f"Reverse geocode failed: {result['error']}")

    addr = result.get("address", {})
    city = (
        addr.get("city") or
        addr.get("town") or
        addr.get("village") or
        addr.get("municipality") or
        addr.get("hamlet") or
        ""
    )
    return {
        "display_name":  result["display_name"],
        "lat":           float(result["lat"]),
        "lng":           float(result["lon"]),
        "street_number": addr.get("house_number", ""),
        "street_name":   addr.get("road", ""),
        "city":          city,
        "state":         addr.get("state", ""),
        "country":       addr.get("country", ""),
    }


def search_places(query: str) -> list:
    """
    Free-text place/address search via Nominatim.
    Good for named places like 'Ottawa Airport', 'Costco Kanata'.
    Returns up to 8 results as [{display_name, lat, lng}].
    """
    r = httpx.get(
        NOMINATIM_URL,
        params={"q": query, "format": "json", "limit": 8, "addressdetails": 0},
        headers=NOMINATIM_HEADERS,
        timeout=10,
    )
    r.raise_for_status()
    return [
        {
            "display_name": result["display_name"],
            "lat":          float(result["lat"]),
            "lng":          float(result["lon"]),
        }
        for result in r.json()
    ]


def get_road_distance(home_lat: float, home_lng: float, dest_lat: float, dest_lng: float) -> float:
    """
    Calculate one-way road distance in km using Valhalla (openstreetmap.de).
    """
    r = httpx.post(
        "https://valhalla1.openstreetmap.de/route",
        json={
            "locations": [
                {"lat": home_lat, "lon": home_lng},
                {"lat": dest_lat, "lon": dest_lng},
            ],
            "costing": "auto",
            "units": "km",
        },
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    if "trip" not in data:
        raise ValueError("Routing service could not find a route between these locations.")
    return round(data["trip"]["summary"]["length"], 1)


def geocode(address: str) -> dict:
    """
    Geocode an address using OpenStreetMap Nominatim.
    Returns {lat, lng, display_name} or raises ValueError if not found.
    """
    r = httpx.get(
        NOMINATIM_URL,
        params={"q": address, "format": "json", "limit": 1},
        headers=NOMINATIM_HEADERS,
        timeout=10,
    )
    r.raise_for_status()
    results = r.json()
    if not results:
        raise ValueError(f"Address not found: {address}")
    result = results[0]
    return {
        "lat":          float(result["lat"]),
        "lng":          float(result["lon"]),
        "display_name": result["display_name"],
    }
