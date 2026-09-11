# AppleSupport AI Agent

A small, reproducible take-home implementation for the Hiver SDE Intern assignment. It classifies customer-support messages, retrieves a historically similar AppleSupport resolution, drafts a grounded reply, and decides whether to escalate with a stated reason.

## 15-minute reproduction

Requires Python 3.10+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m src.generate_golden
pytest -q
python -m src.evaluate --golden data/golden_real.csv
streamlit run app.py
```

The last command writes `outputs/metrics.json`. The bundled fixture in `data/golden.csv` is intentionally tiny and should be treated as a smoke-test benchmark only. Final headline metrics must be computed from a fully labeled real-data set in `data/golden_real.csv`; the construction and limitations are described in `REPORT.md`.

The evaluator also reports a majority-class baseline, a TF-IDF + Logistic Regression baseline, and macro-F1. These are smoke-test comparisons on the committed fixture, not evidence from the full Kaggle corpus.

## Run the browser demo

After installing the requirements, run `streamlit run app.py`. Streamlit will print a local URL, normally `http://localhost:8501`. Enter a message and select **Analyze message** to see the predicted intent, confidence, escalation decision, grounded reply, and top historical evidence. Run the evaluation command first if you want the metrics snapshot in the app.

The Agent tab also includes example messages for quick demos, a reviewer-editable draft, Approved/Needs revision feedback, and a Download decision button that exports the full decision trace as JSON. The Case history tab keeps an in-session audit trail across multiple messages and exports it as CSV. The Overview, Evaluation, and Failure analysis tabs expose aggregate behavior from the committed golden set.

## Local support database

The app persists analyzed cases in SQLite at `data/support_agent.db`. It stores the customer message, intent, confidence, escalation decision and reason, draft reply, evidence ID, generation mode, and reviewer feedback. The uploaded example decision can be imported with:

```powershell
python -m src.database --import-json path\to\support_decision.json
```

To initialize an empty database:

```powershell
python -m src.database
```

The **Case history** tab reads persisted rows, so cases remain available after restarting Streamlit. **Clear session history** removes the stored rows from the local database.

The database also contains the prepared Kaggle evidence corpus in `historical_messages` (205,436 rows: 106,860 agent messages and 98,576 customer messages).

Each decision trace now includes a retrieval score, qualitative evidence strength (`strong`, `moderate`, or `weak`), clarification-needed status for ambiguous messages, PII-redacted text processing, and total latency. The agent never asks for passwords, OTPs, full card numbers, or public credentials.

## Use the Kaggle dataset

1. Download the Customer Support on Twitter CSV from Kaggle: `thoughtvector/customer-support-on-twitter`.
2. Run the normalizer. For the official TWCS file, `author_id` identifies support brands, so `--brand AppleSupport` selects the AppleSupport account and linked customer messages:

```powershell
python -m src.prepare path\to\tweets.csv data/apple_threads.csv --brand AppleSupport
python -m src.database --import-threads data/apple_threads.csv
python -m src.evaluate --threads data/apple_threads.csv
```

The Kaggle export has changed column names across mirrors. `src.prepare` accepts common text and author-role column names and fails loudly when no text field is found. Inspect the resulting CSV before evaluation: real exports need thread-aware pairing of customer tweets with the next brand response.

To create the real blind-labeling sheet after preparation:

```powershell
python -m src.create_golden_template data/apple_threads.csv data/golden_real.csv --brand AppleSupport --size 200
```

A human must fill `intent`, `escalate`, `reference_reply`, and `annotator_notes` before using that file as evaluation input. Do not report metrics from blank or synthetic labels as real-data results. The current `data/golden_real.csv` is only an unlabeled template.

To prepare judge prompts from a JSONL/JSON prediction export, run `python -m src.judge outputs/judge_input.json outputs/judge_prompts.jsonl`. API judging is opt-in: install `openai`, set `OPENAI_API_KEY`, and add `--api`.

## System design

- **Intent:** nine operational intents plus `other_or_unknown`, selected from repeated support patterns in the fixture.
- **Retrieval:** TF-IDF word and bigram similarity over agent-authored historical resolutions. No customer text is used as an answer source.
- **Draft:** by default the nearest historical resolution is returned as a deterministic offline fallback. Set `ENABLE_LLM_GENERATION=1` with `OPENAI_API_KEY` to synthesize a new reply from the top three retrieved historical resolutions. The UI/export records which mode produced each draft.
- **Escalation:** deterministic guardrails cover security/legal language, low confidence, weak retrieval, and issues likely to require private payment/order/repair data.
- **Ambiguity and privacy:** unknown messages receive a clarifying question; common emails, phone numbers, card numbers, passwords, OTPs, and passcodes are redacted before classification and generation.
- **Judge:** `src.evaluate` computes exact intent accuracy, escalation accuracy, token-overlap groundedness, and agreement against a small human-audited judge-label file. Replace that file with a larger blinded sample when using an LLM judge.

## Files

- `src/agent.py`: pipeline and policy.
- `app.py`: Streamlit demonstration UI.
- `src/prepare.py`: Kaggle CSV normalizer.
- `src/evaluate.py`: metrics and judge-agreement harness.
- `src/baselines.py`: majority and TF-IDF + Logistic Regression baselines.
- `src/create_golden_template.py`: real-data blind-labeling sampler.
- `src/judge.py`: rubric prompt export and optional LLM judge runner.
- `src/database.py`: SQLite persistence and JSON import utility.
- `data/golden.csv`: 150-row labeled evaluation set.
- `data/judge_labels.csv`: 10 examples labeled by a human and the judge.
- `REPORT.md`: report, sampling note, rubric, limitations, and decision log.

## Reproducibility and safety

This baseline has no API key requirement and does not send customer text to a third party. Replies never request passwords or public payment details. For production, add PII redaction, retrieval freshness checks, rate limits, human review sampling, and a real held-out set sampled from threads rather than templates.

For opt-in LLM drafting, install `openai`, copy `.env.example` to `.env`, set the key, and enable `ENABLE_LLM_GENERATION=1`. The fallback remains active when the key, package, or API call is unavailable.

## What we did not build

- No production Twitter integration or real-time message ingestion.
- No live access to customer orders, accounts, payments, or refunds.
- No autonomous refund, cancellation, or account actions.
- No production-grade PII vault or identity verification system.
- No fine-tuned language model or multi-brand production deployment.
- No claim that the smoke-test metrics represent full Kaggle performance.
