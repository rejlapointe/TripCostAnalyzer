def calc_costs(dist_km: float, days_per_week: int, l100km: float, gas_price: float) -> dict:
    """
    Calculate trip costs from spec formulas.
    dist_km      — one-way road distance in km
    days_per_week — how many days/week the user makes this trip
    l100km       — combined fuel consumption in L/100km
    gas_price    — current gas price in $/L
    """
    round_trip_km  = dist_km * 2
    fuel_used      = round_trip_km * l100km / 100          # litres per round trip
    cost_per_trip  = round(fuel_used * gas_price, 2)        # $
    weekly  = round(cost_per_trip * days_per_week, 2)
    monthly = round(cost_per_trip * days_per_week * 4.33, 2)
    annual  = round(cost_per_trip * days_per_week * 52, 2)
    return {
        "cost_per_trip": cost_per_trip,
        "weekly":        weekly,
        "monthly":       monthly,
        "annual":        annual,
    }
