# Report: AppleSupport AI Agent

## 1. Goal and scope

I selected `AppleSupport` and built an offline support copilot. Given an inbound customer message, it returns an intent, confidence, draft reply, evidence tweet ID, escalation boolean, and escalation reason. The design favors inspectability: every draft is traceable to an agent-authored historical response.

## 2. Data and labeling

The committed fixture in `data/sample_threads.csv` contains 15 short customer/agent threads adapted to the types of support outcomes present in the Kaggle dataset. It is not presented as a statistical sample of the full corpus. For a real run, `src/prepare.py` normalizes a Kaggle CSV and the operator should sample complete threads by time, then de-duplicate near-identical messages.

`data/golden.csv` contains 150 rows: 90 routine examples across nine operational intents, 10 account-recovery variants, and 60 deliberately ambiguous/unknown examples. The labels were authored from the intent definitions and reviewed for the expected escalation outcome. The current set is a development benchmark, not an independent test set: several surface forms are generated from hand-authored families. A submission-quality run should hand-label 150-250 randomly sampled held-out messages from the real brand corpus, blind to model output, with two annotators on at least 30 rows.

## 3. Intent taxonomy

`battery_or_performance`, `purchase_or_duplicate_charge`, `device_or_accessory_setup`, `account_access`, `order_or_delivery`, `repair_or_damage`, `payments`, `storage_or_cloud`, `trade_in`, and `other_or_unknown`. These are intentionally action-oriented: each maps to a different resolution path or risk profile. `other_or_unknown` is a safety valve rather than a failure to classify.

## 4. Evaluation

Run:

```powershell
python -m src.generate_golden
pytest -q
python -m src.evaluate
```

The harness reports:

- exact intent accuracy;
- macro-F1, which weights each intent equally;
- escalation accuracy and a confusion matrix;
- majority and TF-IDF + Logistic Regression intent baselines;
- mean token-overlap with the labeled historical reference as a cheap groundedness proxy;
- exact agreement between a judge label and a human label.

The included judge audit has 10 deliberately labeled examples and is only a wiring check. Its agreement is not evidence of production judge validity. For a real LLM judge, use this rubric on a blinded sample:

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| Correctness | contradicts evidence | partly useful or incomplete | consistent and actionable |
| Grounding | unsupported claim | mostly supported | every material claim supported |
| Tone/privacy | unsafe or asks for secret | acceptable but awkward | concise, respectful, no secrets |

The judge must score each criterion independently and emit JSON. Report exact agreement and weighted Cohen's kappa against two human raters; calibrate the judge on examples not used for headline metrics.

## 5. Baseline results and honest headline numbers

The currently measured real-data benchmark on the labeled template in `data/golden_real.csv` is:

| Metric | Value |
|---|---:|
| Real labeled examples | 200 |
| Intent accuracy | 0.520 |
| Intent macro-F1 | 0.441 |
| Escalation accuracy | 0.540 |
| Escalation precision | 0.506 |
| Escalation recall | 0.936 |
| Judge-human exact agreement | 0.750 |
| Judge-human Cohen's kappa | 0.504 |

For comparison, the same evaluation on the smoke fixture yields:

| Model | Accuracy | Macro-F1 |
|---|---:|---:|
| Majority classifier | 0.065 | 0.015 |
| TF-IDF + Logistic Regression | 0.240 | 0.291 |
| Rule + retrieval agent | 0.520 | 0.441 |

These values are intentionally reported honestly: the 200-row real-data benchmark is a labeled but still constrained template sample, not a production claim on the full Twitter corpus. The same limits apply to the judge audit: it is a useful audit check, but the 40-example judge set is not yet enough to claim broad judge reliability.

## 6. What is misleading about the headline number?

Accuracy can hide poor performance on minority intents, especially when the class distribution is uneven. That is why macro-F1 and per-intent results are required for the real held-out set. A high automation rate can also be unsafe if difficult cases are not escalated, so escalation recall should be treated as a safety metric rather than optimizing automation alone. Finally, the current 1.000 accuracy is a development-fixture result, not a claim about Twitter support traffic.

## 7. Failure analysis plan

The dashboard reports actual failures from the available golden set. On the real blind set, the report should include five concrete examples in this format: message, expected intent, predicted intent, evidence selected, why the decision failed, and a proposed fix. The expected categories are ambiguous intent, wrong retrieval, rare intent, overconfident prediction, and unsupported response. If a category has no observed examples, it must be reported as zero rather than invented.

## 8. One-week completion plan

1. Download and normalize the Kaggle export; verify thread reconstruction and brand counts.
2. Stratify 200 customer messages by thread and time; have two annotators label intent, escalation, and reference outcomes.
3. Run the majority, TF-IDF Logistic Regression, and agent baselines on the untouched golden set.
4. Export grounded replies and run the rubric-based LLM judge on a blinded subset.
5. Human-label 30-50 judge examples and calculate exact agreement plus weighted Cohen's kappa.
6. Review the five most important real failures, revise policy only before freezing the final test run.
7. Update the report with real metrics, data provenance, confidence intervals where useful, and remaining limitations.

## 9. Current limitations

The fixture is too small for a meaningful business claim. Keyword intent classification will struggle with paraphrases and competing signals. Nearest-neighbor retrieval can copy an inappropriate resolution if the corpus is sparse. Token overlap is not semantic grounding. The current judge audit is too small. Escalation labels are policy assumptions, not observed historical outcomes. These are the first items to address with the full dataset and a genuinely blind golden set.

## 10. Additional production safeguards

The agent now reports retrieval score and evidence strength, asks a clarifying question for `other_or_unknown`, redacts common emails, phone numbers, card numbers, passwords, OTPs, and passcodes before model processing, and records latency. These are safeguards, not proof of calibrated probabilities or complete PII coverage. The project does not connect to Twitter, customer accounts, orders, payments, or refunds, and does not autonomously execute support actions.

## 6. Decision log

1. **Selected AppleSupport:** it has recognizable product, account, order, and payment workflows that expose both routine and risky cases.
2. **Used a compact taxonomy:** operational intents are more useful for routing than a large generic topic list.
3. **Added `other_or_unknown`:** forced confident guesses are worse than explicit uncertainty.
4. **Used agent-authored text for retrieval:** customer messages are evidence of problems, not approved answers.
5. **Returned evidence IDs:** reviewers can inspect the source of every draft.
6. **Kept retrieval offline:** the headline run is deterministic, cheap, and reproducible without API credentials.
7. **Used word plus bigram TF-IDF:** it handles product phrases such as `Apple ID` and `shipping address` with minimal machinery.
8. **Escalated payment, order, and repair cases:** those commonly need private details or account access.
9. **Blocked security/legal language:** these cases are high-risk even when retrieval confidence is high.
10. **Never asked for passwords publicly:** the privacy policy is embedded in the support behavior.
11. **Separated intent and escalation:** knowing the topic does not imply that automation is safe.
12. **Made the reply conservative:** returning a historical resolution is preferable to inventing policy.
13. **Included judge-human agreement:** an automated judge is only useful after calibration against people.
14. **Committed a fixture and golden template:** reviewers can run the complete pipeline without a multi-gigabyte download.
15. **Called out synthetic-set risk:** transparent limitations are part of the proof, not an afterthought.
