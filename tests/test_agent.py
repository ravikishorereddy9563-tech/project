from src.agent import SupportAgent, load_threads


def test_battery_is_routine_and_grounded():
    result = SupportAgent(load_threads("data/sample_threads.csv")).run("My battery is draining after the update")
    assert result.intent == "battery_or_performance"
    assert result.escalation is False
    assert "Battery Health" in result.reply
    assert result.evidence_tweet_id == "2"


def test_payment_escalates():
    result = SupportAgent(load_threads("data/sample_threads.csv")).run("Apple Pay declined at checkout")
    assert result.intent == "payments"
    assert result.escalation is True
    assert "billing address" in result.reply
    assert result.evidence_tweet_id == "16"
