from typing import Any, Dict, List

from backend.app.services.feature_service import build_model_feature_vector
from backend.app.services.modeling_service import score_with_ml_model


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _add_driver(drivers: List[str], label: str) -> None:
    if label not in drivers:
        drivers.append(label)


def _confidence_band(confidence: float) -> str:
    if confidence >= 0.78:
        return "high"
    if confidence >= 0.58:
        return "medium"
    return "low"


def _project_environment(environment: Dict[str, Any], horizon_days: int) -> Dict[str, Any]:
    """Generate a horizon-specific environment projection for short-term risk forecasting."""
    weather = environment.get("weather", {}).copy() if environment.get("weather") else {}
    geospatial = environment.get("geospatial", {}).copy() if environment.get("geospatial") else {}

    base_precip = float(weather.get("avg_precipitation_mm") if weather.get("avg_precipitation_mm") is not None else 0.0)
    base_temp = float(weather.get("avg_temperature_c") if weather.get("avg_temperature_c") is not None else 0.0)
    precip_trend = float(weather.get("precip_trend_last_30d") if weather.get("precip_trend_last_30d") is not None else 0.0)

    # Very simple linear forecast projection: extend 30-day trend into the new horizon.
    precip_delta = (precip_trend / 30.0) * horizon_days
    projected_precip = max(0.0, base_precip + precip_delta)

    # Temperature drift: assume small warming or cooling tendency based on existing trend.
    temperate_change_rate = 0.05
    projected_temp = base_temp + (0.01 * (horizon_days / 7.0))

    weather["avg_precipitation_mm"] = round(projected_precip, 2)
    weather["avg_temperature_c"] = round(projected_temp, 2)
    weather["precip_trend_last_30d"] = round(precip_trend, 2)

    return {
        **environment,
        "weather": weather,
        "geospatial": geospatial,
    }


def forecast_region_risk(environment: Dict[str, Any], horizons: List[int] = [7, 14, 30]) -> List[Dict[str, Any]]:
    """Compute a short-term risk forecast for specified horizons."""
    results = []
    for horizon in horizons:
        horizon_env = _project_environment(environment, horizon)
        horizon_score = compute_composite_score(horizon_env, include_forecast=False)
        confidence = float(horizon_score.get("confidence", 0.0))
        rainfall_trend = float(horizon_env.get("weather", {}).get("precip_trend_last_30d") or 0.0)
        trend_phrase = "stable rainfall pattern" if rainfall_trend >= 0 else "downward rainfall trend"
        reasoning = (
            f"{horizon}-day projection based on recent temperature conditions and a {trend_phrase}; "
            "uncertainty increases with longer horizons because this is a trend-based estimate."
        )

        results.append({
            "horizon_days": horizon,
            "risk_level": horizon_score.get("risk_level", "unknown"),
            "confidence": confidence,
            "confidence_band": _confidence_band(confidence - (0.04 if horizon >= 30 else 0.02 if horizon >= 14 else 0.0)),
            "score": float(horizon_score.get("score", 0.0)),
            "score_components": horizon_score.get("score_components", {}),
            "top_drivers": horizon_score.get("top_drivers", []),
            "reasoning": reasoning,
            "model_prediction": horizon_score.get("model_prediction"),
        })

    return results


def compute_composite_score(environment: Dict[str, Any], include_forecast: bool = True) -> Dict[str, Any]:
    weather = environment.get("weather", {})
    geospatial = environment.get("geospatial", {})

    if not weather:
        return {
            "risk_level": "unknown",
            "confidence": 0.0,
            "score": 0.0,
            "score_components": {},
            "top_drivers": [],
            "model_prediction": None,
        }

    temperature = float(weather.get("avg_temperature_c") if weather.get("avg_temperature_c") is not None else 0.0)
    precipitation = float(weather.get("avg_precipitation_mm") if weather.get("avg_precipitation_mm") is not None else 0.0)
    rainfall_trend = float(weather.get("precip_trend_last_30d") if weather.get("precip_trend_last_30d") is not None else 0.0)
    vegetation_anomaly = float(geospatial.get("vegetation_anomaly") if geospatial.get("vegetation_anomaly") is not None else 0.0)
    soil_moisture = float(geospatial.get("soil_moisture_percentile") if geospatial.get("soil_moisture_percentile") is not None else 0.5)
    drought_index = float(geospatial.get("drought_index") if geospatial.get("drought_index") is not None else 0.5)

    heat_component = 0.0
    moisture_component = 0.0
    trend_component = 0.0
    vegetation_component = 0.0
    soil_component = 0.0
    drought_component = 0.0
    drivers: List[str] = []

    if temperature >= 35:
        heat_component = 0.95
        _add_driver(drivers, "extreme heat stress")
    elif temperature >= 32:
        heat_component = 0.7
        _add_driver(drivers, "high average temperature")
    elif temperature >= 29:
        heat_component = 0.35
        _add_driver(drivers, "moderately high temperature")
    else:
        _add_driver(drivers, "temperature near seasonal baseline")

    if precipitation <= 1:
        moisture_component = 0.95
        _add_driver(drivers, "severe rainfall deficit")
    elif precipitation <= 3:
        moisture_component = 0.65
        _add_driver(drivers, "below normal precipitation")
    elif precipitation <= 7:
        moisture_component = 0.3
        _add_driver(drivers, "tight moisture conditions")
    else:
        _add_driver(drivers, "adequate precipitation")

    if rainfall_trend <= -8:
        trend_component = 0.8
        _add_driver(drivers, "persistent rainfall decline")
    elif rainfall_trend < 0:
        trend_component = 0.45
        _add_driver(drivers, "slightly decreasing rainfall trend")
    else:
        _add_driver(drivers, "stable to improving rainfall trend")

    if vegetation_anomaly <= -0.3:
        vegetation_component = 0.8
        _add_driver(drivers, "sharp vegetation anomaly")
    elif vegetation_anomaly <= -0.15:
        vegetation_component = 0.45
        _add_driver(drivers, "negative vegetation anomaly")

    if soil_moisture <= 0.25:
        soil_component = 0.7
        _add_driver(drivers, "low soil moisture percentile")
    elif soil_moisture <= 0.4:
        soil_component = 0.35
        _add_driver(drivers, "moderately weak soil moisture")

    if drought_index >= 0.7:
        drought_component = 0.75
        _add_driver(drivers, "elevated drought index")
    elif drought_index >= 0.5:
        drought_component = 0.35
        _add_driver(drivers, "moderate drought signal")

    weighted_score = (
        heat_component * 0.22
        + moisture_component * 0.22
        + trend_component * 0.14
        + vegetation_component * 0.18
        + soil_component * 0.12
        + drought_component * 0.12
    )

    model_prediction = score_with_ml_model(build_model_feature_vector(environment))
    ensemble_score = weighted_score * 0.55 + model_prediction["risk_probability"] * 0.45
    confidence = _clamp(0.48 + ensemble_score * 0.4, 0.35, 0.97)

    if ensemble_score >= 0.72:
        risk_level = "high"
    elif ensemble_score >= 0.40:
        risk_level = "medium"
    else:
        risk_level = "low"

    for explanation in model_prediction.get("top_explanations", []):
        humanized = explanation.replace("_", " ")
        if humanized not in drivers:
            drivers.append(humanized)

    risk_record = {
        "risk_level": risk_level,
        "confidence": round(confidence, 2),
        "score": round(ensemble_score, 3),
        "score_components": {
            "heat": round(heat_component, 3),
            "moisture": round(moisture_component, 3),
            "trend": round(trend_component, 3),
            "vegetation": round(vegetation_component, 3),
            "soil_moisture": round(soil_component, 3),
            "drought": round(drought_component, 3),
        },
        "top_drivers": drivers[:5],
        "model_prediction": model_prediction,
        "feature_vector": build_model_feature_vector(environment),
    }

    # Future risk forecast for horizons 7, 14, and 30 days
    if include_forecast:
        risk_record["forecast"] = forecast_region_risk(environment)

    return risk_record
