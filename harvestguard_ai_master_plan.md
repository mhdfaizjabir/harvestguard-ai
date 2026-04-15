# HarvestGuard AI — Master Project Plan

## 1) Project summary

**Working title:** HarvestGuard AI  
**Tagline:** Multi-agent early warning for crop stress and food insecurity  
**Hackathon theme:** **UN SDG 2 — Zero Hunger**  

### One-line pitch
HarvestGuard AI is an end-to-end, agentic platform that combines satellite imagery, agro-climate signals, crop statistics, and LLM-powered decision support to forecast **where food insecurity risk may rise 1–3 months ahead** and suggest **practical interventions for NGOs, school-feeding programs, and local responders**.

### Why this is strong for Hyperbloom V2
This project is directly aligned with **SDG 2**, which the hackathon defines as ending hunger, achieving food security and improved nutrition, and promoting sustainable agriculture. It is far more differentiated than a chatbot or single-API wrapper because it includes:

- geospatial data ingestion
- time-series feature engineering
- multimodal evidence aggregation
- predictive modeling
- explainability
- agentic report generation
- actionable planning output

### The real problem
Food insecurity often becomes obvious **too late**. By the time prices spike, yields collapse, or malnutrition numbers rise, responders have already lost valuable time. NGOs and local programs need an **earlier signal** based on crop stress, rainfall anomalies, vegetation health, and historical crop patterns.

### What the system does
The platform continuously ingests environmental and agricultural data, scores the risk of crop stress and supply shortfalls at the region level, and then uses an LLM-based response agent to generate:

- regional risk briefs
- evidence-backed explanations
- confidence-aware intervention ideas
- priority ranking for field follow-up

---

## 2) What the hackathon actually wants

Hyperbloom V2 allows projects tied to these three themes:

1. **UN SDG 2 — Zero Hunger**
2. **UN SDG 4 — Quality Education**
3. **UN SDG 6 — Clean Water and Sanitation**

Healthcare is **not** one of the listed themes on the challenge page.

For this idea, you should position the project under **SDG 2** and emphasize these phrases in your pitch:

- food security
- improved nutrition
- sustainable agriculture
- early intervention
- aid prioritization
- climate-resilient planning

---

## 3) Core use cases

### Use case A — NGO regional planning
An NGO opens the dashboard and sees that three districts have rising crop stress risk. The system shows rainfall deficit, declining vegetation index, and weak historical yield patterns. The NGO can prioritize which district to inspect first.

### Use case B — School feeding program planning
A school-feeding coordinator sees a warning that local agricultural output may weaken in coming months. The system flags likely procurement pressure and recommends earlier sourcing or alternate suppliers.

### Use case C — Donor and grant brief generation
A donor asks for a one-page evidence summary. The system generates a concise brief explaining why a district is high-risk, what evidence supports the classification, and what intervention categories are most suitable.

### Use case D — Agricultural extension / field triage
A field officer views region-level risk, crop stress heatmaps, and explanation cards, then exports a short field checklist for on-ground verification.

### Use case E — What-if analysis
A program manager asks: *What if rainfall stays below normal for 4 more weeks?* The system simulates worsening risk and shows how priority districts change.

---

## 4) Product vision

### Product layers

#### Layer 1 — Data engine
Pulls and normalizes satellite, weather, and crop data.

#### Layer 2 — Prediction engine
Produces a risk score per region and time window.

#### Layer 3 — Evidence engine
Stores the top features and historical analogs that explain the score.

#### Layer 4 — Agent layer
Generates human-readable insights, intervention suggestions, and alert summaries.

#### Layer 5 — Product UI
Provides map-based risk exploration, scenario simulation, and exportable reports.

### North-star experience
A user chooses a country or district, sees a risk map for the next 1–3 months, opens one district, reads the supporting evidence, and gets a recommended action plan tailored to NGO operations.

---

## 5) Why AI is actually useful here

The LLM is **not** the main model and should **not** be used to “guess” the truth.

### ML / geospatial system is responsible for:
- feature extraction
- anomaly detection
- forecasting / classification
- ranking and prioritization
- confidence scoring

### LLM / agents are responsible for:
- structuring messy outputs into decision-ready summaries
- producing intervention briefs
- answering follow-up questions over model evidence
- generating stakeholder-specific reports
- comparing scenarios and articulating trade-offs

That means the product is **real AI + real data + real product logic**, not a wrapper.

---

## 6) Recommended project shape

### Best framing
**HarvestGuard AI: A Multi-Agent Early Warning Platform for Food Insecurity Risk**

### Better than “predict famine”
Avoid claiming you predict famine with perfect precision. That is too large and hard to justify. Instead, say:

> “HarvestGuard AI estimates rising agricultural stress and food security risk using environmental and crop signals, so responders can act earlier.”

This is stronger, safer, and more believable.

---

## 7) Scope for the hackathon

## Smart MVP
Build a system that predicts **regional crop stress / food insecurity risk** using:

- vegetation condition proxy
- rainfall anomaly
- temperature anomaly
- historical crop productivity data
- simple seasonal context

Then expose the result through:

- a map / regional dashboard
- district risk cards
- an evidence panel
- an LLM-generated intervention brief

### MVP output
For each district/region:
- risk score: low / medium / high
- confidence level
- top contributing signals
- likely crop stress drivers
- suggested intervention class

### Stretch output
- scenario simulator
- conversational analyst mode
- historical analog year matching
- automated weekly alert digest

---

## 8) Data sources

## Satellite / geospatial

### Option 1 — Google Earth Engine
**Best for prototype speed.** It already hosts a large public geospatial catalog and analysis stack.

Use it for:
- Sentinel-2 imagery
- MODIS vegetation products
- drought / land surface / climate layers available in catalog

### Option 2 — Copernicus / Sentinel via CDSE
Use if you want direct Sentinel source access.

Potential use:
- NDVI or vegetation condition extraction
- land cover / crop area proxies

## Weather / climate

### NASA POWER
Great for historical agroclimate variables and analysis-ready API access.

Possible features:
- rainfall totals
- temperature averages
- solar radiation
- humidity / climate-derived stress indicators

### Open-Meteo
Good for lightweight forecast and weather API prototyping when you want easy integration.

Possible features:
- short-term forecast extension
- weather preview for scenario mode

## Agriculture / crop statistics

### FAOSTAT
Use for:
- historical crop production
- crop yield trends
- country / region agricultural context

## Optional future sources
- World Bank indicators
- local agriculture ministry data
- FEWS NET style public food security context layers
- market price data

---

## 9) Data design

### Recommended unit of analysis
Do **not** start at individual farms.

For the hackathon, use:
- district
- province
- grid tile aggregated to district

This keeps the system manageable.

### Suggested target variable
For MVP, choose one of these:

#### Option A — Crop stress risk (recommended)
Label based on environmental thresholds or historical anomaly rules.

#### Option B — Yield drop risk
Predict whether yield may fall below historical baseline.

#### Option C — Composite food insecurity proxy
Build a custom risk score from environmental and agricultural indicators.

### Best recommendation
For hackathon speed, use **Option C**, a transparent composite score, then optionally train a classifier/regressor on top.

---

## 10) Feature engineering plan

### Environmental features
- NDVI / vegetation anomaly
- rolling vegetation decline
- rainfall anomaly vs normal
- temperature anomaly vs normal
- cumulative dry days
- seasonal phase

### Agricultural features
- historical yield mean
- yield volatility
- crop type or dominant crop proxy
- planting / harvest season encoding

### Spatial features
- neighboring-region stress average
- cluster-level drought intensity
- eco-zone / land-use category

### Temporal features
- lagged 1, 2, 4, and 8-week deltas
- month / season index
- pre-harvest vs post-harvest phase

### Derived features
- crop stress composite index
- rainfall deficit severity tier
- persistent anomaly duration
- vegetation recovery failure flag

---

## 11) Modeling strategy

### Recommended model stack

#### Baseline 1 — Rule-based composite score
This is your first working version.

Example:
- vegetation anomaly low + rainfall deficit high + high-temperature anomaly = elevated risk

#### Baseline 2 — Gradient boosting model
Use LightGBM or XGBoost on aggregated tabular features.

Why this is ideal:
- strong performance on tabular data
- fast to train
- interpretable enough with SHAP / feature importance
- realistic for hackathon timeline

#### Optional model 3 — Time-series forecasting layer
Use if you have time:
- Temporal Fusion Transformer
- LSTM / GRU
- Prophet for simple trends

### Best practical recommendation
For the hackathon:
1. build rule-based composite first
2. build LightGBM / XGBoost second
3. only add deep learning if the pipeline is already stable

This gives you the strongest balance of impressiveness and reliability.

---

## 12) Explainability strategy

This part will help you a lot in judging.

For each risk output, show:
- risk score
- confidence band
- top 3 feature contributors
- historical baseline comparison
- analogous past periods if available

### Explainability tools
- SHAP for tabular model
- feature importance bars
- textual evidence summary

### Example explanation
> Risk is high because rainfall is 31% below the seasonal baseline, vegetation has declined for three consecutive intervals, and the district historically shows high yield sensitivity during this season.

That makes the system feel serious and trustworthy.

---

## 13) Agent architecture

## Why use agents here
Agents make sense because the workflow has several specialized tasks that should not all be dumped into one prompt.

### Agent 1 — Ingestion Agent
Responsibilities:
- trigger data pulls
- validate source freshness
- normalize schemas
- store processed features

Inputs:
- region list
- date window

Outputs:
- clean geospatial and tabular feature bundle

### Agent 2 — Geospatial Analysis Agent
Responsibilities:
- compute vegetation trends
- aggregate satellite indicators by region
- flag imagery / data quality issues

Outputs:
- region-level geospatial features

### Agent 3 — Risk Modeling Agent
Responsibilities:
- run predictive model
- generate raw scores
- compute confidence / uncertainty
- save top drivers

Outputs:
- structured risk records

### Agent 4 — Evidence Agent
Responsibilities:
- fetch supporting evidence from feature store
- retrieve analogous periods
- package model explanation data

Outputs:
- evidence packet for each prediction

### Agent 5 — Response Planning Agent (LLM)
Responsibilities:
- generate NGO-friendly summary
- recommend intervention category
- tailor summary to audience
- produce action priorities

Possible outputs:
- aid planning brief
- field check list
- district summary card
- donor email draft

### Agent 6 — QA / Guardrail Agent
Responsibilities:
- ensure claims match evidence
- block unsupported certainty
- enforce that generated text references only available evidence
- add confidence disclaimers when needed

Outputs:
- approved report payload

---

## 14) LLM role in detail

### What the LLM should do
- convert structured risk records into readable language
- produce intervention suggestions
- answer “why is this region high-risk?”
- compare two regions
- generate scenario narratives
- produce exports for different audiences

### What the LLM should NOT do
- directly infer truth without model evidence
- invent yields, rainfall, or confidence scores
- make unsupported humanitarian claims
- replace the predictive model

### Best prompt pattern
Every LLM call should receive:
- region name
- time horizon
- structured evidence JSON
- allowed output schema
- allowed intervention taxonomy
- confidence guidance

Use schema-constrained output only.

---

## 15) Tech stack recommendation

## My recommended stack for you

### Frontend
- **Next.js**
- **Tailwind CSS**
- **shadcn/ui**
- **MapLibre or Leaflet** for maps
- **Recharts** for plots

Why:
- looks like a real product
- more portfolio-worthy than a very plain prototype
- easier to make polished cards, panels, dashboards

### Backend
- **FastAPI**
- Python workers / scripts for ingestion and modeling

Why:
- strong for ML integration
- clean API endpoints
- good dev speed

### Data / storage
- **PostgreSQL + PostGIS** if you want maximum polish
- or start with **SQLite/Parquet + GeoJSON** for MVP speed

### ML / analytics
- pandas
- geopandas
- numpy
- scikit-learn
- xgboost or lightgbm
- shap
- rasterio / xarray if needed

### Geospatial access
- Google Earth Engine **or** direct Copernicus + local processing

### LLM orchestration
**Primary recommendation:** **OpenAI Agents SDK first**  
**Secondary option:** LangGraph if you need more workflow persistence complexity.

Why I recommend OpenAI Agents SDK first:
- fewer moving parts
- fits your OpenAI credits
- supports tool use and specialized agent handoffs
- easier to ship quickly

Why LangGraph is still useful:
- better if you want long-running, resumable, stateful multi-step workflows

### Deployment
- local demo first
- deploy later only if everything is stable

For hackathon judging, a polished local or private demo is acceptable if recorded well.

---

## 16) OpenAI vs LangGraph vs LangChain decision

### Best practical answer
Use:

- **OpenAI Agents SDK** for agent orchestration
- **FastAPI** for your backend services
- **structured JSON outputs** everywhere
- optionally **LangGraph** later if you need persistence/resume

### Why not begin with LangChain + too many layers?
Because too much abstraction early can slow you down and make debugging harder.

### Stable build path
Phase 1:
- Python services + FastAPI
- OpenAI Agents SDK
- structured outputs

Phase 2:
- add LangGraph only if you need advanced graph execution

---

## 17) Cost plan

## Likely cost categories

### 1. Data sources
For your prototype, these can be **free** if you stay within non-commercial / research-friendly usage:
- Google Earth Engine (non-commercial / research)
- NASA POWER API
- Copernicus access portals
- FAOSTAT
- Open-Meteo (non-commercial)

### 2. Model training
Local laptop cost = essentially free, except your time.

### 3. LLM usage
This is the main variable cost.

### 4. Hosting
Can be $0 if you demo locally.

## Best cost strategy
Keep costs low by using the LLM only for:
- summaries
- action plans
- comparisons
- report generation

Do **not** use the LLM to process every raster or raw row.

### Suggested prototype budget
- **Data access:** $0
- **Local development:** $0
- **OpenAI API experimentation:** small, controllable budget
- **Optional deployment:** avoid initially

### Smart API-budget discipline
- cache feature summaries
- send only compact JSON to the LLM
- use short prompts
- use structured outputs
- avoid repeated report generation while testing

### Honest expectation
You can build a serious MVP without paying for expensive infrastructure.

---

## 18) Product pages

## Page 1 — Landing / overview
Shows:
- project mission
- current monitored regions
- latest alerts
- impact statement

## Page 2 — Regional risk map
Shows:
- map with low / medium / high risk
- time window selector
- risk legend
- click-through region cards

## Page 3 — Region detail view
Shows:
- risk score
- confidence
- trend chart
- vegetation anomaly chart
- rainfall anomaly chart
- top drivers
- supporting evidence text

## Page 4 — Intervention planner
Shows:
- suggested intervention categories
- urgency level
- confidence-aware explanation
- exportable action brief

## Page 5 — Scenario simulator
Shows:
- adjustable rainfall / temperature assumptions
- forecast shift
- change in priority ranking

## Page 6 — Analyst chat / command center
Shows:
- ask questions about selected region
- compare two districts
- generate donor/NGO summary

---

## 19) User stories

### NGO analyst
“As an analyst, I want to see which regions are most likely to face near-term agricultural stress so I can prioritize field verification.”

### Program manager
“As a program manager, I want a clear explanation of why a region is high-risk so I can defend intervention choices.”

### Donor communications lead
“As a donor-facing user, I want a concise and evidence-backed brief that explains why action is needed.”

### Field officer
“As a field officer, I want a short operational checklist for the selected district.”

---

## 20) Intervention taxonomy

Use a constrained taxonomy so the LLM stays grounded.

### Examples
- field verification recommended
- emergency procurement planning
- alternate sourcing recommended
- school-feeding contingency review
- irrigation / water stress assessment
- agronomy advisory outreach
- market monitoring follow-up

The LLM chooses only from approved categories and explains why.

---

## 21) Guardrails and honesty

You must present this as a **decision-support system**, not a guaranteed oracle.

### Required guardrails
- show confidence labels
- show evidence source list
- avoid hard claims like “famine will happen”
- label simulated or synthetic data clearly
- distinguish forecast from observation
- avoid fabricated policy advice

### Good phrasing
- “elevated risk”
- “warning signal”
- “suggested priority for follow-up”
- “evidence indicates increased crop stress likelihood”

---

## 22) Evaluation plan

### If using classification
Metrics:
- F1-score
- precision / recall
- ROC-AUC
- calibration if possible

### If using regression / score prediction
Metrics:
- MAE / RMSE
- rank correlation
- error by region / season

### Product evaluation
- explanation quality
- response usefulness
- latency for one region analysis
- robustness to missing data

### Demo evaluation
Use 2–3 example regions:
- one low risk
- one medium risk
- one high risk

This makes the story very clear.

---

## 23) Data quality and missing-data strategy

### Common problems
- missing satellite observations
- cloud contamination
- inconsistent region boundaries
- sparse crop data
- delayed statistics

### Handling strategy
- aggregate over time windows
- impute with rolling averages
- attach quality flags
- degrade confidence when data is incomplete
- explicitly label simulated data

---

## 24) MVP milestones

## Milestone 1 — Project setup
- repo init
- backend skeleton
- frontend skeleton
- region schema and data contracts

## Milestone 2 — Data ingestion
- select 1 country or 1–3 regions
- ingest weather and crop baseline
- ingest vegetation proxy data
- save processed features

## Milestone 3 — Feature engineering
- build regional feature table
- compute anomalies and rolling metrics
- create composite stress score

## Milestone 4 — Risk engine
- baseline scoring
- optional ML model
- save outputs and top drivers

## Milestone 5 — Agent layer
- response planning agent
- evidence-constrained prompts
- region summary generation

## Milestone 6 — UI
- risk map
- region detail page
- brief export card

## Milestone 7 — Scenario mode
- simple what-if controls
- regenerate risk narrative

## Milestone 8 — polish
- screenshots
- final README
- demo video
- Devpost visuals

---

## 25) Day-by-day execution plan

## Day 1
- finalize product name and scope
- choose 1 country or region set
- choose target variable definition
- create repo structure
- wire frontend and backend shells

## Day 2
- set up data access path
- pull first weather and agriculture samples
- choose satellite path: Earth Engine or direct source
- decide region boundaries

## Day 3
- engineer first features
- build first regional dataframe
- visualize sample region trends

## Day 4
- implement composite risk score
- validate that outputs look sensible
- define intervention taxonomy

## Day 5
- add LightGBM / XGBoost baseline
- compare with composite score
- save predictions and explanations

## Day 6
- build region detail endpoint
- create evidence payload format
- add confidence scoring logic

## Day 7
- add OpenAI agent summary flow
- enforce structured output
- generate first region briefs

## Day 8
- build dashboard and map
- connect API endpoints
- polish state handling

## Day 9
- add scenario simulator
- compare baseline vs simulated rainfall stress

## Day 10
- build exportable donor / NGO brief
- refine copy and explanation panels

## Day 11
- run full demo path end to end
- fix bugs, reduce latency

## Day 12
- record screenshots and charts
- write README and architecture diagram

## Day 13+
- polish UI, pitch, and video
- add stretch features only if stable

---

## 26) Repo structure

```text
harvestguard-ai/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── public/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── services/
│   │   ├── agents/
│   │   ├── models/
│   │   └── schemas/
│   ├── notebooks/
│   ├── pipelines/
│   └── tests/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── examples/
│
├── docs/
│   ├── architecture.md
│   ├── demo-script.md
│   └── prompts.md
│
├── README.md
├── requirements.txt
└── docker-compose.yml
```

---

## 27) Backend modules

### `ingestion_service.py`
Pulls and caches source data.

### `feature_service.py`
Builds region-level features.

### `risk_service.py`
Runs composite score and model predictions.

### `evidence_service.py`
Packages supporting evidence.

### `agent_service.py`
Calls the LLM / agent orchestration.

### `scenario_service.py`
Applies hypothetical weather changes and recomputes risk.

---

## 28) API endpoints

### `GET /regions`
Returns supported regions.

### `GET /regions/{id}/risk`
Returns current risk summary.

### `GET /regions/{id}/evidence`
Returns evidence payload and top drivers.

### `POST /regions/{id}/brief`
Generates LLM-backed action brief.

### `POST /scenario`
Runs what-if scenario and returns updated risk outputs.

### `GET /alerts`
Returns highest-priority regions.

---

## 29) Prompt engineering plan

### System rules
- only use provided evidence JSON
- never invent measurements
- always include confidence language
- only choose intervention labels from taxonomy
- mention uncertainty when evidence is incomplete

### Output schemas
#### `RegionSummary`
- region_name
- risk_level
- confidence
- short_reason
- top_drivers
- suggested_actions
- caution_note

#### `ComparisonSummary`
- region_a
- region_b
- main_difference
- stronger_signals_in_a
- stronger_signals_in_b
- action_takeaway

#### `DonorBrief`
- headline
- context
- evidence
- why_it_matters
- recommended_next_step

---

## 30) Example end-to-end flow

1. user opens dashboard  
2. app loads latest regional risk table  
3. user clicks a district  
4. backend fetches risk + evidence  
5. model explanation and charts render  
6. user clicks “Generate NGO Brief”  
7. response planning agent receives structured evidence  
8. QA agent checks for unsupported claims  
9. final brief is displayed and exportable  

---

## 31) What makes this unique

### Why people probably will not build this
Most beginner hackathon teams choose:
- a chatbot
- a note app
- a donation listing app
- a quiz generator

This project stands out because it combines:
- geospatial intelligence
- climate / agriculture reasoning
- predictive modeling
- agentic planning
- polished decision-support UX

It feels much more like a serious AI product.

---

## 32) What not to do

Do **not**:
- claim nation-scale famine prediction with perfect precision
- add too many data sources too early
- rely only on the LLM
- build a huge generic chat interface first
- spend all your time on map polish before the model works

---

## 33) Best MVP version for actually shipping

If time gets tight, this is the best reduced scope:

### Narrow MVP
- one country
- a handful of regions
- satellite vegetation proxy
- weather anomalies
- historical crop context
- composite score + one ML model
- one LLM action brief
- one clean dashboard

That is enough to be impressive.

---

## 34) Best stretch features

### Stretch 1 — Analog year retrieval
Show similar prior periods and outcomes.

### Stretch 2 — Weekly digest generation
Auto-generate alert summary for top 5 regions.

### Stretch 3 — Multi-audience report generator
Switch between NGO, school-feeding, and donor versions.

### Stretch 4 — Scenario simulator
“What if rainfall stays 20% below normal?”

### Stretch 5 — Agent debate mode
One agent proposes intervention priorities, another checks evidence sufficiency, then a final agent resolves the recommendation.

---

## 35) Demo strategy

### Best demo narrative
> “Food insecurity response is often late because weak signals are scattered across climate, vegetation, and crop data. HarvestGuard AI unifies these signals, predicts rising regional risk, explains why, and helps NGOs plan earlier action.”

### Demo sequence
1. open dashboard and show regional risk map  
2. highlight one high-risk region  
3. open evidence panel  
4. show model drivers and charts  
5. generate NGO brief  
6. run a what-if scenario  
7. show how priorities change  

This is a very strong 2–4 minute demo flow.

---

## 36) Judging alignment

### Clarity
Easy to explain: early warning for food insecurity risk.

### Innovation
Combines geospatial data, predictive modeling, and agentic decision support.

### Impact Potential
Strong SDG 2 relevance and real operational use.

### Feasibility
Buildable as a regional prototype within hackathon scope.

### Relevance to Theme
Direct fit to Zero Hunger and sustainable agriculture.

### Presentation
Maps, charts, and generated intervention briefs create a highly visual demo.

---

## 37) Risks and mitigations

### Risk: data complexity becomes too high
**Mitigation:** start with one country and aggregated regional data.

### Risk: geospatial pipeline takes too long
**Mitigation:** precompute and cache features; start with small samples.

### Risk: agent output hallucinates
**Mitigation:** structured evidence input, schema-constrained output, QA agent.

### Risk: model quality is weak
**Mitigation:** use transparent composite baseline and explainable tabular model.

### Risk: UI takes too long
**Mitigation:** prioritize one polished dashboard and one region detail page.

---

## 38) Final recommendation

This should be your build order:

1. **Lock the problem** — early warning for regional crop stress / food insecurity risk  
2. **Start with one region set** — not the whole world  
3. **Build the feature table** — weather + vegetation + crop history  
4. **Build composite scoring** — get signal working fast  
5. **Add LightGBM / XGBoost** — improve technical depth  
6. **Add agent-generated briefs** — make it feel next-level  
7. **Polish the dashboard and story** — win on clarity and presentation  

If you execute this cleanly, this can absolutely become a standout portfolio project and a serious hackathon submission.

---

## 39) Recommended final name options

- **HarvestGuard AI**
- **AgriSentinel**
- **CropShield AI**
- **FoodFrontier AI**
- **HungerMap AI**

### Best choice
**HarvestGuard AI** sounds professional, memorable, and strong on GitHub and Devpost.

---

## 40) Immediate next actions

### Right now
1. choose the final name  
2. choose the geographic scope  
3. decide whether to use Earth Engine first or direct sources  
4. create repo and folder structure  
5. define the first region-level schema  

### Best next deliverables after this plan
- `README.md`
- architecture diagram
- data schema JSON
- day-1 coding checklist
- initial FastAPI skeleton
- prompt templates for the agents

