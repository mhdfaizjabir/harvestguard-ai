from typing import Dict, Any

from backend.app.services.ingestion_service import get_environment_bundle
from backend.app.services.risk_service import compute_composite_score


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default

def simulate_scenario(region: Dict[str, Any], rainfall_reduction_percent: float = 20.0) -> Dict[str, Any]:
    """
    Simulate what-if scenario by reducing rainfall and recomputing risk.
    """
    environment = get_environment_bundle(region["latitude"], region["longitude"])
    weather = environment.get("weather")

    if weather is None:
        return {
            "original_risk": {"risk_level": "unknown", "confidence": 0.0, "top_drivers": []},
            "simulated_risk": {"risk_level": "unknown", "confidence": 0.0, "top_drivers": []},
            "scenario": f"Rainfall reduced by {rainfall_reduction_percent}%"
        }

    # Simulate reduced rainfall
    original_precip = _as_float(weather.get("avg_precipitation_mm"), 0.0)
    reduced_precip = original_precip * (1 - rainfall_reduction_percent / 100.0)

    simulated_weather = weather.copy()
    simulated_weather["avg_precipitation_mm"] = reduced_precip
    simulated_weather["precip_trend_last_30d"] = _as_float(weather.get("precip_trend_last_30d"), 0.0) - (original_precip - reduced_precip)

    simulated_environment = {
        **environment,
        "weather": simulated_weather,
    }

    original_risk = compute_composite_score(environment)
    simulated_risk = compute_composite_score(simulated_environment)

    return {
        "original_risk": {
            "risk_level": original_risk["risk_level"],
            "confidence": original_risk["confidence"],
            "score": original_risk["score"],
            "score_components": original_risk["score_components"],
            "top_drivers": original_risk["top_drivers"],
            "model_prediction": original_risk.get("model_prediction"),
        },
        "simulated_risk": {
            "risk_level": simulated_risk["risk_level"],
            "confidence": simulated_risk["confidence"],
            "score": simulated_risk["score"],
            "score_components": simulated_risk["score_components"],
            "top_drivers": simulated_risk["top_drivers"],
            "model_prediction": simulated_risk.get("model_prediction"),
        },
        "scenario": f"Rainfall reduced by {rainfall_reduction_percent}% over 30 days",
        "evidence": {
            "original_weather": weather,
            "simulated_weather": simulated_weather,
            "geospatial_context": environment.get("geospatial", {}),
        }
    }
