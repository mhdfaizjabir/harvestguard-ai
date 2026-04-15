"use client";

import { FormEvent, useMemo, useState } from "react";

type RiskLevel = "unknown" | "low" | "medium" | "high";
type Audience = "ngo" | "donor" | "school_feeding" | "field_ops";

interface RegionRisk {
  id: string;
  name: string;
  risk_level: RiskLevel;
  confidence: number;
  top_drivers: string[];
}

interface RegionBrief {
  region_id: string;
  summary: string;
  suggested_action: string;
  caution_note: string;
}

interface FeedbackSubmissionResponse {
  feedback_id: string;
  region_id: string;
  submitted_at: string;
  status: "accepted" | "queued_for_retraining";
  message: string;
}

interface ExplainabilityRecord {
  method: string;
  feature_values: Record<string, number>;
  shap_values: Record<string, number>;
  top_positive_drivers: string[];
  top_negative_drivers: string[];
  summary_plot_data: Record<string, number>;
}

interface TrendPoint {
  date: string;
  value: number;
}

interface FeedbackSummary {
  region_id: string;
  total_feedback: number;
  match_count: number;
  match_rate: number | null;
  predicted_risk: RiskLevel;
  latest_observation: RiskLevel | null;
  observer_breakdown: Record<string, number>;
}

interface EvidencePacket {
  region: {
    id: string;
    name: string;
    country: string;
    coordinates: {
      latitude: number;
      longitude: number;
    };
  };
  weather: {
    avg_temperature_c: number | null;
    avg_precipitation_mm: number | null;
    precip_trend_last_30d: number | null;
    data_points: number;
    temperature_history?: TrendPoint[];
    precipitation_history?: TrendPoint[];
  };
  geospatial_context: {
    dominant_crop: string;
    vegetation_anomaly: number | null;
    soil_moisture_percentile: number | null;
    drought_index: number | null;
    crop_sensitivity: number | null;
    seasonal_phase: string;
    boundary_quality: string;
    source: string;
    soil_moisture_history?: TrendPoint[];
    vegetation_history?: TrendPoint[];
  };
  risk_record: {
    risk_level: RiskLevel;
    confidence: number;
    score: number;
    score_components: Record<string, number>;
    top_drivers: string[];
    model_prediction?: {
      model_name: string;
      risk_probability: number;
      explanation_method: string;
      feature_contributions: Record<string, number>;
      feature_importances: Record<string, number>;
      top_explanations?: string[];
    } | null;
  };
  explainability?: ExplainabilityRecord | null;
  evidence_sources: string[];
  quality_flags: string[];
}

interface RiskForecast {
  horizon_days: number;
  risk_level: RiskLevel;
  confidence: number;
  confidence_band: "low" | "medium" | "high";
  score: number;
  score_components: Record<string, number>;
  top_drivers: string[];
  reasoning: string;
  model_prediction?: {
    model_name: string;
    risk_probability: number;
    explanation_method: string;
    feature_contributions: Record<string, number>;
    feature_importances: Record<string, number>;
    top_explanations?: string[];
  } | null;
}

interface WorkflowResponse {
  region_id: string;
  session_id: string;
  mode: "langgraph" | "fallback";
  brief: RegionBrief;
  handoff_path: string[];
  trace_notes: string[];
}

interface ScenarioResponse {
  region_id: string;
  scenario: string;
  evidence: EvidencePacket;
  brief: RegionBrief;
  original_risk: AnalysisResponse["computed_risk"];
  simulated_risk: AnalysisResponse["computed_risk"];
}

interface AnalysisResponse {
  region_id: string;
  name: string;
  country: string;
  evidence: EvidencePacket;
  computed_risk: EvidencePacket["risk_record"] & {
    forecast?: RiskForecast[];
  };
}

interface LocationResult {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  country: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function formatRiskLevel(level: RiskLevel) {
  return level.replace(/^./, (letter) => letter.toUpperCase());
}

function getRiskColor(level: RiskLevel) {
  switch (level) {
    case "high":
      return "#c2410c";
    case "medium":
      return "#d97706";
    case "low":
      return "#3f6212";
    default:
      return "#475569";
  }
}

function getRiskBadgeStyle(level: RiskLevel) {
  switch (level) {
    case "high":
      return {
        background: "#fee2e2",
        color: "#991b1b",
        border: "1px solid #fecaca",
      };
    case "medium":
      return {
        background: "#fef3c7",
        color: "#92400e",
        border: "1px solid #fde68a",
      };
    case "low":
      return {
        background: "#dcfce7",
        color: "#166534",
        border: "1px solid #bbf7d0",
      };
    default:
      return {
        background: "#e2e8f0",
        color: "#334155",
        border: "1px solid #cbd5e1",
      };
  }
}

function formatValue(value: number | null, suffix = "") {
  return value === null || Number.isNaN(value) ? "Unavailable" : `${value.toFixed(2)}${suffix}`;
}

function formatAudience(audience: Audience) {
  return audience.replace(/_/g, " ");
}

function getStatusLabel({
  isSearching,
  isLoadingRisk,
  selectedLocation,
}: {
  isSearching: boolean;
  isLoadingRisk: boolean;
  selectedLocation: LocationResult | null;
}) {
  if (isSearching) {
    return "Searching places...";
  }
  if (isLoadingRisk) {
    return "Running live analysis...";
  }
  if (selectedLocation) {
    return `Selected place: ${selectedLocation.name}`;
  }
  return "Search any place in the world to begin analysis.";
}

function MetricCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent: string;
}) {
  return (
    <div
      style={{
        border: "1px solid rgba(148,163,184,0.14)",
        borderRadius: "18px",
        padding: "14px 16px",
        background: `linear-gradient(180deg, rgba(15,23,42,0.9) 0%, rgba(10,16,30,0.96) 100%), ${accent}`,
      }}
    >
      <div style={{ fontSize: "0.76rem", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</div>
      <div style={{ marginTop: "8px", fontSize: "1.2rem", fontWeight: 800, color: "#f8fafc" }}>{value}</div>
    </div>
  );
}

function MiniBarChart({
  title,
  values,
  color,
  filterZero = false,
  maxItems,
  emptyMessage = "No strong signal available for this view.",
}: {
  title: string;
  values: Record<string, number>;
  color: string;
  filterZero?: boolean;
  maxItems?: number;
  emptyMessage?: string;
}) {
  const entries = Object.entries(values)
    .filter(([, value]) => !filterZero || Math.abs(value) >= 0.001)
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .slice(0, maxItems ?? Number.POSITIVE_INFINITY);
  const maxValue = Math.max(...entries.map(([, value]) => Math.abs(value)), 0.001);

  return (
    <section
      style={{
        border: "1px solid #d6deea",
        borderRadius: "18px",
        padding: "1rem",
        background: "linear-gradient(180deg, #ffffff 0%, #f8fbff 100%)",
        boxShadow: "0 12px 24px rgba(15, 23, 42, 0.08)",
        color: "#0f172a",
      }}
    >
      <h3 style={{ marginTop: 0, marginBottom: "0.9rem", fontSize: "1rem", color: "#0f172a" }}>{title}</h3>
      {entries.length === 0 ? (
        <p style={{ margin: 0, color: "#64748b", lineHeight: 1.6 }}>{emptyMessage}</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.65rem" }}>
          {entries.map(([label, value]) => (
            <div key={label}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.25rem", gap: "0.75rem" }}>
                <span style={{ color: "#0f172a", fontWeight: 600 }}>{label.replace(/_/g, " ")}</span>
                <strong style={{ color: "#334155" }}>{value.toFixed(3)}</strong>
              </div>
              <div style={{ height: "10px", background: "#dbe7f5", borderRadius: "999px", overflow: "hidden" }}>
                <div
                  style={{
                    height: "100%",
                    width: `${(Math.abs(value) / maxValue) * 100}%`,
                    background: color,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function renderSentenceBullets(text: string, color: string) {
  const sentences = text
    .split(/(?<=[.!?])\s+/)
    .map((sentence) => sentence.trim())
    .filter(Boolean);

  if (sentences.length <= 1) {
    return <p style={{ margin: 0, color, lineHeight: 1.75 }}>{text}</p>;
  }

  return (
    <ul style={{ margin: 0, paddingLeft: "1.1rem", color, lineHeight: 1.75 }}>
      {sentences.map((sentence, index) => (
        <li key={`${sentence}-${index}`} style={{ marginBottom: "0.45rem" }}>
          {sentence}
        </li>
      ))}
    </ul>
  );
}

function TrendChart({
  title,
  points,
  color,
}: {
  title: string;
  points: TrendPoint[];
  color: string;
}) {
  const [activePoint, setActivePoint] = useState<TrendPoint | null>(points[points.length - 1] ?? null);

  if (!points.length) {
    return (
      <section style={{ border: "1px solid rgba(148,163,184,0.14)", borderRadius: "18px", padding: "1rem", background: "rgba(255,255,255,0.06)" }}>
        <h3 style={{ marginTop: 0, color: "#f8fafc" }}>{title}</h3>
        <p style={{ marginBottom: 0, color: "#94a3b8" }}>No recent history available.</p>
      </section>
    );
  }

  const width = 320;
  const height = 120;
  const min = Math.min(...points.map((point) => point.value));
  const max = Math.max(...points.map((point) => point.value));
  const range = Math.max(max - min, 0.001);
  const path = points
    .map((point, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * width;
      const y = height - ((point.value - min) / range) * height;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");

  return (
    <section style={{ border: "1px solid rgba(148,163,184,0.14)", borderRadius: "18px", padding: "1rem", background: "rgba(255,255,255,0.06)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", alignItems: "baseline" }}>
        <div>
          <h3 style={{ marginTop: 0, marginBottom: "0.2rem", color: "#f8fafc" }}>{title}</h3>
          <span style={{ color: "#94a3b8", fontSize: "0.82rem" }}>
            {points[0]?.date} to {points[points.length - 1]?.date}
          </span>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ color: "#94a3b8", fontSize: "0.78rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>Latest</div>
          <div style={{ color: "#f8fafc", fontSize: "1rem", fontWeight: 800 }}>
            {points[points.length - 1]?.value.toFixed(2)}
          </div>
        </div>
      </div>
      <div
        style={{
          marginBottom: "0.75rem",
          padding: "0.65rem 0.8rem",
          borderRadius: "12px",
          background: "rgba(15,23,42,0.52)",
          color: "#dbeafe",
          display: "flex",
          justifyContent: "space-between",
          gap: "0.75rem",
          flexWrap: "wrap",
        }}
      >
        <span style={{ fontWeight: 700 }}>{activePoint?.date ?? "Hover a point"}</span>
        <span style={{ color: "#7dd3fc" }}>{activePoint ? activePoint.value.toFixed(2) : "No value"}</span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height: "120px", overflow: "visible" }}>
        <path d={path} fill="none" stroke={color} strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
        {points.map((point, index) => {
          const x = (index / Math.max(points.length - 1, 1)) * width;
          const y = height - ((point.value - min) / range) * height;
          return (
            <circle
              key={`${point.date}-${index}`}
              cx={x}
              cy={y}
              r="5"
              fill={color}
              style={{ cursor: "pointer" }}
              onMouseEnter={() => setActivePoint(point)}
            >
              <title>{`${point.date}: ${point.value.toFixed(2)}`}</title>
            </circle>
          );
        })}
      </svg>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: "0.7rem", color: "#cbd5e1", fontSize: "0.85rem" }}>
        <span>Min {min.toFixed(2)}</span>
        <span>Latest {points[points.length - 1]?.value.toFixed(2)}</span>
        <span>Max {max.toFixed(2)}</span>
      </div>
    </section>
  );
}

export default function Home() {
  const [showIntro, setShowIntro] = useState(true);
  const [selectedLocation, setSelectedLocation] = useState<LocationResult | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string>("");
  const [riskData, setRiskData] = useState<RegionRisk | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [brief, setBrief] = useState<RegionBrief | null>(null);
  const [scenario, setScenario] = useState<ScenarioResponse | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowResponse | null>(null);
  const [forecast, setForecast] = useState<RiskForecast[] | null>(null);
  const [feedbackSummary, setFeedbackSummary] = useState<FeedbackSummary | null>(null);
  const [error, setError] = useState("");
  const [isLoadingRisk, setIsLoadingRisk] = useState(false);
  const [isLoadingBrief, setIsLoadingBrief] = useState(false);
  const [isLoadingScenario, setIsLoadingScenario] = useState(false);
  const [isLoadingWorkflow, setIsLoadingWorkflow] = useState(false);
  const [isLoadingForecast, setIsLoadingForecast] = useState(false);
  const [feedbackResponse, setFeedbackResponse] = useState<FeedbackSubmissionResponse | null>(null);
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<LocationResult[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [audience, setAudience] = useState<Audience>("ngo");

  async function fetchLocationAnalysis(latitude: number, longitude: number, name?: string) {
    setIsLoadingRisk(true);
    setBrief(null);
    setScenario(null);
    setWorkflow(null);
    setForecast(null);
    setFeedbackSummary(null);
    setFeedbackResponse(null);
    setError("");

    try {
      const reverse = await fetch(`${API_BASE_URL}/regions/locations/reverse?latitude=${latitude}&longitude=${longitude}`);
      const resolvedLocation: LocationResult = reverse.ok
        ? await reverse.json()
        : {
            id: `${latitude}-${longitude}`,
            name: name ?? `${latitude.toFixed(3)}, ${longitude.toFixed(3)}`,
            latitude,
            longitude,
            country: "Unknown",
          };

      const [riskRes, analysisRes, feedbackSummaryRes] = await Promise.all([
        fetch(`${API_BASE_URL}/regions/geo/point/risk?latitude=${latitude}&longitude=${longitude}`),
        fetch(`${API_BASE_URL}/regions/geo/point/analysis?latitude=${latitude}&longitude=${longitude}`),
        fetch(`${API_BASE_URL}/regions/geo/point/feedback/summary?latitude=${latitude}&longitude=${longitude}`),
      ]);

      if (!riskRes.ok || !analysisRes.ok) {
        throw new Error("Failed to fetch point analysis");
      }

      const riskPayload: RegionRisk = await riskRes.json();
      const analysisPayload: AnalysisResponse = await analysisRes.json();
      const feedbackSummaryPayload: FeedbackSummary | null = feedbackSummaryRes.ok ? await feedbackSummaryRes.json() : null;

      setRiskData(riskPayload);
      setAnalysis(analysisPayload);
      setFeedbackSummary(feedbackSummaryPayload);
      setLastUpdated(new Date().toLocaleString());
      setSelectedLocation({
        id: resolvedLocation.id ?? riskPayload.id,
        name: name ?? resolvedLocation.name,
        latitude,
        longitude,
        country: resolvedLocation.country,
      });
    } catch {
      setError("Could not fetch live risk data for that location.");
    } finally {
      setIsLoadingRisk(false);
    }
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (searchQuery.trim().length < 2) {
      return;
    }

    setIsSearching(true);
    setHasSearched(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE_URL}/regions/locations/search?query=${encodeURIComponent(searchQuery.trim())}`);
      if (!res.ok) {
        throw new Error("Failed to search locations");
      }

      const results: LocationResult[] = await res.json();
      setSearchResults(results);
      if (results.length > 0) {
        const primaryResult = results[0];
        await fetchLocationAnalysis(primaryResult.latitude, primaryResult.longitude, primaryResult.name);
      } else {
        setSelectedLocation(null);
        setRiskData(null);
        setAnalysis(null);
        setBrief(null);
        setScenario(null);
        setWorkflow(null);
        setForecast(null);
      }
    } catch {
      setError("Could not search locations right now.");
    } finally {
      setIsSearching(false);
    }
  }


  async function generateBrief() {
    if (!selectedLocation) {
      return;
    }

    setIsLoadingBrief(true);
    setError("");

    try {
      const res = await fetch(
        `${API_BASE_URL}/regions/geo/point/brief?latitude=${selectedLocation.latitude}&longitude=${selectedLocation.longitude}&audience=${audience}`,
        { method: "POST" }
      );
      if (!res.ok) {
        throw new Error("Failed to generate brief");
      }

      const data: RegionBrief = await res.json();
      setBrief(data);
    } catch {
      setError("Could not generate the intervention brief.");
    } finally {
      setIsLoadingBrief(false);
    }
  }

  async function runScenario() {
    if (!selectedLocation) {
      return;
    }

    setIsLoadingScenario(true);
    setError("");

    try {
      const res = await fetch(
        `${API_BASE_URL}/regions/geo/point/scenario?latitude=${selectedLocation.latitude}&longitude=${selectedLocation.longitude}&rainfall_reduction=20&audience=${audience}`
      );
      if (!res.ok) {
        throw new Error("Failed to run scenario");
      }

      const data: ScenarioResponse = await res.json();
      setScenario(data);
    } catch {
      setError("Could not run the rainfall reduction scenario.");
    } finally {
      setIsLoadingScenario(false);
    }
  }

  async function runWorkflow() {
    if (!selectedLocation) {
      return;
    }

    setIsLoadingWorkflow(true);
    setError("");

    try {
      const res = await fetch(
        `${API_BASE_URL}/regions/geo/point/workflow?latitude=${selectedLocation.latitude}&longitude=${selectedLocation.longitude}&audience=${audience}`,
        { method: "POST" }
      );
      if (!res.ok) {
        throw new Error("Failed to run workflow");
      }

      const data: WorkflowResponse = await res.json();
      setWorkflow(data);
      setBrief(data.brief);
    } catch {
      setError("Could not run the LangGraph workflow.");
    } finally {
      setIsLoadingWorkflow(false);
    }
  }

  async function runForecast() {
    if (!selectedLocation) {
      return;
    }

    setIsLoadingForecast(true);
    setError("");

    try {
      const res = await fetch(
        `${API_BASE_URL}/regions/geo/point/forecast?latitude=${selectedLocation.latitude}&longitude=${selectedLocation.longitude}`
      );
      if (!res.ok) {
        throw new Error("Failed to run forecast");
      }

      const data: AnalysisResponse = await res.json();
      setForecast(data.computed_risk.forecast || []);
    } catch {
      setError("Could not run the risk forecast.");
    } finally {
      setIsLoadingForecast(false);
    }
  }

  async function submitFeedback(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedLocation) {
      return;
    }

    setIsSubmittingFeedback(true);
    setError("");

    const formData = new FormData(event.currentTarget);
    const feedbackData = {
      latitude: selectedLocation.latitude,
      longitude: selectedLocation.longitude,
      observed_crop_stress: formData.get("observed_crop_stress") as string,
      confidence: parseFloat(formData.get("confidence") as string),
      observation_date: new Date().toISOString().split('T')[0],
      notes: formData.get("notes") as string,
      observer_type: formData.get("observer_type") as string,
    };

    try {
      const res = await fetch(`${API_BASE_URL}/regions/geo/point/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(feedbackData),
      });

      if (!res.ok) {
        throw new Error("Failed to submit feedback");
      }

      const data: FeedbackSubmissionResponse = await res.json();
      setFeedbackResponse(data);
      const summaryRes = await fetch(
        `${API_BASE_URL}/regions/geo/point/feedback/summary?latitude=${selectedLocation.latitude}&longitude=${selectedLocation.longitude}`
      );
      if (summaryRes.ok) {
        const summaryData: FeedbackSummary = await summaryRes.json();
        setFeedbackSummary(summaryData);
      }
    } catch {
      setError("Could not submit ground truth feedback.");
    } finally {
      setIsSubmittingFeedback(false);
    }
  }

  const scoreComponents = useMemo(() => analysis?.computed_risk.score_components ?? {}, [analysis]);
  const shapValues = useMemo(() => {
    const summaryPlot = analysis?.evidence.explainability?.summary_plot_data ?? {};
    const total = Object.values(summaryPlot).reduce((sum, value) => sum + Math.abs(value), 0);
    if (total > 0.0001) {
      return summaryPlot;
    }
    return analysis?.computed_risk.model_prediction?.feature_contributions ?? {};
  }, [analysis]);
  const modelImportances = useMemo(
    () => analysis?.computed_risk.model_prediction?.feature_importances ?? {},
    [analysis]
  );
  const temperatureHistory = useMemo(() => analysis?.evidence.weather.temperature_history ?? [], [analysis]);
  const precipitationHistory = useMemo(() => analysis?.evidence.weather.precipitation_history ?? [], [analysis]);
  const soilMoistureHistory = useMemo(() => analysis?.evidence.geospatial_context.soil_moisture_history ?? [], [analysis]);
  const vegetationHistory = useMemo(() => analysis?.evidence.geospatial_context.vegetation_history ?? [], [analysis]);

  if (showIntro) {
    return (
      <main
        style={{
          minHeight: "100vh",
          padding: "1.5rem",
          fontFamily: "system-ui, sans-serif",
          color: "#e2e8f0",
          overflowX: "hidden",
          background:
            "radial-gradient(circle at top, rgba(56,189,248,0.12), transparent 26%), linear-gradient(180deg, #020617 0%, #08111f 45%, #020617 100%)",
        }}
      >
        <div
          style={{
            maxWidth: "1180px",
            margin: "0 auto",
            minHeight: "calc(100vh - 3rem)",
            borderRadius: "28px",
            padding: "24px",
            background: "linear-gradient(180deg, rgba(7,15,28,0.96) 0%, rgba(5,11,22,0.98) 100%)",
            border: "1px solid rgba(148,163,184,0.16)",
            boxShadow: "0 30px 70px rgba(0,0,0,0.45)",
            display: "grid",
            gap: "1.25rem",
            alignContent: "start",
          }}
        >
          <section
            style={{
              padding: "1.6rem",
              borderRadius: "24px",
              background:
                "linear-gradient(135deg, rgba(11,19,35,0.98) 0%, rgba(11,27,48,0.96) 56%, rgba(7,14,28,0.98) 100%)",
              border: "1px solid rgba(148,163,184,0.14)",
            }}
          >
            <p style={{ margin: "0 0 0.45rem", color: "#7dd3fc", fontSize: "0.78rem", letterSpacing: "0.14em", textTransform: "uppercase" }}>
              Hyperbloom V2 Submission
            </p>
            <h1 style={{ fontSize: "2.9rem", margin: "0 0 0.75rem", letterSpacing: "-0.05em", color: "#f8fafc" }}>HarvestGuard AI</h1>
            <p style={{ margin: "0 0 1rem", color: "#dbeafe", fontSize: "1.08rem", lineHeight: 1.7, maxWidth: "900px" }}>
              An SDG 2 decision-support system that helps responders spot crop stress earlier, understand why risk is rising,
              and decide what to do next before food insecurity gets worse.
            </p>
            <div style={{ display: "flex", gap: "0.85rem", flexWrap: "wrap" }}>
              <button
                onClick={() => setShowIntro(false)}
                style={{
                  padding: "0.95rem 1.2rem",
                  cursor: "pointer",
                  borderRadius: "14px",
                  border: "1px solid rgba(125,211,252,0.3)",
                  background: "linear-gradient(135deg, #0891b2 0%, #1d4ed8 100%)",
                  color: "#eff6ff",
                  fontWeight: 800,
                  boxShadow: "0 18px 30px rgba(8, 145, 178, 0.24)",
                }}
              >
                Open Live Dashboard
              </button>
              <div style={{ padding: "0.95rem 1.1rem", borderRadius: "14px", border: "1px solid rgba(148,163,184,0.14)", background: "linear-gradient(180deg, rgba(15,23,42,0.82) 0%, rgba(9,15,29,0.9) 100%)", color: "#cbd5e1" }}>
                Best demo searches: Kanyakumari, Doha, Nairobi, Algiers, Manila
              </div>
            </div>
          </section>

          <section
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: "1rem",
            }}
          >
            {[
              {
                title: "What It Does",
                copy: "Search any place, see crop-stress risk, read the evidence, project short-term risk, and generate role-specific action guidance.",
              },
              {
                title: "Who It Helps",
                copy: "NGOs, donors, school-feeding teams, and field operators who need clearer signals before they decide where to respond.",
              },
              {
                title: "Why It Matters",
                copy: "Food insecurity often becomes obvious too late. HarvestGuard AI is built to turn scattered environmental signals into earlier action.",
              },
            ].map((item) => (
              <section
                key={item.title}
                style={{
                  border: "1px solid rgba(148,163,184,0.14)",
                  borderRadius: "18px",
                  padding: "1rem",
                  background: "linear-gradient(180deg, rgba(15,23,42,0.78) 0%, rgba(9,15,29,0.88) 100%)",
                }}
              >
                <h3 style={{ marginTop: 0, color: "#f8fafc" }}>{item.title}</h3>
                <p style={{ marginBottom: 0, color: "#cbd5e1", lineHeight: 1.7 }}>{item.copy}</p>
              </section>
            ))}
          </section>

          <section
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))",
              gap: "1rem",
            }}
          >
            {[
              {
                title: "Scenario Analysis",
                copy: "Tests a what-if shock like lower rainfall, so users can see how risk changes if conditions worsen.",
              },
              {
                title: "Forecast",
                copy: "Shows where risk may go over the next 7, 14, and 30 days using recent patterns and a confidence band.",
              },
              {
                title: "Feedback Loop",
                copy: "Lets real people submit observations from the field and compare them against the model, making the system more grounded over time.",
              },
            ].map((item) => (
              <section
                key={item.title}
                style={{
                  border: "1px solid rgba(148,163,184,0.14)",
                  borderRadius: "18px",
                  padding: "1rem",
                  background: "linear-gradient(180deg, rgba(15,23,42,0.78) 0%, rgba(9,15,29,0.88) 100%)",
                }}
              >
                <h3 style={{ marginTop: 0, color: "#7dd3fc" }}>{item.title}</h3>
                <p style={{ marginBottom: 0, color: "#cbd5e1", lineHeight: 1.7 }}>{item.copy}</p>
              </section>
            ))}
          </section>
        </div>
      </main>
    );
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        padding: "1.5rem",
        fontFamily: "system-ui, sans-serif",
        color: "#e2e8f0",
        overflowX: "hidden",
        background:
          "radial-gradient(circle at top, rgba(56,189,248,0.12), transparent 26%), linear-gradient(180deg, #020617 0%, #08111f 45%, #020617 100%)",
      }}
    >
      <div
        style={{
          maxWidth: "1320px",
          margin: "0 auto",
          minHeight: "calc(100vh - 3rem)",
          borderRadius: "28px",
          padding: "18px",
          background: "linear-gradient(180deg, rgba(7,15,28,0.96) 0%, rgba(5,11,22,0.98) 100%)",
          border: "1px solid rgba(148,163,184,0.16)",
          boxShadow: "0 30px 70px rgba(0,0,0,0.45)",
          overflow: "visible",
          display: "flex",
          flexDirection: "column",
          gap: "1rem",
        }}
      >
        <section
          style={{
            padding: "1.3rem 1.3rem 1.05rem",
            borderRadius: "24px",
            background:
              "linear-gradient(135deg, rgba(11,19,35,0.98) 0%, rgba(11,27,48,0.96) 56%, rgba(7,14,28,0.98) 100%)",
            border: "1px solid rgba(148,163,184,0.14)",
            boxShadow: "0 18px 42px rgba(0, 0, 0, 0.24)",
            flex: "0 0 auto",
          }}
        >
          <p style={{ margin: "0 0 0.45rem", color: "#7dd3fc", fontSize: "0.78rem", letterSpacing: "0.14em", textTransform: "uppercase" }}>
            Hyperbloom V2 Submission
          </p>
          <h1 style={{ fontSize: "2.5rem", marginBottom: "1rem", letterSpacing: "-0.05em", color: "#f8fafc" }}>HarvestGuard AI</h1>

        <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1rem", flexWrap: "wrap" }}>
          <form onSubmit={handleSearch} style={{ display: "flex", gap: "0.75rem", flex: "1 1 520px", flexWrap: "wrap" }}>
            <input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Try Doha, Chennai, Lucknow, or Tamil Nadu"
              style={{
                flex: "1 1 320px",
                padding: "0.85rem 1rem",
                border: "1px solid rgba(148,163,184,0.16)",
                borderRadius: "14px",
                background: "rgba(255,255,255,0.04)",
                color: "#f8fafc",
              }}
            />
            <button
              type="submit"
              style={{
                padding: "0.85rem 1.05rem",
                cursor: "pointer",
                borderRadius: "14px",
                border: "1px solid rgba(125,211,252,0.3)",
                background: "linear-gradient(135deg, #0891b2 0%, #1d4ed8 100%)",
                color: "#eff6ff",
                fontWeight: 700,
                boxShadow: "0 16px 28px rgba(8, 145, 178, 0.18)",
              }}
            >
              {isSearching ? "Searching..." : "Search"}
            </button>
          </form>

          <select
            value={audience}
            onChange={(event) => setAudience(event.target.value as Audience)}
            style={{
              padding: "0.85rem 1rem",
              borderRadius: "14px",
              border: "1px solid rgba(148,163,184,0.16)",
              background: "linear-gradient(180deg, rgba(17,24,39,0.85) 0%, rgba(15,23,42,0.78) 100%)",
              color: "#f8fafc",
            }}
          >
            <option value="ngo">NGO</option>
            <option value="donor">Donor</option>
            <option value="school_feeding">School Feeding</option>
            <option value="field_ops">Field Ops</option>
          </select>
        </div>

        <section
          style={{
            marginBottom: "1rem",
            border: "1px solid rgba(148,163,184,0.12)",
            borderRadius: "18px",
            padding: "0.9rem 1rem",
            background: "rgba(255,255,255,0.04)",
          }}
        >
          <strong style={{ display: "block", marginBottom: "0.35rem", color: "#f8fafc" }}>Status</strong>
          <span style={{ color: "#94a3b8" }}>
            {getStatusLabel({ isSearching, isLoadingRisk, selectedLocation })}
          </span>
        </section>
        </section>

        {searchResults.length > 0 && (
          <section
            style={{
              flex: "0 0 auto",
              border: "1px solid rgba(148,163,184,0.14)",
              borderRadius: "18px",
              padding: "1rem",
              background: "rgba(255,255,255,0.04)",
              color: "#e2e8f0",
            }}
          >
            <h2 style={{ marginTop: 0, fontSize: "1rem", color: "#f8fafc" }}>Search Results</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {searchResults.map((result) => (
                <button
                  key={result.id}
                  onClick={() => fetchLocationAnalysis(result.latitude, result.longitude, result.name)}
                  style={{
                    textAlign: "left",
                    padding: "0.85rem",
                    border: "1px solid rgba(148,163,184,0.14)",
                    borderRadius: "14px",
                    background: "rgba(255,255,255,0.04)",
                    color: "#f8fafc",
                    cursor: "pointer",
                  }}
                >
                  <strong>{result.name}</strong>
                  <div style={{ color: "#94a3b8", marginTop: "0.25rem" }}>
                    {result.latitude.toFixed(3)}, {result.longitude.toFixed(3)}
                  </div>
                </button>
              ))}
            </div>
          </section>
        )}

        {hasSearched && !isSearching && searchResults.length === 0 && !error && (
          <section
            style={{
              flex: "0 0 auto",
              border: "1px solid rgba(148,163,184,0.14)",
              borderRadius: "18px",
              padding: "1rem",
              background: "rgba(255,255,255,0.04)",
              color: "#94a3b8",
            }}
          >
            No search results found yet. Try "Doha", "Kanyakumari", "Nairobi", "Sao Paulo", or "Manila".
          </section>
        )}

        <div
          style={{
            flex: "0 0 auto",
            minHeight: "auto",
            overflow: "visible",
            display: "grid",
            gridTemplateColumns: "1fr",
            alignContent: "start",
            gap: "1rem",
          }}
        >
          <section
            style={{
              border: "1px solid rgba(125,211,252,0.12)",
              borderRadius: "22px",
              padding: "1rem 1.15rem",
              background:
                "linear-gradient(135deg, rgba(13,25,44,0.96) 0%, rgba(9,19,36,0.98) 100%)",
              boxShadow: "0 18px 36px rgba(2, 6, 23, 0.24)",
              display: "flex",
              justifyContent: "space-between",
              gap: "1rem",
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
            <div>
              <div style={{ fontSize: "0.76rem", color: "#7dd3fc", letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: "0.35rem" }}>
                Live Analysis Workspace
              </div>
              <h2 style={{ margin: 0, color: "#f8fafc", fontSize: "1.35rem" }}>
                {selectedLocation ? selectedLocation.name : "Search for a location to begin"}
              </h2>
              <p style={{ margin: "0.35rem 0 0", color: "#94a3b8" }}>
                {selectedLocation
                  ? `${selectedLocation.country} | ${selectedLocation.latitude.toFixed(3)}, ${selectedLocation.longitude.toFixed(3)}`
                  : "Use the search box above to load live risk analysis, scenario testing, forecasts, and reports."}
              </p>
              {lastUpdated && (
                <p style={{ margin: "0.35rem 0 0", color: "#64748b", fontSize: "0.88rem" }}>
                  Last updated: {lastUpdated}
                </p>
              )}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(120px, 1fr))", gap: "12px", width: "min(100%, 420px)" }}>
              <MetricCard label="Goal" value="SDG 2" accent="rgba(34,197,94,0.06)" />
              <MetricCard label="Coverage" value="Global" accent="rgba(56,189,248,0.06)" />
              <MetricCard label="Audience" value={formatAudience(audience)} accent="rgba(245,158,11,0.06)" />
            </div>
          </section>

          {selectedLocation && riskData && analysis && (
            <section
              style={{
                border: "1px solid #1e293b",
                borderRadius: "24px",
                padding: "1.15rem",
                background:
                  "linear-gradient(135deg, rgba(15,23,42,0.98) 0%, rgba(10,30,54,0.96) 55%, rgba(8,20,39,0.98) 100%)",
                boxShadow: "0 18px 40px rgba(15, 23, 42, 0.16)",
                color: "#e2e8f0",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: "1rem",
                  flexWrap: "wrap",
                  alignItems: "flex-start",
                }}
              >
                <div>
                  <h2 style={{ marginTop: 0, marginBottom: "0.35rem", color: "#f8fafc" }}>Current Analysis</h2>
                  <p style={{ marginBottom: "0.35rem", fontSize: "1.15rem", fontWeight: 700, color: "#f8fafc" }}>
                    {selectedLocation.name}
                  </p>
                  <p style={{ marginBottom: "0.5rem", color: "#94a3b8" }}>
                    {selectedLocation.country} | {selectedLocation.latitude.toFixed(3)}, {selectedLocation.longitude.toFixed(3)}
                  </p>
                </div>
                <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                  <div
                    style={{
                      minWidth: "120px",
                      padding: "0.75rem 0.9rem",
                      borderRadius: "18px",
                      background: "rgba(255,255,255,0.06)",
                      border: "1px solid rgba(148,163,184,0.18)",
                    }}
                  >
                    <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Risk Level</div>
                    <div style={{ fontSize: "1.1rem", fontWeight: 700, color: getRiskColor(riskData.risk_level) }}>
                      {formatRiskLevel(riskData.risk_level)}
                    </div>
                  </div>
                  <div
                    style={{
                      minWidth: "120px",
                      padding: "0.75rem 0.9rem",
                      borderRadius: "18px",
                      background: "rgba(255,255,255,0.06)",
                      border: "1px solid rgba(148,163,184,0.18)",
                    }}
                  >
                    <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Confidence</div>
                    <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#f8fafc" }}>
                      {Math.round(riskData.confidence * 100)}%
                    </div>
                  </div>
                </div>
              </div>
              <p style={{ marginBottom: "0.5rem", marginTop: "0.8rem", color: "#dbeafe" }}>
                Risk level:{" "}
                <strong style={{ color: getRiskColor(riskData.risk_level) }}>
                  {formatRiskLevel(riskData.risk_level)}
                </strong>
              </p>
              <p style={{ marginBottom: "1rem", color: "#cbd5e1" }}>
                Drivers: {riskData.top_drivers.length > 0 ? riskData.top_drivers.join(", ") : "No drivers returned."}
              </p>
              <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                <button
                  onClick={generateBrief}
                  disabled={isLoadingBrief}
                  style={{
                    padding: "0.8rem 1rem",
                    cursor: "pointer",
                    borderRadius: "999px",
                    border: "1px solid rgba(125,211,252,0.28)",
                    background: "linear-gradient(180deg, rgba(8,145,178,0.16) 0%, rgba(15,23,42,0.75) 100%)",
                    color: "#e0f2fe",
                    fontWeight: 700,
                  }}
                >
                  {isLoadingBrief ? "Generating brief..." : "Generate Brief"}
                </button>
                <button
                  onClick={runScenario}
                  disabled={isLoadingScenario}
                  style={{
                    padding: "0.8rem 1rem",
                    cursor: "pointer",
                    borderRadius: "999px",
                    border: "1px solid rgba(251,191,36,0.25)",
                    background: "linear-gradient(180deg, rgba(217,119,6,0.16) 0%, rgba(15,23,42,0.75) 100%)",
                    color: "#fde68a",
                    fontWeight: 700,
                  }}
                >
                  {isLoadingScenario ? "Running scenario..." : "Run Scenario"}
                </button>
                <button
                  onClick={runForecast}
                  disabled={isLoadingForecast}
                  style={{
                    padding: "0.8rem 1rem",
                    cursor: "pointer",
                    borderRadius: "999px",
                    border: "1px solid rgba(74,222,128,0.24)",
                    background: "linear-gradient(180deg, rgba(22,163,74,0.15) 0%, rgba(15,23,42,0.75) 100%)",
                    color: "#bbf7d0",
                    fontWeight: 700,
                  }}
                >
                  {isLoadingForecast ? "Running forecast..." : "Run Forecast"}
                </button>
              </div>
            </section>
          )}

          {analysis && (
            <>
              <section
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                  gap: "1rem",
                }}
              >
                <section
                  style={{
                    border: "1px solid rgba(148,163,184,0.14)",
                    borderRadius: "18px",
                    padding: "1rem",
                    background: "rgba(255,255,255,0.06)",
                    color: "#e2e8f0",
                  }}
                >
                  <h3 style={{ marginTop: 0, color: "#f8fafc" }}>Observed Signals</h3>
                  <p style={{ color: "#dbeafe" }}>Temperature: {formatValue(analysis.evidence.weather.avg_temperature_c, " C")}</p>
                  <p style={{ color: "#dbeafe" }}>Precipitation: {formatValue(analysis.evidence.weather.avg_precipitation_mm, " mm")}</p>
                  <p style={{ color: "#dbeafe" }}>Rain Trend: {formatValue(analysis.evidence.weather.precip_trend_last_30d, " mm")}</p>
                  <p style={{ color: "#dbeafe" }}>Soil Moisture: {formatValue(analysis.evidence.geospatial_context.soil_moisture_percentile)}</p>
                  <p style={{ color: "#dbeafe" }}>Vegetation Proxy: {formatValue(analysis.evidence.geospatial_context.vegetation_anomaly)}</p>
                  <p style={{ color: "#94a3b8", marginBottom: 0 }}>
                    These are the live environmental signals behind the current risk score.
                  </p>
                </section>

                <section
                  style={{
                    border: "1px solid rgba(148,163,184,0.14)",
                    borderRadius: "18px",
                    padding: "1rem",
                    background: "rgba(255,255,255,0.06)",
                    color: "#e2e8f0",
                  }}
                >
                  <h3 style={{ marginTop: 0, color: "#f8fafc" }}>Model Layer</h3>
                  <p style={{ color: "#dbeafe" }}>
                    Model: {analysis.computed_risk.model_prediction?.model_name === "xgboost_classifier" ? "XGBoost classifier" : analysis.computed_risk.model_prediction?.model_name ?? "Unavailable"}
                  </p>
                  <p style={{ color: "#dbeafe" }}>
                    Probability:{" "}
                    {analysis.computed_risk.model_prediction
                      ? `${(analysis.computed_risk.model_prediction.risk_probability * 100).toFixed(1)}%`
                      : "Unavailable"}
                  </p>
                  <p style={{ color: "#dbeafe" }}>
                    Top drivers: {analysis.computed_risk.model_prediction?.top_explanations?.map((item) => item.replace(/_/g, " ")).join(", ") || "Unavailable"}
                  </p>
                  <p style={{ color: "#94a3b8", marginBottom: 0 }}>
                    This ML layer supports the hybrid risk engine by estimating how strongly the current signal pattern aligns with known stress conditions.
                  </p>
                </section>

                <section
                  style={{
                    border: "1px solid rgba(148,163,184,0.14)",
                    borderRadius: "18px",
                    padding: "1rem",
                    background: "rgba(255,255,255,0.06)",
                    color: "#e2e8f0",
                  }}
                >
                  <h3 style={{ marginTop: 0, color: "#f8fafc" }}>Stakeholder Lens</h3>
                  <p style={{ color: "#dbeafe" }}>Current audience: {formatAudience(audience)}</p>
                  <p style={{ color: "#94a3b8", lineHeight: 1.6 }}>
                    Same evidence, different framing: NGOs get operational response ideas, donors get funding-oriented context,
                    school feeding focuses on supply continuity, and field ops emphasizes verification and action steps.
                  </p>
                  <p style={{ color: "#dbeafe" }}>
                    Top positive SHAP drivers: {analysis.evidence.explainability?.top_positive_drivers.join(", ") || "Unavailable"}
                  </p>
                  <p style={{ color: "#dbeafe" }}>
                    Top negative SHAP drivers: {analysis.evidence.explainability?.top_negative_drivers.join(", ") || "Unavailable"}
                  </p>
                </section>
              </section>

              <section
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                  gap: "1rem",
                }}
              >
                <MiniBarChart title="Risk Score Components" values={scoreComponents} color="#2563eb" />
                <MiniBarChart
                  title="Explainability Summary"
                  values={shapValues}
                  color="#ea580c"
                  filterZero
                  maxItems={5}
                  emptyMessage="No strong explainability signal was returned for this prediction."
                />
                <MiniBarChart
                  title="Model Feature Importances"
                  values={modelImportances}
                  color="#16a34a"
                  filterZero
                  maxItems={5}
                  emptyMessage="The trained model did not assign meaningful importance to these features."
                />
              </section>

              <section
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                  gap: "1rem",
                }}
              >
                <TrendChart title="Temperature Trend" points={temperatureHistory} color="#ef4444" />
                <TrendChart title="Rainfall Trend" points={precipitationHistory} color="#3b82f6" />
                <TrendChart title="Soil Moisture Trend" points={soilMoistureHistory} color="#14b8a6" />
                <TrendChart title="Vegetation Proxy Trend" points={vegetationHistory} color="#22c55e" />
              </section>

            </>
          )}

          {brief && (
            <section
              style={{
                border: "1px solid rgba(148,163,184,0.14)",
                borderRadius: "22px",
                padding: "1.15rem",
                background: "linear-gradient(135deg, rgba(12,21,38,0.96) 0%, rgba(8,17,31,0.98) 100%)",
                boxShadow: "0 18px 32px rgba(2, 6, 23, 0.24)",
                color: "#e2e8f0",
              }}
            >
              <h3 style={{ marginTop: 0, color: "#f8fafc" }}>Intervention Brief</h3>
              <div style={{ display: "grid", gap: "0.9rem" }}>
                <div>
                  <div style={{ fontWeight: 800, color: "#7dd3fc", marginBottom: "0.45rem" }}>Summary</div>
                  {renderSentenceBullets(brief.summary, "#dbeafe")}
                </div>
                <div>
                  <div style={{ fontWeight: 800, color: "#7dd3fc", marginBottom: "0.45rem" }}>Suggested Action</div>
                  {renderSentenceBullets(brief.suggested_action, "#dbeafe")}
                </div>
                <div>
                  <div style={{ fontWeight: 800, color: "#94a3b8", marginBottom: "0.45rem" }}>Caution</div>
                  {renderSentenceBullets(brief.caution_note, "#94a3b8")}
                </div>
              </div>
            </section>
          )}

          {scenario && (
            <section
              style={{
                border: "1px solid rgba(148,163,184,0.14)",
                borderRadius: "22px",
                padding: "1.15rem",
                background: "linear-gradient(135deg, rgba(12,21,38,0.96) 0%, rgba(8,17,31,0.98) 100%)",
                boxShadow: "0 18px 32px rgba(2, 6, 23, 0.24)",
                color: "#e2e8f0",
              }}
            >
              <h3 style={{ marginTop: 0, color: "#f8fafc" }}>Scenario Analysis</h3>
              <p style={{ color: "#dbeafe", lineHeight: 1.7 }}><strong>Scenario:</strong> {scenario.scenario}</p>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem", marginBottom: "1rem" }}>
                <div style={{ padding: "0.9rem", borderRadius: "14px", background: "rgba(15,23,42,0.46)", border: "1px solid rgba(148,163,184,0.18)" }}>
                  <div style={{ color: "#7dd3fc", fontSize: "0.82rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>Current</div>
                  <div style={{ marginTop: "0.3rem", fontSize: "1.1rem", fontWeight: 700, color: getRiskColor(scenario.original_risk.risk_level) }}>
                    {formatRiskLevel(scenario.original_risk.risk_level)}
                  </div>
                  <div style={{ color: "#cbd5e1", marginTop: "0.25rem" }}>Confidence: {Math.round(scenario.original_risk.confidence * 100)}%</div>
                  <div style={{ color: "#cbd5e1" }}>Score: {scenario.original_risk.score.toFixed(3)}</div>
                </div>
                <div style={{ padding: "0.9rem", borderRadius: "14px", background: "rgba(15,23,42,0.46)", border: "1px solid rgba(148,163,184,0.18)" }}>
                  <div style={{ color: "#7dd3fc", fontSize: "0.82rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>Rainfall Shock</div>
                  <div style={{ marginTop: "0.3rem", fontSize: "1.1rem", fontWeight: 700, color: getRiskColor(scenario.simulated_risk.risk_level) }}>
                    {formatRiskLevel(scenario.simulated_risk.risk_level)}
                  </div>
                  <div style={{ color: "#cbd5e1", marginTop: "0.25rem" }}>Confidence: {Math.round(scenario.simulated_risk.confidence * 100)}%</div>
                  <div style={{ color: "#cbd5e1" }}>Score: {scenario.simulated_risk.score.toFixed(3)}</div>
                </div>
              </div>
              <div style={{ display: "grid", gap: "0.9rem" }}>
                <div>
                  <div style={{ fontWeight: 800, color: "#7dd3fc", marginBottom: "0.45rem" }}>Summary</div>
                  {renderSentenceBullets(scenario.brief.summary, "#dbeafe")}
                </div>
                <div>
                  <div style={{ fontWeight: 800, color: "#7dd3fc", marginBottom: "0.45rem" }}>Suggested Action</div>
                  {renderSentenceBullets(scenario.brief.suggested_action, "#dbeafe")}
                </div>
                <div>
                  <div style={{ fontWeight: 800, color: "#94a3b8", marginBottom: "0.45rem" }}>Caution</div>
                  {renderSentenceBullets(scenario.brief.caution_note, "#94a3b8")}
                </div>
              </div>
            </section>
          )}

          {forecast && forecast.length > 0 && (
            <section
              style={{
                border: "1px solid rgba(148,163,184,0.14)",
                borderRadius: "22px",
                padding: "1.15rem",
                background: "linear-gradient(135deg, rgba(12,21,38,0.96) 0%, rgba(8,17,31,0.98) 100%)",
                boxShadow: "0 18px 32px rgba(2, 6, 23, 0.24)",
                color: "#e2e8f0",
              }}
            >
              <h3 style={{ marginTop: 0, color: "#f8fafc" }}>Risk Forecast</h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem" }}>
                {forecast.map((f) => (
                  <div key={f.horizon_days} style={{ padding: "0.85rem", border: "1px solid rgba(148,163,184,0.18)", borderRadius: "14px", background: "rgba(15,23,42,0.46)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: "0.75rem", alignItems: "center" }}>
                      <div style={{ fontSize: "0.9rem", color: "#7dd3fc", fontWeight: 700 }}>{f.horizon_days} Days</div>
                      <span
                        style={{
                          ...getRiskBadgeStyle(f.risk_level),
                          padding: "0.28rem 0.6rem",
                          borderRadius: "999px",
                          fontSize: "0.78rem",
                          fontWeight: 800,
                          textTransform: "uppercase",
                          letterSpacing: "0.06em",
                        }}
                      >
                        {formatRiskLevel(f.risk_level)}
                      </span>
                    </div>
                    <div style={{ fontSize: "0.8rem", color: "#cbd5e1", marginTop: "0.25rem" }}>
                      Confidence: {Math.round(f.confidence * 100)}%
                    </div>
                    <div style={{ fontSize: "0.8rem", color: "#cbd5e1" }}>
                      Confidence band: {f.confidence_band}
                    </div>
                    <div style={{ fontSize: "0.8rem", color: "#cbd5e1" }}>
                      Score: {f.score.toFixed(3)}
                    </div>
                    <div style={{ fontSize: "0.8rem", color: "#94a3b8", marginTop: "0.4rem", lineHeight: 1.5 }}>
                      {f.reasoning}
                    </div>
                  </div>
                ))}
              </div>
              <p style={{ marginTop: "1rem", color: "#94a3b8", fontSize: "0.9rem" }}>
                Forecast based on trend projections of precipitation and temperature patterns.
              </p>
            </section>
          )}

          {feedbackSummary && (
            <section
              style={{
                border: "1px solid rgba(34,197,94,0.18)",
                borderRadius: "20px",
                padding: "1rem",
                background: "rgba(240,253,244,0.08)",
                color: "#e2e8f0",
              }}
            >
              <h3 style={{ marginTop: 0, color: "#dcfce7" }}>Feedback Loop Dashboard</h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "0.85rem" }}>
                <div style={{ padding: "0.85rem", borderRadius: "14px", background: "rgba(15,23,42,0.46)", border: "1px solid rgba(148,163,184,0.18)" }}>
                  <div style={{ color: "#86efac", fontSize: "0.82rem", textTransform: "uppercase" }}>Total Feedback</div>
                  <div style={{ color: "#f8fafc", fontSize: "1.3rem", fontWeight: 800 }}>{feedbackSummary.total_feedback}</div>
                </div>
                <div style={{ padding: "0.85rem", borderRadius: "14px", background: "rgba(15,23,42,0.46)", border: "1px solid rgba(148,163,184,0.18)" }}>
                  <div style={{ color: "#86efac", fontSize: "0.82rem", textTransform: "uppercase" }}>Model Match Rate</div>
                  <div style={{ color: "#f8fafc", fontSize: "1.3rem", fontWeight: 800 }}>
                    {feedbackSummary.match_rate === null ? "N/A" : `${Math.round(feedbackSummary.match_rate * 100)}%`}
                  </div>
                </div>
                <div style={{ padding: "0.85rem", borderRadius: "14px", background: "rgba(15,23,42,0.46)", border: "1px solid rgba(148,163,184,0.18)" }}>
                  <div style={{ color: "#86efac", fontSize: "0.82rem", textTransform: "uppercase" }}>Latest Observation</div>
                  <div style={{ color: "#f8fafc", fontSize: "1.1rem", fontWeight: 800 }}>
                    {feedbackSummary.latest_observation ? formatRiskLevel(feedbackSummary.latest_observation) : "No submissions"}
                  </div>
                </div>
              </div>
              <p style={{ color: "#bbf7d0", marginTop: "0.9rem", marginBottom: "0.4rem" }}>
                This shows how participatory field feedback compares with the current model prediction for the selected region.
              </p>
              <p style={{ color: "#94a3b8", margin: 0 }}>
                Breakdown: {Object.entries(feedbackSummary.observer_breakdown).map(([key, value]) => `${key} ${value}`).join(" | ")}
              </p>
            </section>
          )}

          {selectedLocation && (
            <details
              style={{
                border: "1px solid rgba(34,197,94,0.24)",
                borderRadius: "20px",
                padding: "1rem",
                backgroundColor: "rgba(220,252,231,0.08)",
                boxShadow: "0 14px 28px rgba(34, 197, 94, 0.08)",
                color: "#e2e8f0",
              }}
            >
              <summary style={{ cursor: "pointer", fontWeight: 700, color: "#f8fafc" }}>Submit Ground Truth Feedback</summary>
              <form onSubmit={submitFeedback} style={{ marginTop: "1rem" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "1rem" }}>
                  <div>
                    <label style={{ display: "block", marginBottom: "0.5rem", color: "#f8fafc", fontSize: "0.9rem" }}>
                      Observed Crop Stress Level
                    </label>
                    <select
                      name="observed_crop_stress"
                      required
                      style={{
                        width: "100%",
                        padding: "0.5rem",
                        borderRadius: "8px",
                        border: "1px solid rgba(148,163,184,0.25)",
                        background: "rgba(255,255,255,0.06)",
                        color: "#f8fafc",
                      }}
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="unknown">Unknown</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ display: "block", marginBottom: "0.5rem", color: "#f8fafc", fontSize: "0.9rem" }}>
                      Your Confidence (0-1)
                    </label>
                    <input
                      type="number"
                      name="confidence"
                      min="0"
                      max="1"
                      step="0.1"
                      defaultValue="0.8"
                      required
                      style={{
                        width: "100%",
                        padding: "0.5rem",
                        borderRadius: "8px",
                        border: "1px solid rgba(148,163,184,0.25)",
                        background: "rgba(255,255,255,0.06)",
                        color: "#f8fafc",
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ display: "block", marginBottom: "0.5rem", color: "#f8fafc", fontSize: "0.9rem" }}>
                      Observer Type
                    </label>
                    <select
                      name="observer_type"
                      required
                      style={{
                        width: "100%",
                        padding: "0.5rem",
                        borderRadius: "8px",
                        border: "1px solid rgba(148,163,184,0.25)",
                        background: "rgba(255,255,255,0.06)",
                        color: "#f8fafc",
                      }}
                    >
                      <option value="farmer">Farmer</option>
                      <option value="extension_worker">Extension Worker</option>
                      <option value="researcher">Researcher</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                </div>
                <div style={{ marginBottom: "1rem" }}>
                  <label style={{ display: "block", marginBottom: "0.5rem", color: "#f8fafc", fontSize: "0.9rem" }}>
                    Notes (Optional)
                  </label>
                  <textarea
                    name="notes"
                    placeholder="Describe what you observed..."
                    style={{
                      width: "100%",
                      padding: "0.5rem",
                      borderRadius: "8px",
                      border: "1px solid rgba(148,163,184,0.25)",
                      background: "rgba(255,255,255,0.06)",
                      color: "#f8fafc",
                      minHeight: "60px",
                      resize: "vertical",
                    }}
                  />
                </div>
                <button
                  type="submit"
                  disabled={isSubmittingFeedback}
                  style={{
                    padding: "0.75rem 1.5rem",
                    cursor: "pointer",
                    borderRadius: "999px",
                    border: "1px solid rgba(34,197,94,0.25)",
                    background: "#16a34a",
                    color: "#f0fdf4",
                    fontWeight: 700,
                  }}
                >
                  {isSubmittingFeedback ? "Submitting..." : "Submit Feedback"}
                </button>
              </form>
              {feedbackResponse && (
                <div style={{ marginTop: "1rem", padding: "1rem", borderRadius: "8px", background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.2)" }}>
                  <p style={{ margin: 0, color: "#bbf7d0", fontWeight: 700 }}>Feedback Submitted!</p>
                  <p style={{ margin: "0.5rem 0 0", color: "#bbf7d0", fontSize: "0.9rem" }}>{feedbackResponse.message}</p>
                </div>
              )}
            </details>
          )}

          {error && (
            <p
              style={{
                color: "#fecaca",
                border: "1px solid rgba(248,113,113,0.22)",
                background: "rgba(127,29,29,0.22)",
                borderRadius: "14px",
                padding: "0.85rem 1rem",
                margin: 0,
              }}
            >
              {error}
            </p>
          )}
        </div>
      </div>
    </main>
  );
}
