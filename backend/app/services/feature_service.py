from typing import Dict, Any


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def compute_risk_features_from_weather(weather: Dict[str, Any]) -> Dict[str, Any]:
    if weather is None:
        return {
            "risk_level": "unknown",
            "confidence": 0.0,
            "top_drivers": [],
            "evidence": {},
        }

    t = weather.get("avg_temperature_c")
    p = weather.get("avg_precipitation_mm")
    trend = weather.get("precip_trend_last_30d")

    if t is None or p is None or trend is None:
        return {
            "risk_level": "unknown",
            "confidence": 0.0,
            "top_drivers": ["insufficient live environmental data"],
            "evidence": weather,
        }

    score = 0
    drivers = []

    # temperature driver
    if t >= 33:
        score += 2
        drivers.append("high average temperature")
    elif t >= 30:
        score += 1
        drivers.append("moderately high temperature")
    else:
        drivers.append("temperature near normal")

    # precipitation driver
    if p <= 0.5:
        score += 2
        drivers.append("very low precipitation")
    elif p <= 2:
        score += 1
        drivers.append("below normal precipitation")
    else:
        drivers.append("adequate precipitation")

    # trend driver
    if trend < -10:
        score += 2
        drivers.append("declining rainfall trend")
    elif trend < 0:
        score += 1
        drivers.append("slightly decreasing rainfall trend")
    else:
        drivers.append("stable/increasing rainfall trend")

    if score >= 5:
        risk = "high"
        confidence = 0.92
    elif score >= 3:
        risk = "medium"
        confidence = 0.65
    elif score >= 1:
        risk = "low"
        confidence = 0.45
    else:
        risk = "low"
        confidence = 0.35

    return {
        "risk_level": risk,
        "confidence": confidence,
        "top_drivers": drivers,
        "evidence": weather,
    }


def build_model_feature_vector(environment: Dict[str, Any]) -> Dict[str, float]:
    weather = environment.get("weather", {})
    geospatial = environment.get("geospatial", {})

    return {
        "avg_temperature_c": _as_float(weather.get("avg_temperature_c"), 0.0),
        "avg_precipitation_mm": _as_float(weather.get("avg_precipitation_mm"), 0.0),
        "precip_trend_last_30d": _as_float(weather.get("precip_trend_last_30d"), 0.0),
        "vegetation_anomaly": _as_float(geospatial.get("vegetation_anomaly"), 0.0),
        "soil_moisture_percentile": _as_float(geospatial.get("soil_moisture_percentile"), 0.5),
        "drought_index": _as_float(geospatial.get("drought_index"), 0.5),
        "crop_sensitivity": _as_float(geospatial.get("crop_sensitivity"), 0.5),
    }
