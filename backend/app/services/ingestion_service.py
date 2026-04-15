import datetime
import os
import time
from typing import Any, Dict, List, Optional

import httpx

# ---------------------------------------------------------------------------
# Simple in-process TTL cache to avoid hammering live APIs for the same point
# ---------------------------------------------------------------------------
_CACHE_TTL = 1800  # 30 minutes

_ENV_CACHE: Dict[str, Any] = {}
_GEO_CACHE: Dict[str, Any] = {}


def _location_key(lat: float, lon: float) -> str:
    return f"{round(lat, 3)},{round(lon, 3)}"


def _cache_get(store: Dict, key: str) -> Any:
    entry = store.get(key)
    if entry and time.time() - entry["ts"] < _CACHE_TTL:
        return entry["data"]
    return None


def _cache_set(store: Dict, key: str, data: Any) -> None:
    store[key] = {"data": data, "ts": time.time()}


NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
SENTINEL_HUB_TOKEN_URL = "https://services.sentinel-hub.com/oauth/token"
SENTINEL_HUB_STATS_URL = "https://services.sentinel-hub.com/api/v1/statistics"

DEFAULT_HEADERS = {
    "User-Agent": "HarvestGuardAI/0.1 (research prototype)",
    "Accept-Language": "en",
}


def _safe_average(values: List[float]) -> Optional[float]:
    cleaned = [value for value in values if value is not None]
    if not cleaned:
        return None
    return sum(cleaned) / len(cleaned)


def _build_series(dates: List[str], values: List[float], key: str) -> List[Dict[str, Any]]:
    series: List[Dict[str, Any]] = []
    for date, value in zip(dates, values):
        if isinstance(value, (int, float)):
            series.append({"date": date, key: round(float(value), 4)})
    return series


def fetch_nasa_power_point(
    latitude: float,
    longitude: float,
    start: str,
    end: str,
    parameters: str = "T2M,PRECTOT",
) -> Optional[Dict[str, Any]]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start": start,
        "end": end,
        "parameters": parameters,
        "community": "ag",
        "format": "JSON",
        "header": "true",
    }
    try:
        with httpx.Client(timeout=30.0, headers=DEFAULT_HEADERS) as client:
            response = client.get(NASA_POWER_URL, params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return None

    return payload.get("properties", {}).get("parameter")


def get_recent_nasa_power_features(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
    today = datetime.datetime.now(datetime.UTC).date()
    end_date = today.strftime("%Y%m%d")
    start_date = (today - datetime.timedelta(days=30)).strftime("%Y%m%d")

    params = fetch_nasa_power_point(latitude, longitude, start_date, end_date)
    if not params:
        return None

    temperature_values = [value for value in params.get("T2M", {}).values() if isinstance(value, (int, float))]
    precipitation_values = [value for value in params.get("PRECTOT", {}).values() if isinstance(value, (int, float))]

    if not temperature_values or not precipitation_values:
        return None

    avg_temperature = _safe_average(temperature_values)
    avg_precipitation = _safe_average(precipitation_values)
    trend_precipitation = (
        precipitation_values[-7:]
        if len(precipitation_values) >= 7
        else precipitation_values
    )
    early_precipitation = (
        precipitation_values[:7]
        if len(precipitation_values) >= 7
        else precipitation_values
    )

    recent_avg = _safe_average(trend_precipitation) or 0.0
    early_avg = _safe_average(early_precipitation) or 0.0

    return {
        "latitude": latitude,
        "longitude": longitude,
        "avg_temperature_c": round(avg_temperature or 0.0, 2),
        "avg_precipitation_mm": round(avg_precipitation or 0.0, 2),
        "precip_trend_last_30d": round(recent_avg - early_avg, 2),
        "data_points": len(temperature_values),
        "source": "nasa_power",
    }


def get_recent_open_meteo_weather(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
    today = datetime.datetime.now(datetime.UTC).date()
    start_date = (today - datetime.timedelta(days=30)).isoformat()
    end_date = today.isoformat()

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_mean,precipitation_sum",
        "timezone": "UTC",
    }

    try:
        with httpx.Client(timeout=30.0, headers=DEFAULT_HEADERS) as client:
            response = client.get(OPEN_METEO_ARCHIVE_URL, params=params)
            response.raise_for_status()
            payload = response.json().get("daily", {})
    except Exception:
        return None

    dates = payload.get("time", [])
    temperature_values = [value for value in payload.get("temperature_2m_mean", []) if isinstance(value, (int, float))]
    precipitation_values = [value for value in payload.get("precipitation_sum", []) if isinstance(value, (int, float))]
    if not temperature_values or not precipitation_values:
        return None

    avg_temperature = _safe_average(temperature_values)
    avg_precipitation = _safe_average(precipitation_values)
    recent_avg = _safe_average(precipitation_values[-7:]) or 0.0
    early_avg = _safe_average(precipitation_values[:7]) or 0.0

    return {
        "latitude": latitude,
        "longitude": longitude,
        "avg_temperature_c": round(avg_temperature or 0.0, 2),
        "avg_precipitation_mm": round(avg_precipitation or 0.0, 2),
        "precip_trend_last_30d": round(recent_avg - early_avg, 2),
        "data_points": len(temperature_values),
        "temperature_history": _build_series(dates, payload.get("temperature_2m_mean", []), "value"),
        "precipitation_history": _build_series(dates, payload.get("precipitation_sum", []), "value"),
        "source": "open_meteo_archive",
    }


def get_geospatial_context(latitude: float, longitude: float) -> Dict[str, Any]:
    today = datetime.datetime.now(datetime.UTC).date()
    start_date = (today - datetime.timedelta(days=30)).isoformat()
    end_date = today.isoformat()

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join(
            [
                "temperature_2m_mean",
                "precipitation_sum",
                "soil_moisture_0_to_7cm_mean",
                "et0_fao_evapotranspiration",
            ]
        ),
        "timezone": "UTC",
    }

    try:
        with httpx.Client(timeout=30.0, headers=DEFAULT_HEADERS) as client:
            response = client.get(OPEN_METEO_ARCHIVE_URL, params=params)
            response.raise_for_status()
            payload = response.json().get("daily", {})
    except Exception:
        payload = {}

    dates = payload.get("time", [])
    temperatures = [value for value in payload.get("temperature_2m_mean", []) if isinstance(value, (int, float))]
    precipitation = [value for value in payload.get("precipitation_sum", []) if isinstance(value, (int, float))]
    soil_moisture = [value for value in payload.get("soil_moisture_0_to_7cm_mean", []) if isinstance(value, (int, float))]
    evapotranspiration = [value for value in payload.get("et0_fao_evapotranspiration", []) if isinstance(value, (int, float))]

    avg_soil_moisture = _safe_average(soil_moisture)
    avg_et0 = _safe_average(evapotranspiration)
    avg_precip = _safe_average(precipitation)
    avg_temp = _safe_average(temperatures)

    ndvi_mean = _fetch_satellite_ndvi(latitude, longitude, start_date, end_date)
    vegetation_proxy = ndvi_mean
    if avg_precip is not None and avg_et0 is not None and avg_et0 > 0:
        vegetation_proxy = ndvi_mean if ndvi_mean is not None else max(-1.0, min(1.0, (avg_precip - avg_et0) / max(avg_et0, 1.0)))

    drought_index = None
    if avg_precip is not None and avg_et0 is not None and avg_et0 > 0:
        drought_index = max(0.0, min(1.0, 1 - (avg_precip / max(avg_et0, 1.0))))

    soil_percentile = None
    if avg_soil_moisture is not None:
        soil_percentile = max(0.0, min(1.0, avg_soil_moisture))

    crop_sensitivity = None
    if avg_temp is not None:
        crop_sensitivity = max(0.0, min(1.0, (avg_temp - 10) / 25))

    vegetation_history: List[Dict[str, Any]] = []
    if dates:
        for date, precip_value, et0_value in zip(dates, payload.get("precipitation_sum", []), payload.get("et0_fao_evapotranspiration", [])):
            if isinstance(precip_value, (int, float)) and isinstance(et0_value, (int, float)):
                daily_proxy = max(-1.0, min(1.0, (float(precip_value) - float(et0_value)) / max(float(et0_value), 1.0)))
                vegetation_history.append({"date": date, "value": round(daily_proxy, 4)})

    return {
        "dominant_crop": "unknown",
        "vegetation_anomaly": vegetation_proxy,
        "soil_moisture_percentile": soil_percentile,
        "drought_index": drought_index,
        "crop_sensitivity": crop_sensitivity,
        "seasonal_phase": "inferred_from_recent_climate",
        "boundary_quality": "point_based_lookup",
        "soil_moisture_history": _build_series(dates, payload.get("soil_moisture_0_to_7cm_mean", []), "value"),
        "vegetation_history": vegetation_history,
        "source": "sentinel_hub_statistics" if ndvi_mean is not None else "open_meteo_archive",
    }


def get_environment_bundle(latitude: float, longitude: float) -> Dict[str, Any]:
    key = _location_key(latitude, longitude)
    cached = _cache_get(_ENV_CACHE, key)
    if cached is not None:
        return cached

    nasa_weather = get_recent_nasa_power_features(latitude, longitude)
    open_meteo_weather = get_recent_open_meteo_weather(latitude, longitude)
    weather = nasa_weather or open_meteo_weather
    if weather and open_meteo_weather:
        weather["temperature_history"] = open_meteo_weather.get("temperature_history", [])
        weather["precipitation_history"] = open_meteo_weather.get("precipitation_history", [])
    geospatial = get_geospatial_context(latitude, longitude)

    result = {
        "latitude": latitude,
        "longitude": longitude,
        "weather": weather or {
            "latitude": latitude,
            "longitude": longitude,
            "avg_temperature_c": None,
            "avg_precipitation_mm": None,
            "precip_trend_last_30d": None,
            "data_points": 0,
            "temperature_history": [],
            "precipitation_history": [],
            "source": "unavailable",
        },
        "geospatial": geospatial,
    }

    _cache_set(_ENV_CACHE, key, result)
    return result


def _fetch_satellite_ndvi(latitude: float, longitude: float, start_date: str, end_date: str) -> Optional[float]:
    client_id = os.getenv("SENTINEL_HUB_CLIENT_ID")
    client_secret = os.getenv("SENTINEL_HUB_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None

    try:
        with httpx.Client(timeout=30.0, headers=DEFAULT_HEADERS) as client:
            token_response = client.post(
                SENTINEL_HUB_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            token_response.raise_for_status()
            access_token = token_response.json()["access_token"]

            delta = 0.05
            payload = {
                "input": {
                    "bounds": {
                        "bbox": [longitude - delta, latitude - delta, longitude + delta, latitude + delta],
                        "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
                    },
                    "data": [
                        {
                            "type": "sentinel-2-l2a",
                            "dataFilter": {
                                "timeRange": {
                                    "from": f"{start_date}T00:00:00Z",
                                    "to": f"{end_date}T23:59:59Z",
                                }
                            },
                        }
                    ],
                },
                "aggregation": {
                    "timeRange": {
                        "from": f"{start_date}T00:00:00Z",
                        "to": f"{end_date}T23:59:59Z",
                    },
                    "aggregationInterval": {"of": "P30D"},
                    "resx": 1000,
                    "resy": 1000,
                    "evalscript": """
                        //VERSION=3
                        function setup() {
                          return {
                            input: ["B04", "B08", "dataMask"],
                            output: [
                              { id: "ndvi", bands: 1 },
                              { id: "dataMask", bands: 1 }
                            ]
                          };
                        }
                        function evaluatePixel(sample) {
                          let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04 + 0.0001);
                          return {
                            ndvi: [ndvi],
                            dataMask: [sample.dataMask]
                          };
                        }
                    """,
                },
                "calculations": {
                    "ndvi": {
                        "statistics": {
                            "default": {
                                "percentiles": {
                                    "k": [50]
                                }
                            }
                        }
                    }
                },
            }

            stats_response = client.post(
                SENTINEL_HUB_STATS_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                json=payload,
            )
            stats_response.raise_for_status()
            data = stats_response.json().get("data", [])
            if not data:
                return None
            stats = data[0].get("outputs", {}).get("ndvi", {}).get("bands", {}).get("B0", {}).get("stats", {})
            mean_value = stats.get("mean")
            return round(float(mean_value), 4) if mean_value is not None else None
    except Exception:
        return None


def search_locations(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    params = {
        "q": query,
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": limit,
    }
    try:
        with httpx.Client(timeout=30.0, headers=DEFAULT_HEADERS) as client:
            response = client.get(NOMINATIM_SEARCH_URL, params=params)
            response.raise_for_status()
            results = response.json()
    except Exception:
        return []

    normalized_results = []
    for item in results:
        normalized_results.append(
            {
                "id": str(item.get("place_id")),
                "name": item.get("display_name", "Unknown location"),
                "latitude": float(item.get("lat")),
                "longitude": float(item.get("lon")),
                "country": item.get("address", {}).get("country", "Unknown"),
            }
        )
    return normalized_results


def reverse_geocode(latitude: float, longitude: float) -> Dict[str, Any]:
    key = _location_key(latitude, longitude)
    cached = _cache_get(_GEO_CACHE, key)
    if cached is not None:
        return cached

    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "jsonv2",
        "zoom": 10,
        "addressdetails": 1,
    }
    try:
        with httpx.Client(timeout=30.0, headers=DEFAULT_HEADERS) as client:
            response = client.get(NOMINATIM_REVERSE_URL, params=params)
            response.raise_for_status()
            item = response.json()
    except Exception:
        return {
            "name": f"{latitude:.3f}, {longitude:.3f}",
            "country": "Unknown",
            "latitude": latitude,
            "longitude": longitude,
        }

    result = {
        "name": item.get("display_name", f"{latitude:.3f}, {longitude:.3f}"),
        "country": item.get("address", {}).get("country", "Unknown"),
        "latitude": latitude,
        "longitude": longitude,
    }
    _cache_set(_GEO_CACHE, key, result)
    return result
