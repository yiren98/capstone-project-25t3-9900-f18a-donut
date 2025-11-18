# data_process_llm.py
# LLM helper module used by data_process.py.
# Handles provider config, prompt text, JSON extraction and LLM calls.
# This file is not meant to be run as a script.

import os
import re
import json
import time

# ---- provider switch ----
# Set OPEN_SUBS_PROVIDER=gemini or openrouter
PROVIDER = os.getenv("OPEN_SUBS_PROVIDER", "gemini").strip().lower()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
OR_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1:free")
OR_BASE = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# ---- runtime config ----
SLEEP_SECONDS = 1.2
try:
    SLEEP_SECONDS = float(os.getenv("OPEN_SUBS_SLEEP", "1.2"))
except Exception:
    SLEEP_SECONDS = 1.2

RETRIES = 2
try:
    RETRIES = int(os.getenv("OPEN_SUBS_RETRIES", "2"))
except Exception:
    RETRIES = 2

# ---- prompt for subthemes extraction ----
PROMPT_SYSTEM = """
You are a strict content triage assistant.

For EACH input:
1) Detect the language; if not English, translate internally for analysis. Keep all extracted evidence in the original text.
2) If the content is NOT related to Rio Tinto (the mining company or its business context, including subsidiaries or abbreviations such as "RIO"), output a single dimension:
   [{"name": "Non-Company", "attitude": "neutral", "evidence": "", "confidence": 1.0}]
   and skip further extraction.
   Otherwise, perform open-ended dimension extraction (ANY company-related aspects): infer 1–8 concise dimensions (≤4 words each).
   Examples (non-exhaustive): Collaboration/Teamwork, Diversity, Inclusion, Belonging, Respect, Recognition, Leadership/Management,
   Communication, Transparency, Innovation, Safety Culture, Work-Life Balance, Career Growth, Learning & Development, Autonomy,
   Ethics/Compliance, Wellbeing, Psychological Safety, Compensation & Benefits, Workload/Pressure, Processes/Tools, Product Quality,
   Customer Experience, Environmental Impact, Community Relations, Governance, Strategy, Execution, Investment/Portfolio/Stock,
   Market Positioning, Brand Perception.
   For EACH dimension, output: name, attitude (positive/negative/neutral) WITHIN that dimension, a very short evidence snippet
   (verbatim, contiguous, ≤200 chars), and a confidence [0..1].
3) Be conservative: lower confidence if unsure.
4) Do NOT invent evidence; if no suitable contiguous substring exists, set evidence to "".

Return ONLY one valid minified JSON object (no extra text, no code fences, no explanations).
The JSON keys MUST be exactly:
- confidence (number; your overall confidence in this extraction)
- subthemes_open (array of objects with keys: name, attitude, evidence, confidence)
- reason (short string)

The evidence MUST be a verbatim, contiguous substring copied from the input field Content.
"""

STOP_TOKENS = ["<｜", "<|", "```"]

# ---- JSON extractor for LLM output ----
def extract_first_json(text):
    """Extract the first JSON object from a text response and parse it."""
    if text is None:
        raise ValueError("Empty output")

    s = str(text).strip()
    try:
        # Remove ```json ... ``` fences if present
        s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.DOTALL | re.IGNORECASE)
    except Exception:
        pass

    # Cut off at stop tokens if the model returned extra content
    for tok in STOP_TOKENS:
        if tok in s:
            parts = s.split(tok, 1)
            s = parts[0].strip()

    start = s.find("{")
    if start == -1:
        raise ValueError("No JSON object")

    depth = 0
    in_str = False
    esc = False
    end = -1
    i = start

    while i < len(s):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            else:
                if ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        i += 1

    if end == -1:
        raise ValueError("Unbalanced braces")

    core = s[start:end]
    return json.loads(core)

# ---- normalise subtheme list from LLM ----
def norm_subs(subs):
    """Normalise the list of subthemes from the LLM into a clean list of dicts."""
    out = []
    if not isinstance(subs, list):
        return out

    for d in subs:
        if not isinstance(d, dict):
            continue

        item = {}

        name = d.get("name", "")
        if name is None:
            name = ""
        item["name"] = str(name).strip()[:60]

        att = d.get("attitude", "neutral")
        if att is None:
            att = "neutral"
        item["attitude"] = str(att)

        ev = d.get("evidence", "")
        if ev is None:
            ev = ""
        item["evidence"] = str(ev)[:200]

        try:
            conf = float(d.get("confidence", 0.0))
        except Exception:
            conf = 0.0
        item["confidence"] = conf

        out.append(item)

    return out

# ---- evidence filter helpers ----
AUTHOR_LIKE = re.compile(r"^[A-Za-z0-9_-]{3,}$")

def is_bad_ev(ev):
    """Return True if the evidence string looks invalid for our use."""
    if not ev:
        return True
    if ev.startswith("http"):
        return True
    if len(ev) < 2:
        return True
    if AUTHOR_LIKE.match(ev):
        return True
    return False

def validate_subs_against_text(dim_list, text):
    """
    Filter subthemes whose evidence is not a good substring of the original text.
    Keep only items where evidence is valid and appears in the text.
    """
    ok = []
    t = text if text is not None else ""
    for d in dim_list:
        if not isinstance(d, dict):
            continue
        ev = d.get("evidence", "")
        if not ev:
            continue
        if is_bad_ev(ev):
            continue
        if ev not in t:
            continue
        ok.append(d)
    return ok

# ---- flatten subthemes into CSV row fields ----
def flatten_subs(dim_list, overall_confidence):
    """
    Convert the list of subthemes into flat CSV fields.
    Returns:
      {
        "subthemes": "...",
        "subs_sentiment": "{...}",
        "confidence": float,
        "subs_evidences": "{...}",
      }
    """
    names = []
    sent_map = {}
    evid_map = {}

    if isinstance(dim_list, list):
        for d in dim_list:
            nm = d.get("name", "")
            if nm is None:
                nm = ""
            nm = str(nm).strip()
            if nm == "":
                continue
            names.append(nm)

            att = d.get("attitude", "neutral")
            if att is None:
                att = "neutral"
            sent_map[nm] = str(att)

            ev = d.get("evidence", "")
            if ev:
                evid_map[nm] = str(ev)[:200]

    try:
        conf = float(overall_confidence)
    except Exception:
        conf = 0.0

    row = {
        "subthemes": "|".join(names) if names else "",
        "subs_sentiment": json.dumps(sent_map, ensure_ascii=False),
        "confidence": conf,
        "subs_evidences": json.dumps(evid_map, ensure_ascii=False),
    }
    return row

# ---- error classifier for OpenRouter ----
def is_limit_error(err):
    """Return True if an exception message looks like a rate-limit or quota error."""
    s = str(err).lower()
    keys = [
        "rate limit",
        "limit exceeded",
        "quota",
        "429",
        "free-models-per",
        "per-min",
        "too many requests",
    ]
    for k in keys:
        if k in s:
            return True
    return False

# ---- LLM: Gemini ----
def call_llm_gemini(text, retries, pause):
    """Call Gemini to extract subthemes for a single text field."""
    try:
        from google import genai
    except Exception:
        return {"confidence": 0.0, "subthemes_open": [], "reason": "gemini import error"}

    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if api_key == "":
        return {"confidence": 0.0, "subthemes_open": [], "reason": "no GOOGLE_API_KEY"}

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        return {"confidence": 0.0, "subthemes_open": [], "reason": "client error: " + str(e)}

    prompt = PROMPT_SYSTEM + "\n\nContent:\n" + str(text)
    last_err = None
    attempt = 0

    while attempt <= retries:
        try:
            resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            raw = ""
            try:
                raw = (resp.text or "").strip()
            except Exception:
                raw = ""
            if raw == "":
                raise ValueError("Empty response")

            try:
                data = json.loads(raw)
            except Exception:
                data = extract_first_json(raw)

            if not isinstance(data, dict):
                raise ValueError("Not a dict")
            if "confidence" not in data or "subthemes_open" not in data or "reason" not in data:
                raise ValueError("JSON keys mismatch")

            subs = norm_subs(data.get("subthemes_open", []))
            out = {
                "confidence": float(data.get("confidence", 0.0)),
                "subthemes_open": subs,
                "reason": str(data.get("reason", ""))[:200],
            }
            return out

        except Exception as e:
            last_err = e
            if attempt < retries:
                print(f"[warn] gemini retry {attempt + 1}/{retries}: {e}")
                time.sleep(pause * (attempt + 1))
                attempt += 1
                continue
            print("[fatal] gemini:", e)
            return {"confidence": 0.0, "subthemes_open": [], "reason": "error:" + str(last_err)}

# ---- LLM: OpenRouter (DeepSeek) ----
def call_llm_openrouter(text, retries, pause):
    """Call OpenRouter (DeepSeek) to extract subthemes for a single text field."""
    try:
        from openai import OpenAI
    except Exception:
        return {"confidence": 0.0, "subthemes_open": [], "reason": "openai import error"}

    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if api_key == "":
        return {"confidence": 0.0, "subthemes_open": [], "reason": "no OPENROUTER_API_KEY"}

    try:
        client = OpenAI(base_url=OR_BASE, api_key=api_key, timeout=120.0)
    except Exception as e:
        return {"confidence": 0.0, "subthemes_open": [], "reason": "client error: " + str(e)}

    kwargs = {
        "model": OR_MODEL,
        "temperature": 0.0,
        "max_tokens": 700,
        "messages": [
            {"role": "system", "content": PROMPT_SYSTEM},
            {"role": "user", "content": "Content:\n" + str(text)},
        ],
        "stop": ["<｜"],
    }

    last_err = None
    attempt = 0

    while attempt <= retries:
        try:
            ok = False
            try:
                # Try json_object format first
                resp = client.chat.completions.create(
                    response_format={"type": "json_object"},
                    **kwargs,
                )
                ok = True
            except Exception as e0:
                if is_limit_error(e0):
                    raise e0
                # Fallback: normal text response
                resp = client.chat.completions.create(**kwargs)
                ok = True

            if not ok:
                raise ValueError("no response")

            raw = ""
            try:
                raw = (resp.choices[0].message.content or "").strip()
            except Exception:
                raw = ""

            if raw == "":
                # Second try without stop tokens
                no_stop = dict(kwargs)
                try:
                    del no_stop["stop"]
                except Exception:
                    pass
                resp2 = client.chat.completions.create(**no_stop)
                try:
                    raw = (resp2.choices[0].message.content or "").strip()
                except Exception:
                    raw = ""

            if raw == "":
                raise ValueError("Empty response")

            try:
                data = json.loads(raw)
            except Exception:
                data = extract_first_json(raw)

            if not isinstance(data, dict):
                raise ValueError("Not a dict")
            if "confidence" not in data or "subthemes_open" not in data or "reason" not in data:
                raise ValueError("JSON keys mismatch")

            subs = norm_subs(data.get("subthemes_open", []))
            out = {
                "confidence": float(data.get("confidence", 0.0)),
                "subthemes_open": subs,
                "reason": str(data.get("reason", ""))[:200],
            }
            return out

        except Exception as e:
            last_err = e
            if is_limit_error(e):
                print("[fatal] openrouter limit:", e)
                return {
                    "confidence": 0.0,
                    "subthemes_open": [],
                    "reason": "error(limit):" + str(last_err),
                }
            if attempt < retries:
                sleep_s = pause * (attempt + 1)
                print(f"[warn] openrouter retry {attempt + 1}/{retries}: {e}; sleep {sleep_s}s")
                time.sleep(sleep_s)
                attempt += 1
                continue
            print("[fatal] openrouter:", e)
            return {"confidence": 0.0, "subthemes_open": [], "reason": "error:" + str(last_err)}

# ---- public entry for LLM call ----
def call_llm(text):
    """Public helper used by data_process.main to call the right provider."""
    if PROVIDER == "openrouter":
        return call_llm_openrouter(text, RETRIES, SLEEP_SECONDS)
    return call_llm_gemini(text, RETRIES, SLEEP_SECONDS)
