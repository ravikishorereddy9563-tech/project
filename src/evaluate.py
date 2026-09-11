"""Evaluation harness with deterministic metrics and optional LLM judge labels."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

from .agent import SupportAgent, load_threads
from .baselines import evaluate_baselines


def overlap_score(reply: str, reference: str) -> float:
    words = lambda text: set(re.findall(r"[a-z0-9]+", text.lower()))
    expected = words(reference)
    return round(len(words(reply) & expected) / max(1, len(expected)), 3)


def validate_real_golden(golden: pd.DataFrame, min_rows: int = 150) -> None:
    required = {"id", "text", "intent", "escalate", "reference_reply"}
    missing = required.difference(golden.columns)
    if missing:
        raise ValueError(f"Real golden set is missing required columns: {sorted(missing)}")
    if golden.empty:
        raise ValueError("Real golden set is empty; label at least one real example before evaluation.")

    blank_mask = golden["intent"].isna() | golden["escalate"].isna() | golden["reference_reply"].isna()
    blank_mask |= golden["intent"].astype(str).str.strip().eq("")
    blank_mask |= golden["reference_reply"].astype(str).str.strip().eq("")
    if blank_mask.any():
        raise ValueError("Real golden set is not fully labeled: fill in intent, escalate, and reference_reply for every row before evaluation.")
    if len(golden) < min_rows:
        raise ValueError(f"Real golden set is too small; label at least {min_rows} examples before publishing headline metrics.")


def build_failure_analysis(rows: list[dict]) -> list[dict]:
    failures = []
    for row in rows:
        expected_intent = row.get("expected_intent")
        predicted_intent = row.get("predicted_intent")
        expected_escalation = bool(row.get("expected_escalation", False))
        predicted_escalation = bool(row.get("predicted_escalation", False))

        if expected_intent == "other_or_unknown" or predicted_intent == "other_or_unknown":
            category = "ambiguous_intent"
            reason = "The message is ambiguous enough that the intent routing should have been clarified or sent to a human review path."
        elif not row.get("escalation_correct", True):
            category = "escalation_policy_gap"
            reason = (
                "The agent reached the right intent but chose the wrong escalation policy for a payment, order, "
                "repair, or privacy-sensitive outcome."
            )
        elif expected_intent != predicted_intent:
            category = "wrong_intent_classification"
            reason = "The retrieved evidence or intent rules selected the wrong operating class for this customer issue."
        else:
            category = "grounding_gap"
            reason = "The response was plausible but unsupported by the historical evidence or failed to address the key issue."

        failures.append(
            {
                "id": row.get("id"),
                "category": category,
                "reason": reason,
                "text": row.get("text"),
                "expected_intent": expected_intent,
                "predicted_intent": predicted_intent,
                "expected_escalation": expected_escalation,
                "predicted_escalation": predicted_escalation,
                "reply": row.get("reply"),
                "evidence_tweet_id": row.get("evidence_tweet_id"),
            }
        )
    return failures


def evaluate(agent: SupportAgent, golden: pd.DataFrame) -> tuple[dict, list[dict], list[dict]]:
    validate_real_golden(golden)
    rows = []
    judge_rows = []
    for _, example in golden.iterrows():
        result = agent.run(example["text"])
        evidence = agent.retrieve_top(example["text"], result.intent, limit=3)
        rows.append({"id": example["id"], "text": example["text"], "expected_intent": example["intent"], "predicted_intent": result.intent,
                     "intent_correct": result.intent == example["intent"],
                     "expected_escalation": bool(example["escalate"]), "predicted_escalation": result.escalation,
                     "escalation_correct": result.escalation == bool(example["escalate"]),
                     "groundedness": overlap_score(result.reply, example["reference_reply"]),
                     "reply": result.reply, "evidence_tweet_id": result.evidence_tweet_id})
        judge_rows.append({"id": example["id"], "text": example["text"], "reply": result.reply,
                           "evidence": "\n".join(case["text"] for case, _ in evidence)})
    result = pd.DataFrame(rows)
    from sklearn.metrics import precision_score, recall_score
    intent_report = _intent_report(result.expected_intent, result.predicted_intent)
    escalation_expected = result.expected_escalation.astype(int)
    escalation_predicted = result.predicted_escalation.astype(int)
    return ({"n": len(result), "intent_accuracy": round(result.intent_correct.mean(), 3),
            "intent_macro_f1": _macro_f1(result.expected_intent, result.predicted_intent),
            "intent_per_class": intent_report,
            "intent_confusion_matrix": pd.crosstab(result.expected_intent, result.predicted_intent).to_dict(),
            "escalation_accuracy": round(result.escalation_correct.mean(), 3),
            "escalation_precision": round(precision_score(escalation_expected, escalation_predicted, zero_division=0), 3),
            "escalation_recall": round(recall_score(escalation_expected, escalation_predicted, zero_division=0), 3),
            "mean_groundedness_token_overlap": round(result.groundedness.mean(), 3),
            "escalation_confusion_matrix": pd.crosstab(result.expected_escalation, result.predicted_escalation).to_dict()}, judge_rows, result.to_dict(orient="records"))


def _macro_f1(expected, predicted) -> float:
    from sklearn.metrics import f1_score
    return round(f1_score(expected, predicted, average="macro", zero_division=0), 3)


def _intent_report(expected, predicted) -> dict:
    from sklearn.metrics import precision_recall_fscore_support
    labels = sorted(set(expected) | set(predicted))
    precision, recall, f1, support = precision_recall_fscore_support(expected, predicted, labels=labels, zero_division=0)
    return {label: {"precision": round(float(p), 3), "recall": round(float(r), 3), "f1": round(float(score), 3), "support": int(count)}
            for label, p, r, score, count in zip(labels, precision, recall, f1, support)}


def judge_agreement(path: str) -> dict:
    labels = pd.read_csv(path)
    if {"human_label", "judge_label"}.difference(labels.columns):
        raise ValueError("Judge labels file must include human_label and judge_label columns.")
    human = pd.to_numeric(labels["human_label"], errors="coerce")
    judge = pd.to_numeric(labels["judge_label"], errors="coerce")
    if human.isna().any() or judge.isna().any():
        raise ValueError("Judge-label audit must use binary 0/1 values for human_label and judge_label.")
    from sklearn.metrics import cohen_kappa_score
    agreement = {"n": len(labels), "exact_agreement": round((human == judge).mean(), 3),
                 "cohen_kappa": round(cohen_kappa_score(human, judge), 3),
                 "human_positive_rate": round(human.mean(), 3), "judge_positive_rate": round(judge.mean(), 3)}
    if len(labels) < 30:
        agreement["sample_size_warning"] = "Judge-human validation is still too small for production confidence; expand to at least 30 labeled comparisons."
    return agreement


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", default="data/sample_threads.csv")
    parser.add_argument("--golden", default="data/golden_real.csv")
    parser.add_argument("--judge-labels", default="data/judge_labels.csv")
    parser.add_argument("--out", default="outputs/metrics.json")
    parser.add_argument("--judge-input", default="outputs/judge_input.json")
    parser.add_argument("--failures-out", default="outputs/failures.json")
    args = parser.parse_args()
    golden = pd.read_csv(args.golden)
    report, judge_rows, prediction_rows = evaluate(SupportAgent(load_threads(args.threads)), golden)
    report["baselines"] = evaluate_baselines(load_threads(args.threads), golden)
    report["judge_human_agreement"] = judge_agreement(args.judge_labels)
    Path(args.out).parent.mkdir(exist_ok=True)
    Path(args.judge_input).write_text(json.dumps(judge_rows, indent=2), encoding="utf-8")
    failure_rows = build_failure_analysis([row for row in prediction_rows if not row["intent_correct"] or not row["escalation_correct"]])
    Path(args.failures_out).write_text(json.dumps(failure_rows, indent=2), encoding="utf-8")
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
