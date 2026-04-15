from pathlib import Path
from typing import Any, Dict, Optional, TypedDict

from dotenv import load_dotenv

from backend.app.agents.response_agent import generate_brief, qa_check_response
from backend.app.services.agent_service import generate_region_brief, generate_scenario_brief, run_region_analysis
from backend.app.services.workflow_store import load_workflow_history, save_workflow_event

load_dotenv()

LANGGRAPH_DB_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"

try:
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, START, StateGraph

    LANGGRAPH_AVAILABLE = True
except Exception:
    MemorySaver = None
    END = None
    START = None
    StateGraph = None
    LANGGRAPH_AVAILABLE = False


class WorkflowState(TypedDict, total=False):
    session_id: str
    region: Dict[str, Any]
    rainfall_reduction: Optional[float]
    audience: str
    analysis: Dict[str, Any]
    scenario_output: Dict[str, Any]
    draft_brief: Dict[str, str]
    approved_brief: Dict[str, str]
    handoff_path: list[str]
    trace_notes: list[str]


def _fallback_workflow(
    region: Dict[str, Any],
    session_id: str,
    rainfall_reduction: Optional[float] = None,
    audience: str = "ngo",
) -> Dict[str, Any]:
    if rainfall_reduction is None:
        result = generate_region_brief(region, audience=audience)
        brief = result["brief"]
        trace_notes = [
            "Fallback orchestrator used because LangGraph is unavailable.",
            "Response Planning Agent and QA Agent were run through the shared OpenAI-backed brief service.",
        ]
    else:
        result = generate_scenario_brief(region, rainfall_reduction, audience=audience)
        brief = result["brief"]
        trace_notes = [
            "Fallback orchestrator used because LangGraph is unavailable.",
            f"Scenario simulation applied with rainfall reduction of {rainfall_reduction}%.",
        ]

    return {
        "region_id": region["id"],
        "session_id": session_id,
        "mode": "fallback",
        "brief": {
            "region_id": region["id"],
            "summary": brief["summary"],
            "suggested_action": brief["suggested_action"],
            "caution_note": brief["caution_note"],
        },
        "handoff_path": ["analysis_service", "response_agent", "qa_agent"],
        "trace_notes": trace_notes,
    }


def _analysis_node(state: WorkflowState) -> WorkflowState:
    region = state["region"]
    rainfall_reduction = state.get("rainfall_reduction")

    if rainfall_reduction is None:
        analysis = run_region_analysis(region)
        save_workflow_event(state["session_id"], "analysis", {"risk_level": analysis["risk_record"]["risk_level"]})
        return {
            "analysis": analysis,
            "handoff_path": ["analysis_service"],
            "trace_notes": ["Region analysis completed from weather, geospatial, and model layers."],
        }

    scenario_output = generate_scenario_brief(region, rainfall_reduction, audience=state.get("audience", "ngo"))
    save_workflow_event(state["session_id"], "scenario_analysis", {"rainfall_reduction": rainfall_reduction})
    return {
        "analysis": scenario_output["analysis"],
        "scenario_output": scenario_output,
        "handoff_path": ["analysis_service", "scenario_service"],
        "trace_notes": [f"Scenario analysis completed with rainfall reduction of {rainfall_reduction}%."],
    }


def _planning_node(state: WorkflowState) -> WorkflowState:
    region = state["region"]
    scenario_output = state.get("scenario_output")

    if scenario_output is None:
        draft = generate_brief(
            region["name"],
            state["analysis"]["risk_record"],
            state["analysis"]["evidence_packet"],
            audience=state.get("audience", "ngo"),
        )
    else:
        draft = generate_brief(
            region["name"],
            scenario_output["scenario_result"]["simulated_risk"],
            scenario_output["scenario_packet"],
            audience=state.get("audience", "ngo"),
        )
    save_workflow_event(state["session_id"], "planning", {"summary": draft.get("summary", "")})

    return {
        "draft_brief": draft,
        "handoff_path": state.get("handoff_path", []) + ["response_planning_agent"],
        "trace_notes": state.get("trace_notes", []) + ["Draft brief generated with OpenAI via LangChain-compatible LLM wrapper."],
    }


def _qa_node(state: WorkflowState) -> WorkflowState:
    scenario_output = state.get("scenario_output")
    evidence = scenario_output["scenario_packet"] if scenario_output is not None else state["analysis"]["evidence_packet"]
    approved = qa_check_response(state["draft_brief"], evidence)
    save_workflow_event(state["session_id"], "qa", approved)

    return {
        "approved_brief": approved,
        "handoff_path": state.get("handoff_path", []) + ["qa_guardrail_agent"],
        "trace_notes": state.get("trace_notes", []) + ["QA validation completed against the structured evidence packet."],
    }


def _run_langgraph_workflow(
    region: Dict[str, Any],
    session_id: str,
    rainfall_reduction: Optional[float] = None,
    audience: str = "ngo",
) -> Dict[str, Any]:
    LANGGRAPH_DB_DIR.mkdir(parents=True, exist_ok=True)

    graph = StateGraph(WorkflowState)
    graph.add_node("analysis", _analysis_node)
    graph.add_node("planning", _planning_node)
    graph.add_node("qa", _qa_node)
    graph.add_edge(START, "analysis")
    graph.add_edge("analysis", "planning")
    graph.add_edge("planning", "qa")
    graph.add_edge("qa", END)

    checkpointer = MemorySaver()
    workflow = graph.compile(checkpointer=checkpointer)
    final_state = workflow.invoke(
        {
            "session_id": session_id,
            "region": region,
            "rainfall_reduction": rainfall_reduction,
            "audience": audience,
        },
        config={"configurable": {"thread_id": session_id}},
    )
    approved = final_state["approved_brief"]
    history = load_workflow_history(session_id)

    return {
        "region_id": region["id"],
        "session_id": session_id,
        "mode": "langgraph",
        "brief": {
            "region_id": region["id"],
            "summary": approved["summary"],
            "suggested_action": approved["suggested_action"],
            "caution_note": approved["caution_note"],
        },
        "handoff_path": final_state.get("handoff_path", []),
        "trace_notes": final_state.get("trace_notes", []) + [
            "LangGraph state machine completed successfully.",
            f"Persisted workflow events: {len(history)}",
        ],
    }


def run_agent_workflow(
    region: Dict[str, Any],
    session_id: str,
    rainfall_reduction: Optional[float] = None,
    audience: str = "ngo",
) -> Dict[str, Any]:
    if not LANGGRAPH_AVAILABLE:
        return _fallback_workflow(region, session_id, rainfall_reduction=rainfall_reduction, audience=audience)

    try:
        return _run_langgraph_workflow(region, session_id, rainfall_reduction=rainfall_reduction, audience=audience)
    except Exception:
        return _fallback_workflow(region, session_id, rainfall_reduction=rainfall_reduction, audience=audience)
