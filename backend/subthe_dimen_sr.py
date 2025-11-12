"""
Generate JSON summaries for each subtheme (using deepseek/deepseek-chat-v3.1:free)

Input: comments.csv
[tag,text,author,score,comment_count,content,created_time,
    dimensions,subthemes,subs_sentiment,confidence,subs_evidences,source]

Outputs:
    Subthemes:   <sub_outdir>/subtheme_<slug>.json
    Dimensions:  <dim_outdir>/dimension_<slug>.json  

Basic usage (subthemes/dimensions only):
    python subthe_dimen_sr.py --csv comments.csv --outdir subthemes_sr --max-examples 10

Subthemes + dimensions:
    python subthe_dimen_sr.py --csv comments.csv --outdir subthemes_sr --dim-outdir dimensions_sr

Selective overwrite (applies to both subthemes and dimensions):
    # Overwrite all existing files
    python subthe_dimen_sr.py --csv comments.csv --outdir subthemes_sr --dim-outdir dimensions_sr --overwrite

    # Same, explicit:
    python subthe_dimen_sr.py --csv comments.csv --outdir subthemes_sr --dim-outdir dimensions_sr --overwrite all

    # Only overwrite subthemes/dimensions whose names contain "Accountability" or "Digital"
    python subthe_dimen_sr.py --csv comments.csv --outdir subthemes_sr --dim-outdir dimensions_sr \
        --overwrite "Accountability,Digital"
"""

import os
import re
import json
import argparse
from pathlib import Path
from collections import Counter
import pandas as pd
from openai import OpenAI

# ==================== CONFIGURATION ====================
DEFAULT_MODEL = "deepseek/deepseek-chat-v3.1:free"
DEFAULT_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
API_KEY_ENV = "OPENROUTER_API_KEY"


# ==================== UTILITY FUNCTIONS ====================
def slugify(name: str) -> str:
    """Convert a label (subtheme or dimension) into a safe lowercase slug for filenames."""
    name = name.strip()
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug.lower() or "item"

def safe_json_loads(s):
    """Safely parse a JSON string; return None if it fails."""
    if pd.isna(s) or not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None

def is_quota_or_ratelimit_error(err: Exception) -> bool:
    """Detect whether an exception message is likely due to quota/rate limit."""
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
    """Build an OpenAI client that targets OpenRouter with the DeepSeek model."""
    api_key = os.getenv(API_KEY_ENV)
    if not api_key:
        raise RuntimeError(f"Missing {API_KEY_ENV}. Please export your OpenRouter API key.")
    client = OpenAI(base_url=DEFAULT_BASE_URL, api_key=api_key)
    return client


# ==================== PROMPT CONSTRUCTION ====================
def build_prompt_for_subtheme(subtheme_name: str, stats: dict, examples: list) -> str:
    """
    Build the DeepSeek prompt text for one subtheme.

    stats: aggregated info (mentions, sentiment counts, avg confidence, dimension frequencies)
    examples: representative samples from comments for this subtheme
    """
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

def build_prompt_for_dimension(dimension_name: str, stats: dict, examples: list) -> str:
    """
    Build the DeepSeek prompt text for one dimension.

    stats: {
        "total_mentions": int,
        "sentiment_counts": {"positive": x, "negative": y},
        "avg_confidence": float,
        "subthemes_counter": {"Transparency & Disclosure": 60, ...}
    }
    examples: representative samples from comments for this dimension
    """
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


# ==================== JSON EXTRACTION HELPERS ====================
def extract_first_json(text: str) -> str:
    """Extract the first complete JSON object from a text response."""
    text = text.strip()
    # Handle fenced code blocks like ```json ... ```
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
    return text[start:end + 1]

def call_deepseek_json(client, model: str, prompt: str) -> dict:
    """
    Call DeepSeek to generate JSON.
    1. Call the model with the prompt.
    2. Extract the first JSON object from the response.
    3. If parsing fails, try a repair step with another LLM call.
    """
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
        temperature=0.35,
    )
    text = resp.choices[0].message.content.strip()

    # Try to extract JSON object from the raw text.
    try:
        json_str = extract_first_json(text)
    except ValueError:
        lower = text.lower()
        if any(k in lower for k in ["quota", "rate limit", "usage limit", "insufficient_quota"]):
            raise RuntimeError(f"Quota or rate-limit error: {text}")
        raise RuntimeError(f"LLM did not return JSON. Raw response:\n{text}")

    # Try direct JSON parsing first.
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # If the JSON is slightly invalid, ask the model to fix it.
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


# ==================== DATA AGGREGATION ====================
def aggregate_by_subtheme(df: pd.DataFrame) -> dict:
    """
    Group comments by subtheme and aggregate statistics.

    For each subtheme we collect:
        - total_mentions: number of rows where it appears with positive/negative sentiment
        - sentiment_counts: count of "positive"/"negative"
        - avg_confidence: mean confidence (over rows included)
        - dimensions_counter: count of associated dimensions
        - examples: representative comment snippets
    """
    agg = {}

    for _, row in df.iterrows():
        # Choose a readable text body: prefer "content", fallback to "text".
        body = (row.get("content") or "").strip() or (row.get("text") or "").strip()
        created_time = str(row.get("created_time", ""))
        source = str(row.get("source", ""))
        confidence = row.get("confidence", None)

        dims_raw = row.get("dimensions")
        subs_raw = row.get("subthemes")
        subs_sent_raw = row.get("subs_sentiment")
        subs_evid_raw = row.get("subs_evidences")

        if pd.isna(subs_raw) or not str(subs_raw).strip():
            continue

        subthemes_list = [s.strip() for s in str(subs_raw).split("|") if s.strip()]
        if not subthemes_list:
            continue

        dims_list = [d.strip() for d in str(dims_raw).split("|")] if dims_raw else []
        # If dimensions list is shorter than subthemes list, repeat the last dimension
        if dims_list and len(dims_list) < len(subthemes_list):
            dims_list += [dims_list[-1]] * (len(subthemes_list) - len(dims_list))

        sent_map = safe_json_loads(subs_sent_raw) or {}
        evid_map = safe_json_loads(subs_evid_raw) or {}

        for i, sub in enumerate(subthemes_list):
            # Determine sentiment for this specific subtheme.
            sent = sent_map.get(sub)
            if sent is None and len(sent_map) == 1:
                # If only one key exists and name mismatch, use that single sentiment.
                sent = list(sent_map.values())[0]

            # Only keep positive / negative; drop everything else (including neutral).
            if sent not in ("positive", "negative"):
                continue

            dim = dims_list[i] if dims_list and i < len(dims_list) else None
            if sub in evid_map:
                ev = evid_map.get(sub)
            elif len(evid_map) == 1:
                ev = list(evid_map.values())[0]
            else:
                ev = ""

            if sub not in agg:
                agg[sub] = {
                    "total_mentions": 0,
                    "sentiment_counts": Counter(),
                    "confidences": [],
                    "dimensions_counter": Counter(),
                    "examples": [],
                }

            item = agg[sub]
            item["total_mentions"] += 1
            item["sentiment_counts"][sent] += 1

            if isinstance(confidence, (int, float)):
                item["confidences"].append(float(confidence))

            if dim:
                item["dimensions_counter"][dim] += 1

            item["examples"].append({
                "sentiment": sent,
                "dimension": dim or "",
                "subtheme": sub,
                "confidence": float(confidence) if isinstance(confidence, (int, float)) else None,
                "created_time": created_time,
                "source": source,
                "evidence": ev,
                "content": body[:1000],  # Clip long comments for prompt safety.
            })

    # Compute average confidence and finalize structure.
    result = {}
    for sub, item in agg.items():
        confs = item["confidences"]
        avg_conf = sum(confs) / len(confs) if confs else 0.0
        result[sub] = {
            "total_mentions": item["total_mentions"],
            "sentiment_counts": dict(item["sentiment_counts"]),
            "avg_confidence": avg_conf,
            "dimensions_counter": dict(item["dimensions_counter"]),
            "examples": item["examples"],
        }
    return result

def aggregate_dimensions_from_sub_agg(sub_agg: dict) -> dict:
    """
    Build dimension-level aggregation from subtheme-level aggregation.

    We re-use the examples collected for each subtheme:
        - For each example, we look at its 'dimension' and 'sentiment'.
        - We group by dimension, accumulate positive/negative counts and confidence.
        - We also track how often each subtheme appears under each dimension.
    """
    dim_agg = {}

    for sub, data in sub_agg.items():
        for ex in data["examples"]:
            dim = ex.get("dimension") or ""
            if not dim:
                continue
            sent = ex.get("sentiment")
            if sent not in ("positive", "negative"):
                continue

            if dim not in dim_agg:
                dim_agg[dim] = {
                    "total_mentions": 0,
                    "sentiment_counts": Counter(),
                    "confidences": [],
                    "subthemes_counter": Counter(),
                    "examples": [],
                }

            item = dim_agg[dim]
            item["total_mentions"] += 1
            item["sentiment_counts"][sent] += 1
            conf = ex.get("confidence")
            if isinstance(conf, (int, float)):
                item["confidences"].append(float(conf))
            item["subthemes_counter"][sub] += 1

            # Keep example; include subtheme explicitly for prompt.
            item["examples"].append({
                "subtheme": sub,
                "sentiment": sent,
                "confidence": conf if isinstance(conf, (int, float)) else None,
                "created_time": ex.get("created_time", ""),
                "source": ex.get("source", ""),
                "evidence": ex.get("evidence", ""),
                "content": ex.get("content", "")[:1000],
            })

    result = {}
    for dim, item in dim_agg.items():
        confs = item["confidences"]
        avg_conf = sum(confs) / len(confs) if confs else 0.0
        result[dim] = {
            "total_mentions": item["total_mentions"],
            "sentiment_counts": dict(item["sentiment_counts"]),
            "avg_confidence": avg_conf,
            "subthemes_counter": dict(item["subthemes_counter"]),
            "examples": item["examples"],
        }
    return result

def load_df(csv_path: Path) -> pd.DataFrame:
    """
    Read CSV with multiple encoding fallbacks and ensure required columns exist.

    - Tries utf-8-sig, utf-8, cp1252 encodings.
    - Normalises column names by stripping BOM, spaces, etc.
    - Ensures all expected columns exist (filled with empty strings if missing).
    """
    for enc in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            df = pd.read_csv(csv_path, encoding=enc, on_bad_lines="skip")
            break
        except Exception:
            continue
    else:
        raise RuntimeError(f"Failed to read CSV: {csv_path}")

    # Normalise column names (remove BOM, whitespace).
    df.columns = [
        str(c).encode("utf-8", "ignore").decode("utf-8").strip().lstrip("\ufeff")
        for c in df.columns
    ]

    required = [
        "content", "dimensions", "subthemes", "subs_sentiment",
        "confidence", "subs_evidences", "author", "source", "created_time", "text",
    ]
    for col in required:
        if col not in df.columns:
            df[col] = None

    for col in required:
        df[col] = df[col].fillna("")

    # Convenience: merged text field (not strictly required by this script, but handy).
    df["raw_text"] = df.apply(
        lambda r: (r.get("content") or "").strip() or (r.get("text") or "").strip(),
        axis=1,
    )
    return df


# ==================== MAIN ENTRY POINT ====================
def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate JSON summaries for subthemes (and optionally dimensions), "
            "positive/negative only, with selective overwrite."
        )
    )
    parser.add_argument("--csv", required=True, help="Path to comments.csv")
    parser.add_argument("--outdir", required=True, help="Output directory for subtheme JSON files")
    parser.add_argument("--dim-outdir", help="Optional output directory for dimension JSON files")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="LLM model name")
    parser.add_argument("--max-examples", type=int, default=5, help="Maximum examples per label (subtheme/dimension)")
    parser.add_argument("--limit-subthemes", type=int, default=0, help="Limit N subthemes for debug (0=all)")
    parser.add_argument(
        "--overwrite",
        nargs="?",
        const="all",
        default="none",
        help=(
            "Overwrite behavior (applies to both subthemes and dimensions):\n"
            "  --overwrite           → overwrite all existing files\n"
            "  --overwrite all       → overwrite all existing files\n"
            "  --overwrite 'A,B,C'   → only overwrite labels whose names contain A or B or C\n"
            "  (default: 'none' → existing files are skipped)"
        ),
    )
    args = parser.parse_args()

    # ---------- Overwrite logic ----------
    overwrite_value = str(args.overwrite).strip().lower()
    overwrite_all = overwrite_value == "all"
    overwrite_list = set()

    if not overwrite_all and overwrite_value not in ("none", "", "null"):
        overwrite_list = {
            token.strip().lower()
            for token in str(args.overwrite).split(",")
            if token.strip()
        }

    def should_overwrite(name: str) -> bool:
        """
        Decide whether this label (subtheme or dimension) should be overwritten.

        Rules:
            - If overwrite_all is True: always overwrite.
            - Else if overwrite_list is non-empty: overwrite if any keyword is a substring
              of the lowercase name.
            - Else: do not overwrite (skip existing file).
        """
        if overwrite_all:
            return True
        if not overwrite_list:
            return False
        lname = name.lower()
        return any(key in lname for key in overwrite_list)

    # ---------- Load and aggregate data ----------
    csv_path = Path(args.csv)
    sub_out_dir = Path(args.outdir)
    sub_out_dir.mkdir(parents=True, exist_ok=True)

    dim_out_dir = None
    if args.dim_outdir:
        dim_out_dir = Path(args.dim_outdir)
        dim_out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[cfg] CSV         = {csv_path}")
    print(f"[cfg] SUB_OUTDIR  = {sub_out_dir}")
    print(f"[cfg] DIM_OUTDIR  = {dim_out_dir if dim_out_dir else '(disabled)'}")
    print(f"[cfg] MODEL       = {args.model}")
    print(f"[cfg] OVERWRITE   = {args.overwrite}")

    df = load_df(csv_path)
    print(f"[info] Loaded {len(df)} rows from {csv_path}")

    sub_agg = aggregate_by_subtheme(df)
    all_subthemes = sorted(sub_agg.keys())
    print(f"[info] Found {len(all_subthemes)} subthemes with positive/negative data")

    if args.limit_subthemes > 0:
        all_subthemes = all_subthemes[:args.limit_subthemes]
        print(f"[debug] limit-subthemes = {args.limit_subthemes} (effective count = {len(all_subthemes)})")

    client = build_client()

    # ---------- Subtheme summaries ----------
    for idx, sub in enumerate(all_subthemes, start=1):
        slug = slugify(sub)
        out_path = sub_out_dir / f"subtheme_{slug}.json"

        if out_path.exists() and not should_overwrite(sub):
            print(f"[{idx}/{len(all_subthemes)}] (subtheme) {sub} -> skip (exists, overwrite=False)")
            continue

        data = sub_agg[sub]
        stats = {
            "total_mentions": data["total_mentions"],
            "sentiment_counts": {
                "positive": data["sentiment_counts"].get("positive", 0),
                "negative": data["sentiment_counts"].get("negative", 0),
            },
            "avg_confidence": data["avg_confidence"],
            "dimensions_counter": data["dimensions_counter"],
        }
        examples = data["examples"][:args.max_examples]

        print(
            f"[{idx}/{len(all_subthemes)}] (subtheme) {sub} "
            f"(mentions={stats['total_mentions']}, examples={len(examples)})"
        )

        prompt = build_prompt_for_subtheme(sub, stats, examples)

        try:
            json_obj = call_deepseek_json(client, args.model, prompt)
        except Exception as e:
            print(f"[error] LLM failed for subtheme '{sub}': {e}")

            if is_quota_or_ratelimit_error(e):
                print("[fatal] Quota or rate-limit issue detected. Please refresh your API key or wait.")
                return

            json_obj = {
                "subtheme": sub,
                "parent_dimensions": sorted(stats["dimensions_counter"].keys()),
                "overview": "ERROR: LLM call failed.",
                "key_patterns": [],
                "sentiment_snapshot": {
                    "positive": stats["sentiment_counts"]["positive"],
                    "negative": stats["sentiment_counts"]["negative"],
                    "average_confidence": stats["avg_confidence"],
                },
                "typical_contexts": [],
                "risks_and_blindspots": [],
                "recommendations": [],
            }

        with out_path.open("w", encoding="utf-8") as f:
            json.dump(json_obj, f, ensure_ascii=False, indent=2)
        print(f"    -> wrote {out_path}")

    # ---------- Dimension summaries (optional) ----------
    if dim_out_dir is not None:
        dim_agg = aggregate_dimensions_from_sub_agg(sub_agg)
        all_dims = sorted(dim_agg.keys())
        print(f"[info] Found {len(all_dims)} dimensions with positive/negative data")

        for idx, dim in enumerate(all_dims, start=1):
            slug = slugify(dim)
            out_path = dim_out_dir / f"dimension_{slug}.json"

            if out_path.exists() and not should_overwrite(dim):
                print(f"[{idx}/{len(all_dims)}] (dimension) {dim} -> skip (exists, overwrite=False)")
                continue

            data = dim_agg[dim]
            stats = {
                "total_mentions": data["total_mentions"],
                "sentiment_counts": {
                    "positive": data["sentiment_counts"].get("positive", 0),
                    "negative": data["sentiment_counts"].get("negative", 0),
                },
                "avg_confidence": data["avg_confidence"],
                "subthemes_counter": data["subthemes_counter"],
            }
            examples = data["examples"][:args.max_examples]

            print(
                f"[{idx}/{len(all_dims)}] (dimension) {dim} "
                f"(mentions={stats['total_mentions']}, examples={len(examples)})"
            )

            prompt = build_prompt_for_dimension(dim, stats, examples)

            # Pre-compute true top_subthemes list from counts, sorted desc
            top_subthemes_sorted = sorted(
                stats["subthemes_counter"].items(),
                key=lambda x: x[1],
                reverse=True,
            )
            top_subthemes_list = [
                {"subtheme": name, "count": count}
                for name, count in top_subthemes_sorted
            ]

            try:
                json_obj = call_deepseek_json(client, args.model, prompt)

                # Force sentiment_snapshot and top_subthemes to use our true numbers,
                # in case the model slightly changes them.
                json_obj["sentiment_snapshot"] = {
                    "positive": stats["sentiment_counts"]["positive"],
                    "negative": stats["sentiment_counts"]["negative"],
                    "average_confidence": stats["avg_confidence"],
                }
                json_obj["top_subthemes"] = top_subthemes_list

            except Exception as e:
                print(f"[error] LLM failed for dimension '{dim}': {e}")

                if is_quota_or_ratelimit_error(e):
                    print("[fatal] Quota or rate-limit issue detected. Please refresh your API key or wait.")
                    return

                json_obj = {
                    "dimension": dim,
                    "overview": "ERROR: LLM call failed.",
                    "key_patterns": [],
                    "sentiment_snapshot": {
                        "positive": stats["sentiment_counts"]["positive"],
                        "negative": stats["sentiment_counts"]["negative"],
                        "average_confidence": stats["avg_confidence"],
                    },
                    "top_subthemes": top_subthemes_list,
                    "risks_and_blindspots": [],
                    "recommendations": [],
                }

            with out_path.open("w", encoding="utf-8") as f:
                json.dump(json_obj, f, ensure_ascii=False, indent=2)
            print(f"    -> wrote {out_path}")

    print("[done] All subthemes processed; dimensions summarised as requested.")


if __name__ == "__main__":
    main()
