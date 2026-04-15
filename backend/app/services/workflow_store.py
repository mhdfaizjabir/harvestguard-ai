import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


DB_PATH = Path(__file__).resolve().parents[3] / "data" / "processed" / "workflow_state.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS workflow_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feedback_id TEXT NOT NULL UNIQUE,
            region_id TEXT NOT NULL,
            feedback_data TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            processed INTEGER DEFAULT 0
        )
        """
    )
    return connection


def save_workflow_event(session_id: str, stage: str, payload: Dict[str, Any]) -> None:
    with _connect() as connection:
        connection.execute(
            "INSERT INTO workflow_events (session_id, stage, payload, created_at) VALUES (?, ?, ?, ?)",
            (
                session_id,
                stage,
                json.dumps(payload),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        connection.commit()


def load_workflow_history(session_id: str) -> List[Dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT stage, payload, created_at FROM workflow_events WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()

    return [
        {
            "stage": stage,
            "payload": json.loads(payload),
            "created_at": created_at,
        }
        for stage, payload, created_at in rows
    ]


def save_feedback_event(feedback_id: str, region_id: str, feedback_data: Dict[str, Any], submitted_at: str) -> None:
    with _connect() as connection:
        connection.execute(
            "INSERT INTO feedback_events (feedback_id, region_id, feedback_data, submitted_at) VALUES (?, ?, ?, ?)",
            (
                feedback_id,
                region_id,
                json.dumps(feedback_data),
                submitted_at,
            ),
        )
        connection.commit()


def load_feedback_events(limit: int = 100) -> List[Dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT feedback_id, region_id, feedback_data, submitted_at, processed FROM feedback_events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()

    return [
        {
            "feedback_id": feedback_id,
            "region_id": region_id,
            "feedback_data": json.loads(feedback_data),
            "submitted_at": submitted_at,
            "processed": bool(processed),
        }
        for feedback_id, region_id, feedback_data, submitted_at, processed in rows
    ]


def summarize_feedback_events(region_id: str, predicted_risk: str, limit: int = 200) -> Dict[str, Any]:
    events = [event for event in load_feedback_events(limit=limit) if event["region_id"] == region_id]
    observed_counts = {"low": 0, "medium": 0, "high": 0, "unknown": 0}

    for event in events:
        observed = str(event.get("feedback_data", {}).get("observed_crop_stress", "unknown"))
        if observed not in observed_counts:
            observed = "unknown"
        observed_counts[observed] += 1

    comparable = [event for event in events if event.get("feedback_data", {}).get("observed_crop_stress") in {"low", "medium", "high", "unknown"}]
    matches = [
        event for event in comparable
        if str(event.get("feedback_data", {}).get("observed_crop_stress", "unknown")) == predicted_risk
    ]

    latest = comparable[0] if comparable else None
    return {
        "region_id": region_id,
        "total_feedback": len(events),
        "match_count": len(matches),
        "match_rate": round(len(matches) / len(comparable), 2) if comparable else None,
        "predicted_risk": predicted_risk,
        "latest_observation": latest.get("feedback_data", {}).get("observed_crop_stress") if latest else None,
        "observer_breakdown": observed_counts,
    }
