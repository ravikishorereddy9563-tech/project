"""Convert Kaggle's customer-support-on-twitter CSV into agent training rows."""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


def prepare(input_path: str, output_path: str, brand: str, agent_author_id: str | None = None) -> None:
    raw = pd.read_csv(input_path)
    columns = {column.lower(): column for column in raw.columns}
    text_column = next((columns[name] for name in ("text", "tweet_text", "body") if name in columns), None)
    author_column = next((columns[name] for name in ("author_role", "inbound", "author") if name in columns), None)
    tweet_id_column = columns.get("tweet_id")
    parent_column = columns.get("in_response_to_tweet_id")
    if not text_column:
        raise ValueError("Could not find a text column in the input CSV")
    brand_column = columns.get("brand")
    author_id_column = columns.get("author_id")
    if brand_column:
        raw = raw[raw[brand_column].eq(brand)].copy()
    elif author_id_column:
        selected_author = agent_author_id or brand
        agent_ids = raw[author_id_column].astype(str).eq(selected_author)
        tweet_ids_all = raw[tweet_id_column].astype(str) if tweet_id_column else raw.index.astype(str)
        referenced_by_agent = raw["response_tweet_id"].astype(str).isin(tweet_ids_all[agent_ids]) if "response_tweet_id" in columns else pd.Series(False, index=raw.index)
        replies_to_agent = raw["in_response_to_tweet_id"].astype(str).isin(tweet_ids_all[agent_ids]) if "in_response_to_tweet_id" in columns else pd.Series(False, index=raw.index)
        raw = raw[agent_ids | referenced_by_agent | replies_to_agent].copy()
    tweet_ids = raw[tweet_id_column].astype(str) if tweet_id_column else raw.index.astype(str)
    parent_ids = raw[parent_column].fillna("").astype(str) if parent_column else pd.Series([""] * len(raw), index=raw.index)
    parent_map = dict(zip(tweet_ids, parent_ids))

    def root_id(tweet_id: str) -> str:
        seen = set()
        current = tweet_id
        while current in parent_map and parent_map[current] and current not in seen:
            seen.add(current)
            current = parent_map[current]
        return current

    result = pd.DataFrame({"tweet_id": tweet_ids,
                           "thread_id": tweet_ids.map(root_id), "brand": brand,
                           "author_role": "customer", "text": raw[text_column].fillna("").astype(str)})
    if author_column:
        values = raw[author_column]
        if values.dtype == bool or set(values.dropna().unique()).issubset({True, False, 0, 1}):
            result["author_role"] = values.map(lambda value: "customer" if bool(value) else "agent")
        else:
            result["author_role"] = values.map(lambda value: "agent" if str(value).lower() in {"agent", "brand", "company", "false", "0"} else "customer")
    if agent_author_id and author_id_column:
        result["author_role"] = raw[author_id_column].astype(str).map(lambda value: "agent" if value == agent_author_id else "customer")
    result = result[result["text"].str.strip().ne("")]
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--brand", default="AppleSupport")
    parser.add_argument("--agent-author-id", help="Optional TWCS author_id for the selected brand")
    args = parser.parse_args()
    prepare(args.input, args.output, args.brand, args.agent_author_id)
