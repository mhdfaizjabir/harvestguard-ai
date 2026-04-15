from typing import Any, Dict, Optional

from backend.app.schemas.region import (
    EvidencePacket,
    GeospatialContext,
    ModelPrediction,
    RegionCoordinates,
    RegionDescriptor,
    RiskRecord,
    ScoreComponents,
    WeatherObservation,
)
from backend.app.services.training_service import load_persisted_model_bundle


def build_evidence_packet(
    region: Dict[str, Any],
    weather: Dict[str, Any],
    geospatial: Dict[str, Any],
    risk_record: Dict[str, Any],
    explainability: Optional[Dict[str, Any]] = None,
    scenario: Optional[Dict[str, object]] = None,
) -> Dict[str, Any]:
    model_bundle = load_persisted_model_bundle()
    label_source = str(model_bundle["metadata"].get("label_source", "unknown"))
    is_synthetic_training = bool(risk_record.get("model_prediction", {}).get("synthetic_training", False))
    model_source_label = "synthetic_ml_baseline" if is_synthetic_training else label_source
    quality_flags = [
        "live_external_api_data",
        "derived_geospatial_proxy_features",
        "synthetic_model_training_data" if is_synthetic_training else "hfid_label_backed_training_data",
    ]
    packet = EvidencePacket(
        region=RegionDescriptor(
            id=region.get("id", "unknown"),
            name=region.get("name", "Unknown region"),
            country=region.get("country", "Unknown"),
            coordinates=RegionCoordinates(
                latitude=float(region.get("latitude", 0.0)),
                longitude=float(region.get("longitude", 0.0)),
            ),
        ),
        weather=WeatherObservation(
            avg_temperature_c=(
                float(weather.get("avg_temperature_c"))
                if weather.get("avg_temperature_c") is not None
                else None
            ),
            avg_precipitation_mm=(
                float(weather.get("avg_precipitation_mm"))
                if weather.get("avg_precipitation_mm") is not None
                else None
            ),
            precip_trend_last_30d=(
                float(weather.get("precip_trend_last_30d"))
                if weather.get("precip_trend_last_30d") is not None
                else None
            ),
            data_points=int(weather.get("data_points", 0)),
            temperature_history=weather.get("temperature_history"),
            precipitation_history=weather.get("precipitation_history"),
        ),
        geospatial_context=GeospatialContext(
            dominant_crop=str(geospatial.get("dominant_crop", "mixed staples")),
            vegetation_anomaly=(
                float(geospatial.get("vegetation_anomaly"))
                if geospatial.get("vegetation_anomaly") is not None
                else None
            ),
            soil_moisture_percentile=(
                float(geospatial.get("soil_moisture_percentile"))
                if geospatial.get("soil_moisture_percentile") is not None
                else None
            ),
            drought_index=(
                float(geospatial.get("drought_index"))
                if geospatial.get("drought_index") is not None
                else None
            ),
            crop_sensitivity=(
                float(geospatial.get("crop_sensitivity"))
                if geospatial.get("crop_sensitivity") is not None
                else None
            ),
            seasonal_phase=str(geospatial.get("seasonal_phase", "growing")),
            boundary_quality=str(geospatial.get("boundary_quality", "point_lookup")),
            source=str(geospatial.get("source", "api_lookup")),
            soil_moisture_history=geospatial.get("soil_moisture_history"),
            vegetation_history=geospatial.get("vegetation_history"),
        ),
        risk_record=RiskRecord(
            risk_level=risk_record.get("risk_level", "unknown"),
            confidence=float(risk_record.get("confidence", 0.0)),
            score=float(risk_record.get("score", 0.0)),
            score_components=ScoreComponents(**risk_record.get("score_components", {})),
            top_drivers=list(risk_record.get("top_drivers", [])),
            model_prediction=(
                ModelPrediction(
                    model_name=str(risk_record.get("model_prediction", {}).get("model_name", "unknown")),
                    risk_probability=float(risk_record.get("model_prediction", {}).get("risk_probability", 0.0)),
                    risk_label=risk_record.get("model_prediction", {}).get("risk_label", "unknown"),
                    explanation_method=str(risk_record.get("model_prediction", {}).get("explanation_method", "none")),
                    feature_contributions=dict(risk_record.get("model_prediction", {}).get("feature_contributions", {})),
                    feature_importances=dict(risk_record.get("model_prediction", {}).get("feature_importances", {})),
                    class_probabilities=dict(risk_record.get("model_prediction", {}).get("class_probabilities", {})),
                    top_explanations=list(risk_record.get("model_prediction", {}).get("top_explanations", [])),
                    synthetic_training=bool(risk_record.get("model_prediction", {}).get("synthetic_training", False)),
                )
                if risk_record.get("model_prediction")
                else None
            ),
        ),
        explainability=explainability,
        evidence_sources=[
            str(weather.get("source", "weather_api")),
            str(geospatial.get("source", "geospatial_api")),
            "composite_risk_engine",
            model_source_label,
        ],
        quality_flags=quality_flags,
        scenario=scenario,
    )

    return packet.dict()
