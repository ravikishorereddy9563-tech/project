"""Grounded reply generation with an opt-in OpenAI-compatible LLM."""
from __future__ import annotations

import os

SYSTEM_PROMPT = """You draft customer-support replies for a brand. Use only the historical agent replies supplied as evidence. Do not invent refunds, dates, policies, account facts, or guarantees. Never ask for passwords or public payment details. If evidence is insufficient, ask the customer to continue in a private channel. Keep the reply concise and professional."""


def generate_reply(customer_message: str, intent: str, evidence: list[str], fallback: str) -> tuple[str, str]:
    """Return (reply, mode); mode is `llm` only when explicitly enabled."""
    if os.getenv("ENABLE_LLM_GENERATION") != "1" or not os.getenv("OPENAI_API_KEY"):
        return fallback, "historical_retrieval"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        evidence_text = "\n\n".join(f"Evidence {index}: {text}" for index, text in enumerate(evidence, 1))
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            max_tokens=180,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Intent: {intent}\nCustomer: {customer_message}\nHistorical evidence:\n{evidence_text}"},
            ],
        )
        reply = response.choices[0].message.content.strip()
        if reply:
            return reply, "llm"
    except Exception:
        pass
    return fallback, "historical_retrieval"
