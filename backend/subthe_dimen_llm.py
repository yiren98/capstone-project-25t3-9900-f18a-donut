# subthe_dimen_llm.py
# LLM helpers for subtheme/dimension summaries:
# - OpenRouter client
# - prompts
# - JSON extraction

from __future__ import annotations

import os
import json
import re
from typing import Any, Dict, List

from openai import OpenAI

DEFAULT_MODEL = "deepseek/deepseek-chat-v3.1:free"
DEFAULT_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
API_KEY_ENV = "OPENROUTER_API_KEY"


def is_quota_or_ratelimit_error(err: Exception) -> bool:
    # Check if error looks like quota / rate limit.
    msg = str(err).lower()
    keywords = [
        "insufficient_quota",
        "insufficient quota",
        "usage limit",
        "rate limit",
        "too many requests",
        "429",
        "402",
        "billing_hard_limit",
        "billing_soft_limit",
    ]
    return any(k in msg for k in keywords)


def build_client():
    # Build OpenAI client for OpenRouter + DeepSeek.
    api_key = os.getenv(API_KEY_ENV)
    if not api_key:
        raise RuntimeError(f"Missing {API_KEY_ENV}. Please export your OpenRouter API key.")
    client = OpenAI(base_url=DEFAULT_BASE_URL, api_key=api_key)
    return client


def extract_first_json(text: str) -> str:
    # Extract first complete JSON object from LLM text.
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        first_brace = text.find("{")
        if first_brace != -1:
            text = text[first_brace:]

    start = text.find("{")
    if start == -1:
        raise ValueError("No '{' found in response; cannot extract JSON.")

    depth = 0
    in_string = False
    escape = False
    end = None

    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break

    if end is None:
        raise ValueError("No matching closing brace for JSON object.")
    return text[start : end + 1]


def call_deepseek_json(client, model: str, prompt: str) -> Dict[str, Any]:
    # Call DeepSeek and return parsed JSON.
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
        temperature=0.35,
    )
    text = resp.choices[0].message.content.strip()

    try:
        json_str = extract_first_json(text)
    except ValueError:
        lower = text.lower()
        if any(k in lower for k in ["quota", "rate limit", "usage limit", "insufficient_quota"]):
            raise RuntimeError(f"Quota or rate-limit error: {text}")
        raise RuntimeError(f"LLM did not return JSON. Raw response:\n{text}")

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        fix_prompt = f"""
            Fix the following text into valid JSON (keep all keys/values intact, only fix syntax):

            ```json
            {json_str}
            """
        resp2 = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": fix_prompt}],
            max_tokens=800,
            temperature=0.0,
        )
        fixed_text = resp2.choices[0].message.content.strip()
        fixed_json_str = extract_first_json(fixed_text)
        return json.loads(fixed_json_str)


def build_prompt_for_subtheme(subtheme_name: str, stats: Dict[str, Any], examples: List[Dict[str, Any]]) -> str:
    # Prompt for one subtheme summary.
    dim_lines = [f"- {dim}: {c}" for dim, c in stats["dimensions_counter"].items()]
    dim_block = "\n".join(dim_lines) if dim_lines else "(no clear parent dimension)"

    sent_counts = stats["sentiment_counts"]
    sent_block = (
        f"- positive: {sent_counts.get('positive', 0)}\n"
        f"- negative: {sent_counts.get('negative', 0)}\n"
    )

    ex_lines = []
    for i, ex in enumerate(examples, start=1):
        conf_str = "n/a" if ex["confidence"] is None else f"{ex['confidence']:.2f}"
        ex_lines.append(
            f"{i}. [sentiment={ex['sentiment']}, dim={ex['dimension']}, conf={conf_str}] "
            f"source={ex['source']}, time={ex['created_time']}\n"
            f"   evidence: {ex['evidence']}\n"
            f"   content: {ex['content']}"
        )
    examples_block = "\n".join(ex_lines) if ex_lines else "(no examples available)"

    prompt = f"""
        You are a corporate culture analyst. Summarise the following *subtheme* based on aggregated statistics and representative examples.

        Subtheme name:
        - {subtheme_name}

        Aggregated statistics:
        - Total mentions: {stats["total_mentions"]}
        - Sentiment counts:
        {sent_block.strip()}
        - Average confidence (overall): {stats["avg_confidence"]:.3f}
        - Parent dimensions distribution:
        {dim_block if dim_block else "(none)"}

        Representative examples (each bullet is one real-world comment snippet):
        {examples_block if examples_block else "(none)"}

        TASK:
        1. Read the data carefully and write a concise, insightful summary of this **subtheme** in the corporate culture context.
        2. Focus on:
        - What this subtheme represents in simple terms.
        - How it typically appears in company-related discourse.
        - What challenges or risks it reveals.
        - Actionable recommendations.

        OUTPUT FORMAT:
        Return **strict JSON** only, with this structure:

        {{
        "subtheme": "<subtheme_name>",
        "parent_dimensions": ["<most_relevant_dimension_1>", "<most_relevant_dimension_2>"],
        "overview": "<2–4 sentences: what this subtheme represents and why it matters>",
        "key_patterns": [
            "<pattern 1>",
            "<pattern 2>",
            "<pattern 3>"
        ],
        "sentiment_snapshot": {{
            "positive": {sent_counts.get('positive', 0)},
            "negative": {sent_counts.get('negative', 0)},
            "average_confidence": {stats["avg_confidence"]:.3f}
        }},
        "typical_contexts": [
            "<how this subtheme usually appears in comments>",
            "<which situations trigger it>",
            "<its interaction with other cultural dimensions>"
        ],
        "risks_and_blindspots": [
            "<risk or blindspot 1>",
            "<risk or blindspot 2>"
        ],
        "recommendations": [
            "<recommendation 1 (organisation-level)>",
            "<recommendation 2 (leadership/process-level)>"
        ]
        }}

        IMPORTANT:
        - Do NOT fabricate numbers; use the given sentiment counts and confidence.
        - Speak as a human consultant, not an AI model.
        - Output must be valid JSON and parseable.
        """
    return prompt.strip()


def build_prompt_for_dimension(dimension_name: str, stats: Dict[str, Any], examples: List[Dict[str, Any]]) -> str:
    # Prompt for one culture dimension summary.
    sub_lines = [f"- {sub}: {c}" for sub, c in stats["subthemes_counter"].items()]
    sub_block = "\n".join(sub_lines) if sub_lines else "(no clear associated subthemes)"

    sent_counts = stats["sentiment_counts"]
    sent_block = (
        f"- positive: {sent_counts.get('positive', 0)}\n"
        f"- negative: {sent_counts.get('negative', 0)}\n"
    )

    ex_lines = []
    for i, ex in enumerate(examples, start=1):
        conf_str = "n/a" if ex["confidence"] is None else f"{ex['confidence']:.2f}"
        ex_lines.append(
            f"{i}. [subtheme={ex.get('subtheme','')}, sentiment={ex['sentiment']}, conf={conf_str}] "
            f"source={ex['source']}, time={ex['created_time']}\n"
            f"   evidence: {ex['evidence']}\n"
            f"   content: {ex['content']}"
        )
    examples_block = "\n".join(ex_lines) if ex_lines else "(no examples available)"

    prompt = f"""
        You are a corporate culture analyst. Summarise the following *culture dimension* based on aggregated statistics and representative examples.

        Dimension name:
        - {dimension_name}

        Aggregated statistics:
        - Total mentions: {stats["total_mentions"]}
        - Sentiment counts:
        {sent_block.strip()}
        - Average confidence (overall): {stats["avg_confidence"]:.3f}
        - Key associated subthemes (with frequency):
        {sub_block if sub_block else "(none)"}

        Representative examples (each bullet is one real-world comment snippet):
        {examples_block if examples_block else "(none)"}

        TASK:
        1. Read the data carefully and write a concise, insightful summary of this **dimension** in the corporate culture context.
        2. Focus on:
        - What this dimension represents in simple terms.
        - Typical narratives and patterns where this dimension appears.
        - How this dimension shapes stakeholder perception.
        - Actionable recommendations.

        OUTPUT FORMAT:
        Return **strict JSON** only, with this structure:

        {{
        "dimension": "<dimension_name>",
        "overview": "<2–4 sentences: what this dimension represents and why it matters>",
        "key_patterns": [
            "<pattern 1>",
            "<pattern 2>",
            "<pattern 3>",
            "<pattern 4>",
            "<pattern 5>"
        ],
        "sentiment_snapshot": {{
            "positive": {sent_counts.get('positive', 0)},
            "negative": {sent_counts.get('negative', 0)},
            "average_confidence": {stats["avg_confidence"]:.3f}
        }},
        "top_subthemes": [
            {{"subtheme": "<subtheme_name_1>", "count": <int_count_1>}},
            {{"subtheme": "<subtheme_name_2>", "count": <int_count_2>}},
            {{"subtheme": "<subtheme_name_3>", "count": <int_count_3>}}
        ],
        "risks_and_blindspots": [
            "<risk or blindspot 1>",
            "<risk or blindspot 2>",
            "<risk or blindspot 3>",
            "<risk or blindspot 4>",
            "<risk or blindspot 5>"
        ],
        "recommendations": [
            "<recommendation 1>",
            "<recommendation 2>",
            "<recommendation 3>",
            "<recommendation 4>",
            "<recommendation 5>",
            "<recommendation 6>",
            "<recommendation 7>"
        ]
        }}

        IMPORTANT:
        - Do NOT fabricate numbers; use the sentiment counts and average_confidence as given.
        - For "top_subthemes", use the subtheme names and counts from the frequency list above.
        - Speak as a human consultant, not an AI model.
        - Output must be valid JSON and parseable.
        """
    return prompt.strip()
