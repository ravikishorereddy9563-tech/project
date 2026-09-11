"""Streamlit dashboard for the AppleSupport support agent."""
import json
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from src.agent import INTENTS, SupportAgent, load_threads
from src.database import DEFAULT_PATH, clear_cases, list_cases, save_case

ROOT = Path(__file__).parent
THREADS_PATH = ROOT / "data" / "sample_threads.csv"
METRICS_PATH = ROOT / "outputs" / "metrics.json"

EXAMPLE_MESSAGES = {
    "Delivery delay": "My order was supposed to arrive yesterday but I still have not received it.",
    "Apple Pay declined": "My Apple Pay was declined when I tried to pay.",
    "Battery draining": "My iPhone battery is draining very quickly after the update.",
    "AirPods connection": "My AirPods will not connect to my iPhone.",
    "Unknown issue": "I need help with a problem I cannot describe.",
}

st.set_page_config(page_title="AppleSupport AI Agent", page_icon="A", layout="wide")

@st.cache_resource
def get_agent() -> SupportAgent:
    return SupportAgent(load_threads(THREADS_PATH))

@st.cache_data
def get_metrics() -> dict:
    if not METRICS_PATH.exists():
        return {}
    return pd.read_json(METRICS_PATH, typ="series").to_dict()

@st.cache_data
def get_evaluation_rows() -> pd.DataFrame:
    golden_real_path = ROOT / "data" / "golden_real.csv"
    golden_smoke_path = ROOT / "data" / "golden.csv"
    selected_path = golden_real_path if golden_real_path.exists() else golden_smoke_path
    if not selected_path.exists():
        return pd.DataFrame()
    golden = pd.read_csv(selected_path)
    evaluation_agent = SupportAgent(load_threads(THREADS_PATH))
    rows = []
    for _, example in golden.iterrows():
        result = evaluation_agent.run(example["text"])
        rows.append({
            "id": example["id"],
            "text": example["text"],
            "expected_intent": example["intent"],
            "predicted_intent": result.intent,
            "intent_correct": result.intent == example["intent"],
            "expected_escalation": bool(example["escalate"]),
            "predicted_escalation": result.escalation,
            "escalation_correct": result.escalation == bool(example["escalate"]),
            "evidence_tweet_id": result.evidence_tweet_id,
        })
    return pd.DataFrame(rows)

agent = get_agent()
metrics = get_metrics()
evaluation_rows = get_evaluation_rows()

st.title("AppleSupport AI Agent")
st.caption("Classify, ground, and route customer-support messages using historical resolutions.")

if "case_history" not in st.session_state:
    st.session_state["case_history"] = list_cases(DEFAULT_PATH)

with st.sidebar:
    st.header("System")
    st.selectbox("Brand", [agent.brand], disabled=True)
    st.metric("Historical replies", len(agent.examples))
    st.metric("Supported intents", len(INTENTS) + 1)
    st.metric("Session cases", len(st.session_state["case_history"]))
    if st.button("Clear session history", width="stretch"):
        st.session_state["case_history"] = []
        st.session_state.pop("analysis", None)
        clear_cases(DEFAULT_PATH)
        st.rerun()
    st.caption("Offline demo using the committed fixture. No customer text leaves this app.")

agent_tab, overview_tab, history_tab, evaluation_tab, failures_tab = st.tabs([
    "Agent", "Overview", "Case history", "Evaluation", "Failure analysis"
])

with agent_tab:
    with st.form("analysis_form"):
        example_name = st.selectbox("Try an example", ["Custom message", *EXAMPLE_MESSAGES.keys()])
        message = st.text_area(
            "Customer message",
            value=EXAMPLE_MESSAGES.get(example_name, EXAMPLE_MESSAGES["Delivery delay"]),
            height=120,
        )
        analyze = st.form_submit_button("Analyze message", type="primary", width="stretch")

    if analyze:
        if not message.strip():
            st.warning("Enter a customer message first.")
        else:
            st.session_state["analysis"] = {
                "message": message.strip(),
                "result": agent.run(message.strip()),
            }
            result = st.session_state["analysis"]["result"]
            case = {
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "message": message.strip(),
                "intent": result.intent,
                "confidence": result.intent_confidence,
                "decision": "escalate" if result.escalation else "auto-handle",
                "escalation_reason": result.escalation_reason,
                "generation_mode": getattr(result, "generation_mode", "historical_retrieval"),
                "evidence_tweet_id": result.evidence_tweet_id,
                "draft_reply": result.reply,
                "reviewer_feedback": "Not reviewed",
                "retrieval_score": getattr(result, "retrieval_score", 0),
                "evidence_strength": getattr(result, "evidence_strength", "weak"),
                "clarification_needed": getattr(result, "clarification_needed", False),
                "latency_ms": getattr(result, "latency_ms", 0),
            }
            save_case(case, DEFAULT_PATH)
            st.session_state["case_history"] = list_cases(DEFAULT_PATH)

    analysis = st.session_state.get("analysis")
    if analysis:
        message = analysis["message"]
        result = analysis["result"]
        generation_mode = getattr(result, "generation_mode", "historical_retrieval")
        evidence = agent.retrieve_top(message, result.intent, limit=3)

        intent_col, confidence_col, decision_col = st.columns(3)
        intent_col.metric("Intent", result.intent.replace("_", " ").title(), border=True)
        confidence_col.metric("Classifier confidence", f"{result.intent_confidence:.2f}", border=True)
        confidence_col.caption("Uncalibrated model score")
        decision_col.metric(
            "Decision", "Escalate to human" if result.escalation else "Auto-handle", border=True
        )

        evidence_score_col, latency_col = st.columns(2)
        evidence_score_col.metric("Retrieval score", f"{getattr(result, 'retrieval_score', 0):.3f}", border=True)
        latency_col.metric("Total latency", f"{getattr(result, 'latency_ms', 0):.0f} ms", border=True)
        st.caption(f"Evidence strength: {getattr(result, 'evidence_strength', 'weak').title()} · confidence is an uncalibrated model score")

        if getattr(result, "clarification_needed", False):
            st.info("**Clarification recommended**  \nThe message is ambiguous, so the draft asks for product and issue details before routing.")

        if result.escalation:
            st.warning(f"**Decision: ESCALATE**  \n**Reason:** {result.escalation_reason}")
        else:
            st.success(f"**Decision: AUTO-HANDLE**  \n**Reason:** {result.escalation_reason}")

        reply_col, evidence_col = st.columns([1.1, 1])
        with reply_col:
            with st.container(border=True):
                st.subheader("Draft reply")
                edited_reply = st.text_area("Edit before sending", value=result.reply, height=140)
                st.caption(f"Grounded in historical agent reply {result.evidence_tweet_id}.")
                feedback_col, action_col = st.columns(2)
                with feedback_col:
                    feedback = st.selectbox("Reviewer feedback", ["Not reviewed", "Approved", "Needs revision"], key="feedback")
                with action_col:
                    st.download_button(
                        "Download decision",
                        data=json.dumps({
                            "customer_message": message,
                            "intent": result.intent,
                            "confidence": result.intent_confidence,
                            "escalate": result.escalation,
                            "escalation_reason": result.escalation_reason,
                            "draft_reply": edited_reply,
                            "evidence_tweet_id": result.evidence_tweet_id,
                            "generation_mode": generation_mode,
                            "reviewer_feedback": feedback,
                            "retrieval_score": getattr(result, "retrieval_score", 0),
                            "evidence_strength": getattr(result, "evidence_strength", "weak"),
                        }, indent=2),
                        file_name="support_decision.json",
                        mime="application/json",
                        width="stretch",
                    )
                if feedback == "Approved":
                    st.success("Reply marked approved for this review session.")
                elif feedback == "Needs revision":
                    st.info("Review the evidence and edit the draft before using it.")
        with evidence_col:
            with st.container(border=True):
                st.subheader("Historical evidence")
                for rank, (case, similarity) in enumerate(evidence, start=1):
                    with st.expander(f"Evidence {rank} · similarity {similarity:.0%}", expanded=rank == 1):
                        st.write(f"**Intent:** {result.intent.replace('_', ' ').title()}")
                        st.write(f"**Similarity:** {similarity:.3f}")
                        st.write(f"**Customer thread:** {case['thread_id']}")
                        st.write(f"**Historical resolution:** {case['text']}")
                        st.caption(f"Tweet ID: {case['tweet_id']}")
        with st.expander("Decision trace"):
            st.json({
                "brand": agent.brand,
                "customer_message": message,
                "intent": result.intent,
                "confidence": result.intent_confidence,
                "escalate": result.escalation,
                "reason": result.escalation_reason,
                "evidence_tweet_id": result.evidence_tweet_id,
                "generation_mode": generation_mode,
                "retrieval_score": getattr(result, "retrieval_score", 0),
                "evidence_strength": getattr(result, "evidence_strength", "weak"),
                "clarification_needed": getattr(result, "clarification_needed", False),
                "latency_ms": getattr(result, "latency_ms", 0),
            })
    else:
        st.info("Enter a message and select Analyze message to inspect the full decision trace.")

with overview_tab:
    st.subheader("System overview")
    metric_row = st.container(horizontal=True)
    with metric_row:
        metric_row.metric("Historical replies", len(agent.examples), border=True)
        metric_row.metric("Supported intents", len(INTENTS) + 1, border=True)
        metric_row.metric("Golden examples", len(evaluation_rows), border=True)
        metric_row.metric("Judge agreement", f"{metrics.get('judge_human_agreement', {}).get('exact_agreement', 0):.0%}", border=True)

    if evaluation_rows.empty:
        st.warning("Run `python -m src.evaluate` to generate evaluation data.")
    else:
        intent_counts = evaluation_rows["predicted_intent"].value_counts().rename_axis("intent").reset_index(name="messages")
        st.subheader("Intent distribution")
        st.bar_chart(intent_counts, x="intent", y="messages")
        st.caption("Counts are calculated from the committed golden evaluation set, not fabricated dashboard values.")

with history_tab:
    st.subheader("Session case history")
    history = pd.DataFrame(st.session_state["case_history"])
    if history.empty:
        st.info("Analyze messages in the Agent tab to build a reviewable case history.")
    else:
        auto_count = int((history["decision"] == "auto-handle").sum())
        escalate_count = int((history["decision"] == "escalate").sum())
        history_col, auto_col, escalation_col = st.columns(3)
        history_col.metric("Analyzed cases", len(history), border=True)
        auto_col.metric("Auto-handled", auto_count, border=True)
        escalation_col.metric("Escalated", escalate_count, border=True)
        st.dataframe(history, hide_index=True, width="stretch")
        st.download_button(
            "Download session audit CSV",
            data=history.to_csv(index=False),
            file_name="support_session_audit.csv",
            mime="text/csv",
            width="stretch",
        )

with evaluation_tab:
    st.subheader("Evaluation results")
    if metrics:
        metric_row = st.container(horizontal=True)
        with metric_row:
            metric_row.metric("Intent accuracy", f"{metrics.get('intent_accuracy', 0):.1%}", border=True)
            metric_row.metric("Intent macro-F1", f"{metrics.get('intent_macro_f1', 0):.1%}", border=True)
            metric_row.metric("Escalation accuracy", f"{metrics.get('escalation_accuracy', 0):.1%}", border=True)
            metric_row.metric("Escalation recall", f"{metrics.get('escalation_recall', 0):.1%}", border=True)
        st.caption("Headline metrics are only as trustworthy as the labeled golden set. The committed fixture is a smoke test, not real Kaggle evidence.")
        st.json(metrics)
    else:
        st.warning("Run `python -m src.evaluate` to generate evaluation metrics.")
    if not evaluation_rows.empty:
        st.subheader("Golden-set predictions")
        st.dataframe(
            evaluation_rows[["id", "text", "expected_intent", "predicted_intent", "intent_correct", "escalation_correct"]],
            hide_index=True,
            width="stretch",
        )

with failures_tab:
    st.subheader("Failure analysis")
    if evaluation_rows.empty:
        st.info("Generate the golden set and run evaluation first.")
    else:
        intent_failures = evaluation_rows[~evaluation_rows["intent_correct"]]
        escalation_failures = evaluation_rows[~evaluation_rows["escalation_correct"]]
        failure_col, escalation_col = st.columns(2)
        failure_col.metric("Intent failures", len(intent_failures), border=True)
        escalation_col.metric("Escalation failures", len(escalation_failures), border=True)
        if intent_failures.empty and escalation_failures.empty:
            st.success("No failures in the committed golden set.")
        else:
            st.write("Review the examples below to identify taxonomy, retrieval, or policy gaps.")
            if not intent_failures.empty:
                st.write("**Intent failures**")
                st.dataframe(intent_failures, hide_index=True, width="stretch")
            if not escalation_failures.empty:
                st.write("**Escalation failures**")
                st.dataframe(escalation_failures, hide_index=True, width="stretch")
