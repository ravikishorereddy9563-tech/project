"""Offline AppleSupport agent: intent, grounded draft, and escalation decision."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .generation import generate_reply

INTENTS = {
    "battery_or_performance": ["battery", "draining", "overheating", "slow", "shutting down"],
    "purchase_or_duplicate_charge": ["charged twice", "duplicate", "purchase", "subscription", "refund"],
    "device_or_accessory_setup": ["airpods", "connect", "pair", "transfer photos", "quick start"],
    "account_access": ["password", "apple id", "sign in", "locked out", "forgot", "account"],
    "order_or_delivery": ["order", "arrived", "tracking", "shipping address", "delivery"],
    "repair_or_damage": ["cracked", "screen", "repair", "broken", "damage"],
    "payments": ["apple pay", "declined", "card", "billing"],
    "storage_or_cloud": ["icloud", "storage", "backup", "photos"],
    "trade_in": ["trade-in", "trade in", "credit"],
}

@dataclass
class AgentResult:
    intent: str
    intent_confidence: float
    reply: str
    escalation: bool
    escalation_reason: str
    evidence_tweet_id: str
    generation_mode: str = "historical_retrieval"
    retrieval_score: float = 0.0
    evidence_strength: str = "weak"
    clarification_needed: bool = False
    redacted_message: str = ""
    latency_ms: float = 0.0

class SupportAgent:
    def __init__(self, threads: pd.DataFrame, brand: str = "AppleSupport") -> None:
        self.brand = brand
        data = threads[threads["brand"].eq(brand)].copy()
        thread_intents = {}
        for thread_id, thread in data.groupby("thread_id"):
            customer_text = " ".join(thread.loc[thread["author_role"].eq("customer"), "text"])
            thread_intents[thread_id] = self.classify(customer_text)[0]
        self.examples = data[data["author_role"].eq("agent")].reset_index(drop=True)
        self.examples["intent"] = self.examples["thread_id"].map(thread_intents)
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        self.matrix = self.vectorizer.fit_transform(self.examples["text"].tolist())

    def classify(self, text: str) -> tuple[str, float]:
        normalized = text.lower()
        scores = {intent: sum(phrase in normalized for phrase in phrases) for intent, phrases in INTENTS.items()}
        intent, hits = max(scores.items(), key=lambda item: item[1])
        if hits == 0:
            return "other_or_unknown", 0.20
        total = sum(scores.values()) or 1
        confidence = min(0.98, 0.55 + (hits / total) * 0.4)
        return intent, round(confidence, 2)

    def retrieve(self, text: str, intent: str) -> tuple[pd.Series, float]:
        return self.retrieve_top(text, intent, limit=1)[0]

    def retrieve_top(self, text: str, intent: str, limit: int = 3) -> list[tuple[pd.Series, float]]:
        query = self.vectorizer.transform([text])
        candidate_indexes = self.examples.index[self.examples["intent"].eq(intent)].tolist()
        if not candidate_indexes:
            candidate_indexes = self.examples.index.tolist()
        similarities = cosine_similarity(query, self.matrix[candidate_indexes])[0]
        ranked = sorted(zip(candidate_indexes, similarities), key=lambda item: item[1], reverse=True)[:limit]
        return [(self.examples.iloc[index], float(similarity)) for index, similarity in ranked]

    def run(self, text: str) -> AgentResult:
        started = time.perf_counter()
        safe_text = redact_pii(text)
        intent, confidence = self.classify(safe_text)
        ranked_evidence = self.retrieve_top(safe_text, intent, limit=3)
        evidence, similarity = ranked_evidence[0]
        fallback = self._grounded_reply(intent, evidence["text"])
        reply, generation_mode = generate_reply(
            safe_text, intent, [case["text"] for case, _ in ranked_evidence], fallback
        )
        clarification_needed = intent == "other_or_unknown"
        escalation, reason = self._escalation(safe_text, intent, confidence, similarity)
        return AgentResult(
            intent, confidence, reply, escalation, reason, str(evidence["tweet_id"]), generation_mode,
            round(similarity, 3), evidence_strength(similarity), clarification_needed, safe_text,
            round((time.perf_counter() - started) * 1000, 2),
        )

    @staticmethod
    def _grounded_reply(intent: str, historical_reply: str) -> str:
        if intent == "other_or_unknown":
            return "Could you tell us which product is affected and whether the issue is with charging, signing in, payment, delivery, or setup?"
        return historical_reply

    @staticmethod
    def _escalation(text: str, intent: str, confidence: float, similarity: float) -> tuple[bool, str]:
        normalized = text.lower()
        if any(word in normalized for word in ("stolen", "fraud", "hacked", "unsafe", "lawsuit")):
            return True, "Potential security, safety, or legal issue requires a human."
        if intent in {"purchase_or_duplicate_charge", "payments", "order_or_delivery", "repair_or_damage"}:
            return True, "The issue may require account, payment, order, or repair details in a private channel."
        if confidence < 0.6 or similarity < 0.12:
            return True, "Low model confidence or weak historical evidence."
        return False, "Routine troubleshooting with a close historical resolution."

def load_threads(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"tweet_id": str, "thread_id": str})


def redact_pii(text: str) -> str:
    """Remove common credentials and contact/payment identifiers before processing."""
    redacted = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL REDACTED]", text)
    redacted = re.sub(r"\b(?:\d[ -]*?){13,19}\b", "[CARD REDACTED]", redacted)
    redacted = re.sub(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b", "[PHONE REDACTED]", redacted)
    redacted = re.sub(r"(?i)\b(password|passcode|otp|one[- ]time code)\s*[:=]?\s*\S+", r"\1 [REDACTED]", redacted)
    return redacted


def evidence_strength(similarity: float) -> str:
    if similarity >= 0.45:
        return "strong"
    if similarity >= 0.2:
        return "moderate"
    return "weak"
