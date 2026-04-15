import os
from typing import Any, Dict

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

try:
    from langchain_openai import ChatOpenAI

    LANGCHAIN_OPENAI_AVAILABLE = True
except Exception:
    ChatOpenAI = None
    LANGCHAIN_OPENAI_AVAILABLE = False

SYSTEM_PROMPT = """
You are the Response Planning Agent for HarvestGuard AI, a platform that provides early warning for crop stress and food insecurity risk.

Your role is to generate human-readable, evidence-based intervention briefs and summaries based on structured risk data.

Guidelines:
- Only use the provided evidence JSON - do not invent data
- Be confident but not overconfident; include uncertainty where appropriate
- Tailor language and recommendations to the requested audience
- Focus on actionable recommendations
- Keep summaries concise but comprehensive
- Always reference the evidence sources
- If evidence is incomplete, note that in the response
- Never contradict the supplied risk level, confidence, or model probability
- Treat model probability as a probability score, not as a textual risk label
- Do not say phrases like "low probability of 0.85" or "high probability of 0.12"
- Prefer describing the strongest active drivers and ignore zero-value or inactive signals

Output format: JSON with keys: summary, suggested_action, caution_note
"""

QA_SYSTEM_PROMPT = """
You are the QA / Guardrail Agent for HarvestGuard AI.

Your job is to verify that a generated response is grounded in the provided evidence packet.

Rules:
- do not add unsupported claims
- keep uncertainty language when evidence is incomplete or synthetic
- preserve the original structure: summary, suggested_action, caution_note
- correct overclaiming, but do not become vague
- mention that this is decision support rather than certainty where appropriate
- fix contradictions between numeric probabilities and textual wording
- ensure the audience framing matches the requested audience
"""


class BriefPayload(BaseModel):
    summary: str
    suggested_action: str
    caution_note: str


def _audience_guidance(audience: str) -> str:
    audience = (audience or "ngo").lower()
    if audience == "donor":
        return "Emphasize why support is justified, what should be funded first, and what near-term impact donor action could have."
    if audience == "school_feeding":
        return "Emphasize continuity of food access, procurement pressure, supply planning, and school feeding resilience."
    if audience == "field_ops":
        return "Emphasize field verification, operational next steps, rapid checks, and deployment priorities."
    return "Emphasize practical community response, partner coordination, and operational mitigation for NGO teams."


def _fallback_brief(region_name: str, risk_data: Dict[str, Any], audience: str) -> Dict[str, str]:
    risk_level = str(risk_data.get("risk_level", "unknown"))
    confidence = int(round(float(risk_data.get("confidence", 0.0)) * 100))
    drivers = [driver for driver in risk_data.get("top_drivers", []) if driver]
    driver_text = ", ".join(drivers[:3]) if drivers else "available environmental signals"

    action_by_audience = {
        "ngo": "Prioritize partner coordination, targeted farmer support, and local monitoring in the highest-stress areas.",
        "donor": "Prioritize flexible funding for rapid response, water-stress mitigation, and follow-up monitoring in the most exposed communities.",
        "school_feeding": "Review procurement resilience, identify backup sourcing options, and monitor any local supply stress that could affect meal continuity.",
        "field_ops": "Dispatch field teams for rapid verification, crop-condition checks, and moisture-related follow-up in the highest-risk pockets.",
    }

    caution_by_audience = {
        "ngo": "This is decision support, not a guarantee; validate conditions with local partners before committing resources.",
        "donor": "Use this as an evidence-backed prioritization aid and pair it with local validation before allocating funds.",
        "school_feeding": "Treat this as an early warning signal and verify local supply conditions before changing procurement plans.",
        "field_ops": "Use this to guide field prioritization, but confirm conditions on the ground before escalation.",
    }

    return {
        "summary": f"{region_name} is currently assessed at {risk_level} risk with {confidence}% confidence, driven mainly by {driver_text}.",
        "suggested_action": action_by_audience.get(audience, action_by_audience["ngo"]),
        "caution_note": caution_by_audience.get(audience, caution_by_audience["ngo"]),
    }


def _get_langchain_model():
    if not api_key or not LANGCHAIN_OPENAI_AVAILABLE:
        return None
    try:
        return ChatOpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0)
    except Exception:
        return None

def generate_brief(
    region_name: str,
    risk_data: Dict[str, Any],
    evidence: Dict[str, Any],
    audience: str = "ngo",
) -> Dict[str, str]:
    prompt = f"""
Region: {region_name}
Audience: {audience}
Risk Level: {risk_data.get('risk_level', 'unknown')}
Confidence: {risk_data.get('confidence', 0.0):.0%}
Top Drivers: {', '.join(risk_data.get('top_drivers', []))}
Evidence: {evidence}
Audience Guidance: {_audience_guidance(audience)}

Generate a brief intervention summary.
"""

    try:
        llm = _get_langchain_model()
        if llm is not None:
            structured_llm = llm.with_structured_output(BriefPayload)
            result = structured_llm.invoke(
                [
                    ("system", SYSTEM_PROMPT),
                    ("user", prompt),
                ]
            )
            return result.dict()

        if client is None:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        result = response.choices[0].message.content
        import json

        return json.loads(result)
    except Exception:
        return _fallback_brief(region_name, risk_data, audience)


def qa_check_response(brief: Dict[str, str], evidence: Dict[str, Any]) -> Dict[str, str]:
    """QA agent to ensure claims match evidence"""
    prompt = f"""
Check this brief against the evidence. Ensure no unsupported claims.

Brief: {brief}
Evidence: {evidence}

If valid, return the brief unchanged. If issues, correct them.
"""

    try:
        llm = _get_langchain_model()
        if llm is not None:
            structured_llm = llm.with_structured_output(BriefPayload)
            result = structured_llm.invoke(
                [
                    ("system", QA_SYSTEM_PROMPT),
                    ("user", prompt),
                ]
            )
            return result.dict()

        if client is None:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": QA_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        result = response.choices[0].message.content
        import json

        return json.loads(result)
    except:
        return brief
