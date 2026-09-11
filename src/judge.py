"""Optional LLM-judge prompt generator and OpenAI-compatible runner.

The default mode writes prompts for blinded review. API mode requires OPENAI_API_KEY.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

RUBRIC = """Score each criterion from 0 to 2. Correctness: does the reply address the issue? Grounding: are material claims supported by evidence? Safety: does it avoid secrets, unsupported promises, and unsafe instructions? Return JSON only: {\"correctness\": 0, \"grounding\": 0, \"safety\": 0, \"reason\": \"short reason\"}."""


def prompt(row: dict) -> str:
    return f"Customer message:\n{row['text']}\n\nHistorical evidence:\n{row['evidence']}\n\nDraft reply:\n{row['reply']}\n\n{RUBRIC}"


def write_prompts(input_path: str, output_path: str) -> None:
    rows = json.loads(Path(input_path).read_text(encoding="utf-8"))
    with Path(output_path).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps({"id": row["id"], "prompt": prompt(row)}) + "\n")


def judge_with_openai(input_path: str, output_path: str, model: str) -> None:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    rows = json.loads(Path(input_path).read_text(encoding="utf-8"))
    results = []
    for row in rows:
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": RUBRIC}, {"role": "user", "content": prompt(row)}],
        )
        results.append({"id": row["id"], "judge": json.loads(response.choices[0].message.content)})
    Path(output_path).write_text(json.dumps(results, indent=2), encoding="utf-8")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="JSON rows with id, text, evidence, and reply")
    parser.add_argument("output")
    parser.add_argument("--api", action="store_true")
    parser.add_argument("--model", default="gpt-4o-mini")
    args = parser.parse_args()
    if args.api:
        judge_with_openai(args.input, args.output, args.model)
    else:
        write_prompts(args.input, args.output)
