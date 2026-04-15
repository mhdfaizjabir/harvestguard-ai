<img width="1325" height="819" alt="Screenshot 2026-04-15 201535" src="https://github.com/user-attachments/assets/6f3492a8-493a-42bb-892a-70bc2e8aa74c" /># HarvestGuard AI <img width="1536" height="1024" alt="ChatGPT Image Apr 15, 2026, 07_58_52 PM" src="https://github.com/user-attachments/assets/54e22dac-6390-46cb-9c2c-d3b9d06c2fad" />

HarvestGuard AI is a regional crop-stress and food-security decision-support prototype built with a FastAPI backend and a Next.js frontend. The project is structured around live API-driven environmental data, a hybrid scoring pipeline, explainable ML outputs, and a LangGraph orchestration layer that uses OpenAI only as the LLM provider.

![Uploading Screenshot 2026-04-15 201325.png…]()

<img width="1574" height="873" alt="Screenshot 2026-04-15 201346" src="https://github.com/user-attachments/assets/8d3a127d-f193-4b2c-82e5-882194cdf557" />

<img width="1582" height="828" alt="Screenshot 2026-04-15 201405" src="https://github.com/user-attachments/assets/d08e9bee-6008-4133-ad9e-f5a8c5745ecd" />

<img width="1565" height="748" alt="Screenshot 2026-04-15 201419" src="https://github.com/user-attachments/assets/aae824ac-fca6-4b33-9b8c-1d55ac8dd267" />

<img width="1268" height="610" alt="Screenshot 2026-04-15 201504" src="https://github.com/user-attachments/assets/76e2066e-57ad-4974-8443-c992325655dc" />

<img width="1267" height="724" alt="Screenshot 2026-04-15 201516" src="https://github.com/user-attachments/assets/6f91d8c2-d562-4744-98ee-baf67c25754b" />

<img width="1325" height="819" alt="Screenshot 2026-04-15 201535" src="https://github.com/user-attachments/assets/4f097970-5b2a-4f4c-93a7-0cdfe68fd2ae" />


## What is implemented

- FastAPI backend with point-based analysis endpoints
- Next.js frontend with search-led location analysis and dynamic location search
- Live NASA POWER weather ingestion for recent temperature and precipitation signals
- Live Open-Meteo archive ingestion for soil moisture and evapotranspiration-derived context
- Live Nominatim geocoding and reverse geocoding for location discovery
- Hybrid risk pipeline combining rule-based scoring and a synthetic ML baseline
- **Short-term risk forecasting (7/14/30-day horizons) with trend-based projections**
- **Participatory ground truth feedback system for continuous model improvement**
- Persisted model artifacts and training metadata under `data/processed/artifacts`
- Structured evidence packets and typed API responses
- LangGraph workflow scaffolding for analysis -> planning -> QA
- SQLite-backed workflow event history
- OpenAI-backed brief generation through LangChain/OpenAI integration

## Architecture

### Data and feature layer

- `backend/app/services/ingestion_service.py`
- `backend/app/services/feature_service.py`
- `backend/app/services/modeling_service.py`
- `backend/app/services/risk_service.py`
- `backend/app/services/evidence_service.py`

### Orchestration layer

- `backend/app/services/agent_service.py`
- `backend/app/agents/response_agent.py`
- `backend/app/agents/orchestrator_agent.py`

### Product layer

- `backend/app/api/regions.py`
- `frontend/app/page.tsx`

## Run locally

### Backend

```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Optional frontend env:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

**Frontend Features:**
- Interactive global location search
- Real-time risk analysis display with confidence scores
- Multi-horizon risk forecasting (7/14/30 days)
- Forecast confidence bands and reasoning
- Scenario simulation (rainfall reduction impact)
- Audience-specific intervention briefs (NGO, donor, school feeding, field ops)
- Downloadable plain-text risk report
- Participatory feedback form for ground truth submissions
- Feedback loop dashboard with model-vs-observation match summary
- Workflow execution tracing
- Explainability and model-importance charts that focus on active signals
- Time-trend charts for temperature, rainfall, soil moisture, and vegetation proxy

## Main API endpoints

- `GET /regions`
- `GET /regions/locations/search?query=<text>`
- `GET /regions/locations/reverse?latitude=<lat>&longitude=<lng>`
- `GET /regions/geo/point/risk?latitude=<lat>&longitude=<lng>`
- `GET /regions/geo/point/analysis?latitude=<lat>&longitude=<lng>`
- `GET /regions/geo/point/forecast?latitude=<lat>&longitude=<lng>`
- `POST /regions/geo/point/brief?latitude=<lat>&longitude=<lng>`
- `POST /regions/geo/point/scenario?latitude=<lat>&longitude=<lng>&rainfall_reduction=20`
- `GET /regions/geo/point/scenario?latitude=<lat>&longitude=<lng>&rainfall_reduction=20`
- `POST /regions/geo/point/workflow?latitude=<lat>&longitude=<lng>`
- `GET /regions/workflow/history?session_id=<id>`
- `POST /regions/geo/point/feedback` (ground truth submission)
- `GET /regions/model/metadata`
- `POST /regions/model/train`

## Forecast API Response Structure

The `/regions/geo/point/forecast` endpoint returns a `RegionAnalysisResponse` with an extended `computed_risk` field containing:

```json
{
  "region_id": "point-13.0827-80.2707",
  "name": "Chennai, India",
  "country": "India",
  "evidence": {...},
  "computed_risk": {
    "risk_level": "high",
    "confidence": 0.78,
    "score": 0.758,
    "score_components": {...},
    "top_drivers": [...],
    "model_prediction": {...},
    "forecast": [
      {
        "horizon_days": 7,
        "risk_level": "high",
        "confidence": 0.78,
        "score": 0.758,
        "score_components": {...},
        "top_drivers": [...],
        "model_prediction": {...}
      },
      {
        "horizon_days": 14,
        "risk_level": "high",
        "confidence": 0.78,
        "score": 0.758,
        "score_components": {...},
        "top_drivers": [...],
        "model_prediction": {...}
      },
      {
        "horizon_days": 30,
        "risk_level": "high",
        "confidence": 0.78,
        "score": 0.758,
        "score_components": {...},
        "top_drivers": [...],
        "model_prediction": {...}
      }
    ]
  }
}
```

The forecast uses trend-based projections of precipitation and temperature to estimate risk evolution over the next 7, 14, and 30 days.

## Ground Truth Feedback API

The `/regions/geo/point/feedback` endpoint accepts participatory ground truth observations from farmers, extension workers, and researchers to improve model accuracy over time.

**Request Body:**
```json
{
  "latitude": 13.0827,
  "longitude": 80.2707,
  "observed_crop_stress": "high",
  "confidence": 0.8,
  "observation_date": "2026-04-02",
  "notes": "Visible wilting in rice fields",
  "photo_url": "https://example.com/photo.jpg",
  "observer_type": "farmer"
}
```

**Response:**
```json
{
  "feedback_id": "feedback-abc123...",
  "region_id": "point-13.0827-80.2707",
  "submitted_at": "2026-04-02T10:30:00Z",
  "status": "accepted",
  "message": "Ground truth feedback accepted and queued for model improvement"
}
```

Feedback submissions are stored in SQLite and can be used for continuous model retraining to improve prediction accuracy in high-engagement regions.

- The app is now point-driven and API-driven rather than relying on seeded demo regions in code.
- OpenAI is used as the LLM provider only. Orchestration is built around LangGraph/LangChain.
- The ML layer now persists artifacts and can consume `data/raw/training_labels.csv` when you provide real labeled rows, but the default fallback dataset is still synthetic until that file exists.

