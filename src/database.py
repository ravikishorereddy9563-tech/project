"""SQLite persistence for support decisions and reviewer audit history."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "support_agent.db"


def connect(path: str | Path = DEFAULT_PATH) -> sqlite3.Connection:
    database_path = Path(path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    initialize(connection)
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS historical_messages (
            tweet_id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL,
            brand TEXT NOT NULL,
            author_role TEXT NOT NULL,
            text TEXT NOT NULL
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS support_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            customer_message TEXT NOT NULL,
            intent TEXT NOT NULL,
            confidence REAL NOT NULL,
            decision TEXT NOT NULL,
            escalation_reason TEXT NOT NULL,
            draft_reply TEXT NOT NULL,
            evidence_tweet_id TEXT NOT NULL,
            generation_mode TEXT NOT NULL,
            reviewer_feedback TEXT NOT NULL DEFAULT 'Not reviewed'
        )
    """)
    existing_columns = {row[1] for row in connection.execute("PRAGMA table_info(support_cases)")}
    for name, definition in {
        "retrieval_score": "REAL NOT NULL DEFAULT 0",
        "evidence_strength": "TEXT NOT NULL DEFAULT 'weak'",
        "clarification_needed": "INTEGER NOT NULL DEFAULT 0",
        "latency_ms": "REAL NOT NULL DEFAULT 0",
    }.items():
        if name not in existing_columns:
            connection.execute(f"ALTER TABLE support_cases ADD COLUMN {name} {definition}")
    connection.commit()


def import_threads(input_path: str | Path, path: str | Path = DEFAULT_PATH) -> int:
    import csv
    rows = []
    with Path(input_path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"tweet_id", "thread_id", "brand", "author_role", "text"}
        if not required.issubset(reader.fieldnames or set()):
            raise ValueError(f"Historical CSV must contain: {sorted(required)}")
        for row in reader:
            rows.append((row["tweet_id"], row["thread_id"], row["brand"], row["author_role"], row["text"]))
            if len(rows) >= 5000:
                _insert_messages(rows, path)
                rows.clear()
    if rows:
        _insert_messages(rows, path)
    with connect(path) as connection:
        return int(connection.execute("SELECT COUNT(*) FROM historical_messages").fetchone()[0])


def _insert_messages(rows: list[tuple[str, str, str, str, str]], path: str | Path) -> None:
    with connect(path) as connection:
        connection.executemany("""
            INSERT OR REPLACE INTO historical_messages (tweet_id, thread_id, brand, author_role, text)
            VALUES (?, ?, ?, ?, ?)
        """, rows)
        connection.commit()


def save_case(case: dict[str, Any], path: str | Path = DEFAULT_PATH) -> int:
    with connect(path) as connection:
        cursor = connection.execute("""
            INSERT INTO support_cases (
                created_at, customer_message, intent, confidence, decision,
                escalation_reason, draft_reply, evidence_tweet_id,
                generation_mode, reviewer_feedback, retrieval_score,
                evidence_strength, clarification_needed, latency_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            case.get("timestamp"), case["message"], case["intent"], case["confidence"],
            case["decision"], case["escalation_reason"], case.get("draft_reply", ""),
            case["evidence_tweet_id"], case["generation_mode"], case.get("reviewer_feedback", "Not reviewed"),
            case.get("retrieval_score", 0), case.get("evidence_strength", "weak"),
            int(case.get("clarification_needed", False)), case.get("latency_ms", 0),
        ))
        connection.commit()
        return int(cursor.lastrowid)


def list_cases(path: str | Path = DEFAULT_PATH) -> list[dict[str, Any]]:
    with connect(path) as connection:
        rows = connection.execute("SELECT * FROM support_cases ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]


def clear_cases(path: str | Path = DEFAULT_PATH) -> None:
    with connect(path) as connection:
        connection.execute("DELETE FROM support_cases")
        connection.commit()


def import_json(input_path: str | Path, path: str | Path = DEFAULT_PATH) -> int:
    payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
    case = {
        "timestamp": payload.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "message": payload["customer_message"],
        "intent": payload["intent"],
        "confidence": payload["confidence"],
        "decision": "escalate" if payload["escalate"] else "auto-handle",
        "escalation_reason": payload.get("escalation_reason", ""),
        "draft_reply": payload.get("draft_reply", ""),
        "evidence_tweet_id": str(payload.get("evidence_tweet_id", "")),
        "generation_mode": payload.get("generation_mode", "historical_retrieval"),
        "reviewer_feedback": payload.get("reviewer_feedback", "Not reviewed"),
    }
    return save_case(case, path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize or import support-agent SQLite data")
    parser.add_argument("--db", default=str(DEFAULT_PATH))
    parser.add_argument("--import-json")
    parser.add_argument("--import-threads")
    args = parser.parse_args()
    if args.import_json:
        case_id = import_json(args.import_json, args.db)
        print(f"imported decision as case {case_id} into {args.db}")
    elif args.import_threads:
        count = import_threads(args.import_threads, args.db)
        print(f"imported {count} historical messages into {args.db}")
    else:
        connect(args.db).close()
        print(f"initialized {args.db}")
