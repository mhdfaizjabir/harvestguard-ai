from typing import Any, Dict

from backend.app.agents.response_agent import generate_brief, qa_check_response
from backend.app.services.evidence_service import build_evidence_packet
from backend.app.services.explainability_service import build_explainability_record
from backend.app.services.feature_service import compute_risk_features_from_weather
from backend.app.services.ingestion_service import get_environment_bundle
from backend.app.services.risk_service import compute_composite_score
from backend.app.services.scenario_service import simulate_scenario
from backend.app.services.training_service import build_training_row_from_environment


def run_region_analysis(region: Dict[str, Any]) -> Dict[str, Any]:
    environment = get_environment_bundle(
        latitude=region["latitude"],
        longitude=region["longitude"],
    )
    feature_summary = compute_risk_features_from_weather(environment["weather"])
    composite_risk = compute_composite_score(environment)
    feature_vector = composite_risk.get("feature_vector") or {}
    explainability = build_explainability_record(feature_vector) if feature_vector else None

    training_row = build_training_row_from_environment(
        environment,
        label=composite_risk["risk_level"],
    )

    risk_record = {
        "risk_level": composite_risk["risk_level"],
        "confidence": composite_risk["confidence"],
        "score": composite_risk["score"],
        "score_components": composite_risk["score_components"],
        "top_drivers": composite_risk["top_drivers"] or feature_summary.get("top_drivers", []),
        "model_prediction": composite_risk.get("model_prediction"),
        "forecast": composite_risk.get("forecast", []),
    }
    evidence_packet = build_evidence_packet(
        region=region,
        weather=environment["weather"],
        geospatial=environment["geospatial"],
        risk_record=risk_record,
        explainability=explainability,
    )

    return {
        "region": region,
        "environment": environment,
        "weather": environment["weather"],
        "geospatial": environment["geospatial"],
        "risk_record": risk_record,
        "feature_summary": feature_summary,
        "training_row": training_row,
        "evidence_packet": evidence_packet,
    }


def generate_region_brief(region: Dict[str, Any], audience: str = "ngo") -> Dict[str, Any]:
    analysis = run_region_analysis(region)
    brief = generate_brief(region["name"], analysis["risk_record"], analysis["evidence_packet"], audience=audience)
    approved_brief = qa_check_response(brief, analysis["evidence_packet"])

    return {
        "analysis": analysis,
        "brief": approved_brief,
    }


def generate_scenario_brief(region: Dict[str, Any], rainfall_reduction_percent: float, audience: str = "ngo") -> Dict[str, Any]:
    analysis = run_region_analysis(region)
    scenario_result = simulate_scenario(region, rainfall_reduction_percent)

    scenario_packet = build_evidence_packet(
        region=region,
        weather=analysis["weather"],
        geospatial=analysis["geospatial"],
        risk_record=analysis["risk_record"],
        scenario={
            "rainfall_reduction_percent": rainfall_reduction_percent,
            "original_risk": scenario_result.get("original_risk", {}),
            "simulated_risk": scenario_result.get("simulated_risk", {}),
            "simulated_weather": scenario_result.get("evidence", {}).get("simulated_weather", {}),
        },
    )

    scenario_risk = {
        "risk_level": scenario_result.get("simulated_risk", {}).get("risk_level", "unknown"),
        "confidence": scenario_result.get("simulated_risk", {}).get("confidence", 0.0),
        "score": scenario_result.get("simulated_risk", {}).get("score", 0.0),
        "score_components": scenario_result.get("simulated_risk", {}).get("score_components", {}),
        "top_drivers": scenario_result.get("simulated_risk", {}).get("top_drivers", []),
        "model_prediction": scenario_result.get("simulated_risk", {}).get("model_prediction"),
    }
    brief = generate_brief(region["name"], scenario_risk, scenario_packet, audience=audience)
    approved_brief = qa_check_response(brief, scenario_packet)

    return {
        "analysis": analysis,
        "scenario_result": scenario_result,
        "brief": approved_brief,
        "scenario_packet": scenario_packet,
    }
