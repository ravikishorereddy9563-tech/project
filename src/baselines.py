"""Intent baselines used for comparison against the support agent."""
from __future__ import annotations

from collections import Counter

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score


def training_examples(threads: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for thread_id, thread in threads.groupby("thread_id"):
        customer = " ".join(thread.loc[thread["author_role"].eq("customer"), "text"])
        if customer.strip():
            rows.append({"text": customer, "intent": _label_from_text(customer)})
    return pd.DataFrame(rows)


def _label_from_text(text: str) -> str:
    from .agent import INTENTS
    normalized = text.lower()
    scores = {intent: sum(phrase in normalized for phrase in phrases) for intent, phrases in INTENTS.items()}
    intent, hits = max(scores.items(), key=lambda item: item[1])
    return intent if hits else "other_or_unknown"


def evaluate_baselines(threads: pd.DataFrame, golden: pd.DataFrame) -> dict:
    training = training_examples(threads)
    if training.empty:
        raise ValueError("No customer examples found for baseline training")
    majority = Counter(training["intent"]).most_common(1)[0][0]
    majority_predictions = [majority] * len(golden)

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    features = vectorizer.fit_transform(training["text"])
    classifier = LogisticRegression(max_iter=1000, class_weight="balanced")
    classifier.fit(features, training["intent"])
    tfidf_predictions = classifier.predict(vectorizer.transform(golden["text"]))

    return {
        "majority_classifier": _scores(golden["intent"], majority_predictions),
        "tfidf_logistic_regression": _scores(golden["intent"], tfidf_predictions),
        "majority_label": majority,
        "training_examples": len(training),
    }


def _scores(expected: pd.Series, predicted) -> dict:
    return {
        "accuracy": round(accuracy_score(expected, predicted), 3),
        "macro_f1": round(f1_score(expected, predicted, average="macro", zero_division=0), 3),
    }
