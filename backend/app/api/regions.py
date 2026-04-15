from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Query

from backend.app.agents.orchestrator_agent import run_agent_workflow
from backend.app.schemas import (
    AgentWorkflowResponse,
    FeedbackSubmissionResponse,
    GroundTruthFeedback,
    RegionAnalysisResponse,
    RegionBrief,
    RegionRisk,
    ScenarioResponse,
)
from backend.app.services.agent_service import generate_region_brief, generate_scenario_brief, run_region_analysis
from backend.app.services.ingestion_service import reverse_geocode, search_locations
from backend.app.services.overlay_service import load_hfid_overlay_geojson
from backend.app.services.training_service import load_persisted_model_bundle, train_and_persist_model
from backend.app.services.workflow_store import load_workflow_history, summarize_feedback_events

router = APIRouter()


def _point_region(latitude: float, longitude: float, name: Optional[str] = None, country: Optional[str] = None) -> dict:
    location = reverse_geocode(latitude, longitude)
    return {
        "id": f"point-{latitude:.4f}-{longitude:.4f}",
        "name": name or location["name"],
        "latitude": latitude,
        "longitude": longitude,
        "country": country or location["country"],
    }


@router.get("", response_model=List[RegionRisk])
def get_regions():
    return []


@router.get("/model/metadata")
def get_model_metadata():
    bundle = load_persisted_model_bundle()
    return {
        "metadata": bundle["metadata"],
        "feature_importances": bundle["feature_importances"],
        "dataset_rows": bundle["dataset_rows"],
    }


@router.post("/model/train")
def retrain_model():
    metadata = train_and_persist_model()
    return {
        "status": "trained",
        "metadata": metadata,
    }


@router.get("/overlays/hfid")
def get_hfid_overlays(limit: int = Query(250, ge=1, le=600)):
    return load_hfid_overlay_geojson(limit=limit)


@router.get("/locations/search")
def lookup_locations(query: str = Query(..., min_length=2), limit: int = Query(5, ge=1, le=10)):
    return search_locations(query=query, limit=limit)


@router.get("/locations/reverse")
def reverse_lookup(latitude: float, longitude: float):
    return reverse_geocode(latitude=latitude, longitude=longitude)


@router.get("/geo/point/risk", response_model=RegionRisk)
def get_point_risk(latitude: float, longitude: float):
    point_region = _point_region(latitude, longitude)
    analysis = run_region_analysis(point_region)
    risk = analysis["risk_record"]
    return {
        "id": point_region["id"],
        "name": point_region["name"],
        "risk_level": risk["risk_level"],
        "confidence": risk["confidence"],
        "top_drivers": risk["top_drivers"],
    }


@router.get("/geo/point/analysis", response_model=RegionAnalysisResponse)
def get_point_analysis(latitude: float, longitude: float):
    point_region = _point_region(latitude, longitude)
    analysis = run_region_analysis(point_region)
    return RegionAnalysisResponse(
        region_id=point_region["id"],
        name=point_region["name"],
        country=point_region["country"],
        evidence=analysis["evidence_packet"],
        computed_risk=analysis["risk_record"],
    )


@router.get("/geo/point/forecast", response_model=RegionAnalysisResponse)
def get_point_forecast(latitude: float, longitude: float):
    point_region = _point_region(latitude, longitude)
    analysis = run_region_analysis(point_region)

    return RegionAnalysisResponse(
        region_id=point_region["id"],
        name=point_region["name"],
        country=point_region["country"],
        evidence=analysis["evidence_packet"],
        computed_risk=analysis["risk_record"],
    )


@router.post("/geo/point/brief", response_model=RegionBrief)
def generate_point_brief(latitude: float, longitude: float, audience: str = Query("ngo")):
    point_region = _point_region(latitude, longitude)
    output = generate_region_brief(point_region, audience=audience)
    approved_brief = output["brief"]

    return {
        "region_id": point_region["id"],
        "summary": approved_brief["summary"],
        "suggested_action": approved_brief["suggested_action"],
        "caution_note": approved_brief["caution_note"],
    }


@router.post("/geo/point/scenario", response_model=RegionBrief)
def run_point_scenario(
    latitude: float,
    longitude: float,
    rainfall_reduction: float = Query(20.0, description="Rainfall reduction percentage"),
    audience: str = Query("ngo"),
):
    point_region = _point_region(latitude, longitude)
    scenario_output = generate_scenario_brief(point_region, rainfall_reduction, audience=audience)
    approved_brief = scenario_output["brief"]

    return {
        "region_id": point_region["id"],
        "summary": approved_brief["summary"],
        "suggested_action": approved_brief["suggested_action"],
        "caution_note": approved_brief["caution_note"],
    }


@router.get("/geo/point/scenario", response_model=ScenarioResponse)
def get_point_scenario_analysis(
    latitude: float,
    longitude: float,
    rainfall_reduction: float = Query(20.0, description="Rainfall reduction percentage"),
    audience: str = Query("ngo"),
):
    point_region = _point_region(latitude, longitude)
    scenario_output = generate_scenario_brief(point_region, rainfall_reduction, audience=audience)
    approved_brief = scenario_output["brief"]
    scenario_result = scenario_output["scenario_result"]

    return ScenarioResponse(
        region_id=point_region["id"],
        scenario=scenario_result["scenario"],
        evidence=scenario_output["scenario_packet"],
        brief={
            "region_id": point_region["id"],
            "summary": approved_brief["summary"],
            "suggested_action": approved_brief["suggested_action"],
            "caution_note": approved_brief["caution_note"],
        },
        original_risk=scenario_result["original_risk"],
        simulated_risk=scenario_result["simulated_risk"],
    )


@router.post("/geo/point/workflow", response_model=AgentWorkflowResponse)
def run_point_workflow(latitude: float, longitude: float, session_id: Optional[str] = None, audience: str = Query("ngo")):
    point_region = _point_region(latitude, longitude)
    workflow_output = run_agent_workflow(
        point_region,
        session_id=session_id or f"point-{uuid4().hex}",
        audience=audience,
    )
    return AgentWorkflowResponse(**workflow_output)


@router.get("/workflow/history")
def get_workflow_history(session_id: str):
    return {
        "session_id": session_id,
        "events": load_workflow_history(session_id),
    }


@router.post("/geo/point/feedback", response_model=FeedbackSubmissionResponse)
def submit_ground_truth_feedback(feedback: GroundTruthFeedback):
    from backend.app.services.workflow_store import save_feedback_event
    import uuid
    from datetime import datetime, timezone

    feedback_id = f"feedback-{uuid.uuid4().hex}"
    region_id = f"point-{feedback.latitude:.4f}-{feedback.longitude:.4f}"
    submitted_at = datetime.now(timezone.utc).isoformat()

    # Save feedback to workflow store
    save_feedback_event(
        feedback_id=feedback_id,
        region_id=region_id,
        feedback_data=feedback.dict(),
        submitted_at=submitted_at
    )

    return FeedbackSubmissionResponse(
        feedback_id=feedback_id,
        region_id=region_id,
        submitted_at=submitted_at,
        status="accepted",
        message="Ground truth feedback accepted and queued for model improvement"
    )


@router.get("/geo/point/feedback/summary")
def get_feedback_summary(latitude: float, longitude: float):
    point_region = _point_region(latitude, longitude)
    analysis = run_region_analysis(point_region)
    return summarize_feedback_events(
        region_id=point_region["id"],
        predicted_risk=analysis["risk_record"]["risk_level"],
    )
