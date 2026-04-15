import json
from pathlib import Path
from typing import Any, Dict, List

from backend.app.services.training_service import load_hfid_latest_labels

HFID_GEOMETRY_PATH = Path(__file__).resolve().parents[3] / "data" / "raw" / "simplified_hfid_geom.gpkg"


def _normalize_geometry_columns(columns: List[str]) -> Dict[str, str]:
    lowered = {column.lower(): column for column in columns}
    resolved: Dict[str, str] = {}

    for target, candidates in {
        "country": ["admin0", "adm0_name", "country", "name_0", "shapeName0"],
        "admin1": ["admin1", "adm1_name", "name_1", "shapeName1"],
        "admin2": ["admin2", "adm2_name", "name_2", "shapeName2"],
    }.items():
        for candidate in candidates:
            if candidate.lower() in lowered:
                resolved[target] = lowered[candidate.lower()]
                break

    return resolved


def load_hfid_overlay_geojson(limit: int = 300) -> Dict[str, Any]:
    if not HFID_GEOMETRY_PATH.exists():
        return {"type": "FeatureCollection", "features": []}

    try:
        import geopandas as gpd
    except Exception:
        return {"type": "FeatureCollection", "features": []}

    labels = load_hfid_latest_labels()
    if not labels:
        return {"type": "FeatureCollection", "features": []}

    label_lookup = {}
    admin1_lookup = {}
    for row in labels:
        full_key = (
            str(row.get("country", "")).strip().lower(),
            str(row.get("admin1", "")).strip().lower(),
            str(row.get("admin2", "")).strip().lower(),
        )
        admin1_key = full_key[:2]
        label_lookup[full_key] = row
        admin1_lookup.setdefault(admin1_key, row)

    try:
        gdf = gpd.read_file(HFID_GEOMETRY_PATH)
    except Exception:
        return {"type": "FeatureCollection", "features": []}

    column_map = _normalize_geometry_columns(list(gdf.columns))
    if "country" not in column_map or "admin1" not in column_map:
        return {"type": "FeatureCollection", "features": []}

    if gdf.crs is not None and str(gdf.crs).lower() != "epsg:4326":
        gdf = gdf.to_crs(epsg=4326)

    matched_rows = []
    for _, record in gdf.iterrows():
        key = (
            str(record.get(column_map["country"], "")).strip().lower(),
            str(record.get(column_map["admin1"], "")).strip().lower(),
            str(record.get(column_map.get("admin2", ""), "")).strip().lower(),
        )
        label_info = label_lookup.get(key) or admin1_lookup.get(key[:2])
        if not label_info:
            continue

        centroid = record.geometry.centroid if record.geometry is not None else None
        matched_rows.append(
            {
                "country": label_info["country"],
                "admin1": label_info["admin1"],
                "admin2": label_info["admin2"],
                "year_month": label_info["year_month"],
                "risk_level": label_info["label"],
                "phase": label_info["phase"],
                "latitude": float(centroid.y) if centroid is not None else None,
                "longitude": float(centroid.x) if centroid is not None else None,
                "geometry": record.geometry,
            }
        )

    if not matched_rows:
        return {"type": "FeatureCollection", "features": []}

    overlay_gdf = gpd.GeoDataFrame(matched_rows, geometry="geometry", crs="EPSG:4326").head(limit)
    return json.loads(overlay_gdf.to_json(drop_id=True))
