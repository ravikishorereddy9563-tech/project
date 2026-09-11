"""Sample real customer messages for blind human labeling.

This creates a labeling template; it intentionally does not assign model labels.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


def create_template(input_path: str, output_path: str, brand: str, size: int, seed: int) -> None:
    data = pd.read_csv(input_path, dtype={"tweet_id": str, "thread_id": str})
    data = data[data["brand"].eq(brand) & data["author_role"].eq("customer")].copy()
    if data.empty:
        raise ValueError(f"No customer messages found for brand {brand!r}")
    sample = data.sample(n=min(size, len(data)), random_state=seed).reset_index(drop=True)
    result = pd.DataFrame({
        "id": [f"real-{index + 1:03d}" for index in range(len(sample))],
        "source_thread_id": sample["thread_id"].astype(str),
        "source_tweet_id": sample["tweet_id"].astype(str),
        "text": sample["text"].astype(str),
        "intent": "",
        "escalate": "",
        "reference_reply": "",
        "annotator_notes": "",
    })
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    print(f"wrote {len(result)} unlabeled rows to {output_path}; label intent and escalation before evaluation")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--brand", default="AppleSupport")
    parser.add_argument("--size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    create_template(args.input, args.output, args.brand, args.size, args.seed)
