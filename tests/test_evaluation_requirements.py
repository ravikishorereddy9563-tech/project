import pandas as pd
import pytest

from src.evaluate import build_failure_analysis, validate_real_golden


def test_validate_real_golden_rejects_blank_labels():
    golden = pd.DataFrame(
        {
            "id": ["real-001", "real-002"],
            "text": ["battery issue", "payment issue"],
            "intent": [None, "payments"],
            "escalate": [False, None],
            "reference_reply": ["reply 1", "reply 2"],
        }
    )

    with pytest.raises(ValueError, match="labeled"):
        validate_real_golden(golden)


def test_failure_analysis_adds_named_failure_categories():
    rows = [
        {
            "id": "real-1",
            "text": "I need help with something weird",
            "expected_intent": "other_or_unknown",
            "predicted_intent": "battery_or_performance",
            "intent_correct": False,
            "expected_escalation": False,
            "predicted_escalation": False,
            "escalation_correct": True,
            "reply": "This is a battery reply",
            "evidence_tweet_id": "123",
        },
        {
            "id": "real-2",
            "text": "My Apple Pay keeps declining",
            "expected_intent": "payments",
            "predicted_intent": "payments",
            "intent_correct": True,
            "expected_escalation": True,
            "predicted_escalation": False,
            "escalation_correct": False,
            "reply": "No private details",
            "evidence_tweet_id": "456",
        },
    ]

    failure_rows = build_failure_analysis(rows)

    assert {item["category"] for item in failure_rows} == {"ambiguous_intent", "escalation_policy_gap"}
    assert all("reason" in item for item in failure_rows)
