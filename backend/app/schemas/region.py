from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class StrictBaseModel(BaseModel):
    class Config:
        extra = "forbid"


class RegionCoordinates(StrictBaseModel):
    latitude: float
    longitude: float


class RegionDescriptor(StrictBaseModel):
    id: str
    name: str
    country: str
    coordinates: RegionCoordinates


class WeatherObservation(StrictBaseModel):
    avg_temperature_c: Optional[float]
    avg_precipitation_mm: Optional[float]
    precip_trend_last_30d: Optional[float]
    data_points: int
    temperature_history: Optional[List[Dict[str, float | str]]] = None
    precipitation_history: Optional[List[Dict[str, float | str]]] = None


class GeospatialContext(StrictBaseModel):
    dominant_crop: str
    vegetation_anomaly: Optional[float]
    soil_moisture_percentile: Optional[float]
    drought_index: Optional[float]
    crop_sensitivity: Optional[float]
    seasonal_phase: str
    boundary_quality: str
    source: str
    soil_moisture_history: Optional[List[Dict[str, float | str]]] = None
    vegetation_history: Optional[List[Dict[str, float | str]]] = None


class ScoreComponents(StrictBaseModel):
    heat: float = 0.0
    moisture: float = 0.0
    trend: float = 0.0
    vegetation: float = 0.0
    soil_moisture: float = 0.0
    drought: float = 0.0


class ModelPrediction(StrictBaseModel):
    model_name: str
    risk_probability: float
    risk_label: Literal["low", "medium", "high", "unknown"]
    explanation_method: str
    feature_contributions: Dict[str, float]
    feature_importances: Dict[str, float]
    class_probabilities: Optional[Dict[str, float]] = None
    top_explanations: Optional[List[str]] = None
    synthetic_training: Optional[bool] = None
    artifact_path: Optional[str] = None


class RiskForecast(StrictBaseModel):
    horizon_days: int
    risk_level: Literal["low", "medium", "high", "unknown"]
    confidence: float
    confidence_band: Literal["low", "medium", "high"]
    score: float
    score_components: ScoreComponents
    top_drivers: List[str]
    reasoning: str
    model_prediction: Optional[ModelPrediction] = None


class RiskRecord(StrictBaseModel):
    risk_level: Literal["low", "medium", "high", "unknown"]
    confidence: float
    score: float
    score_components: ScoreComponents
    top_drivers: List[str]
    model_prediction: Optional[ModelPrediction] = None
    forecast: Optional[List[RiskForecast]] = None


class ExplainabilityRecord(StrictBaseModel):
    method: str
    feature_values: Dict[str, float]
    shap_values: Dict[str, float]
    top_positive_drivers: List[str]
    top_negative_drivers: List[str]
    summary_plot_data: Dict[str, float]


class EvidencePacket(StrictBaseModel):
    region: RegionDescriptor
    weather: WeatherObservation
    geospatial_context: GeospatialContext
    risk_record: RiskRecord
    explainability: Optional[ExplainabilityRecord] = None
    evidence_sources: List[str]
    quality_flags: List[str]
    scenario: Optional[Dict[str, object]] = None


class RegionRisk(StrictBaseModel):
    id: str
    name: str
    risk_level: Literal["low", "medium", "high", "unknown"]
    confidence: float
    top_drivers: List[str]


class RegionBrief(StrictBaseModel):
    region_id: str
    summary: str
    suggested_action: str
    caution_note: str


class RegionAnalysisResponse(StrictBaseModel):
    region_id: str
    name: str
    country: str
    evidence: EvidencePacket
    computed_risk: RiskRecord


class ScenarioResponse(StrictBaseModel):
    region_id: str
    scenario: str
    evidence: EvidencePacket
    brief: RegionBrief
    original_risk: RiskRecord
    simulated_risk: RiskRecord


class AgentWorkflowResponse(StrictBaseModel):
    region_id: str
    session_id: str = Field(..., description="Conversation/session identifier for the agent workflow")
    mode: Literal["langgraph", "fallback"]
    brief: RegionBrief
    handoff_path: List[str]
    trace_notes: List[str]


class GroundTruthFeedback(StrictBaseModel):
    latitude: float
    longitude: float
    observed_crop_stress: Literal["low", "medium", "high", "unknown"]
    confidence: float = Field(..., ge=0.0, le=1.0, description="Observer confidence in assessment")
    observation_date: str = Field(..., description="ISO date string (YYYY-MM-DD)")
    notes: Optional[str] = None
    photo_url: Optional[str] = None
    observer_type: Literal["farmer", "extension_worker", "researcher", "other"]


class FeedbackSubmissionResponse(StrictBaseModel):
    feedback_id: str
    region_id: str
    submitted_at: str
    status: Literal["accepted", "queued_for_retraining"]
    message: str
