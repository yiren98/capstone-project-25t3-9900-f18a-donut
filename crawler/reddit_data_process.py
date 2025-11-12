"""
The subthemes and evidences extraction.
Default api: Gemini. Optional api: OpenRouter/DeepSeek.
Input: crawler/reddit-crawler-master/submissions.csv
Output: data/processed/comments_reddit.csv and subthemes_reddit.txt
"""

import os
import re
import json
import time
import pandas as pd
from pathlib import Path
from collections import defaultdict, Counter

# ---- provider switch ----
# set OPEN_SUBS_PROVIDER=gemini or openrouter
PROVIDER = os.getenv("OPEN_SUBS_PROVIDER", "gemini").strip().lower()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
OR_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1:free")
OR_BASE = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# ---- paths ----
ROOT_DIR = Path(__file__).resolve().parents[1]
CSV_IN = ROOT_DIR / "crawler" / "reddit-crawler-master" / "submissions.csv"
CSV_OUT = ROOT_DIR / "data" / "processed" / "comments_reddit.csv"
DIM_TXT = ROOT_DIR / "data" / "processed" / "subthemes_reddit.txt"

# ---- runtime ----
SLEEP_SECONDS = 1.2
try:
    SLEEP_SECONDS = float(os.getenv("OPEN_SUBS_SLEEP", "1.2"))
except:
    SLEEP_SECONDS = 1.2
RETRIES = 2
try:
    RETRIES = int(os.getenv("OPEN_SUBS_RETRIES", "2"))
except:
    RETRIES = 2

# ---- prompt (exact) ----
PROMPT_SYSTEM = """
You are a strict content triage assistant.

For EACH input:
1) Detect the language; if not English, translate internally for analysis. Keep all extracted evidence in the original text.
2) Open-ended subtheme extraction (ANY company-related aspects): infer 1–8 concise subthemes (≤4 words each). Examples (non-exhaustive): Collaboration/Teamwork, Diversity, Inclusion, Belonging, Respect, Recognition, Leadership/Management, Communication, Transparency, Innovation, Safety Culture, Work-Life Balance, Career Growth, Learning & Development, Autonomy, Ethics/Compliance, Wellbeing, Psychological Safety, Compensation & Benefits, Workload/Pressure, Processes/Tools, Product Quality, Customer Experience, Environmental Impact, Community Relations, Governance, Strategy, Execution, Investment/Portfolio/Stock, Market Positioning, Brand Perception.
   For EACH subtheme, output: name, attitude (positive/negative/neutral) WITHIN that subtheme, a very short evidence snippet (verbatim, contiguous, ≤200 chars), and a confidence [0..1].
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

# ---- json extractor ----
def extract_first_json(text):
    if text is None:
        raise ValueError("Empty output")
    s = str(text).strip()
    try:
        s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.DOTALL | re.IGNORECASE)
    except:
        pass
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

# ---- normalize subs ----
def norm_subs(subs):
    out = []
    if not isinstance(subs, list):
        return out
    for d in subs:
        if isinstance(d, dict):
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
            ev = str(ev)[:200]
            item["evidence"] = ev

            try:
                conf = float(d.get("confidence", 0.0))
            except:
                conf = 0.0
            item["confidence"] = conf

            out.append(item)
    return out

# ---- evidence filter ----
AUTHOR_LIKE = re.compile(r"^[A-Za-z0-9_-]{3,}$")

def is_bad_ev(ev):
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

# ---- flatten to csv row ----
def flatten_subs(dim_list, overall_confidence):
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
    except:
        conf = 0.0
    row = {
        "subthemes": "|".join(names) if len(names) > 0 else "",
        "subs_sentiment": json.dumps(sent_map, ensure_ascii=False),
        "confidence": conf,
        "subs_evidences": json.dumps(evid_map, ensure_ascii=False),
    }
    return row

# ---- resume helper ----
def get_prev_progress(path_obj):
    if not path_obj.exists():
        return 0
    try:
        old = pd.read_csv(path_obj, dtype=str)
        return len(old)
    except:
        return 0

# ---- append one ----
def append_one_row(text_value, row_out, header_if_new):
    to_write = dict(row_out)
    to_write["text"] = text_value
    out_df = pd.DataFrame([to_write], columns=["text","subthemes","subs_sentiment","confidence","subs_evidences"])
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(CSV_OUT, mode="a", header=header_if_new, index=False, encoding="utf-8-sig")

# ---- summary ----
def rebuild_subtheme_summary():
    if not CSV_OUT.exists():
        return
    try:
        df_all = pd.read_csv(CSV_OUT, dtype=str)
    except:
        return
    if len(df_all) == 0:
        return

    agg = defaultdict(lambda: {"count":0, "attitudes":Counter(), "conf_sum":0.0, "conf_n":0, "example":""})

    idx = 0
    while idx < len(df_all):
        try:
            row = df_all.iloc[idx]
        except:
            idx += 1
            continue

        try:
            s_map = json.loads(row.get("subs_sentiment","{}"))
        except:
            s_map = {}
        if not isinstance(s_map, dict):
            s_map = {}

        try:
            e_map = json.loads(row.get("subs_evidences","{}"))
        except:
            e_map = {}
        if not isinstance(e_map, dict):
            e_map = {}

        try:
            conf = float(row.get("confidence", 0.0))
        except:
            conf = 0.0

        for dim_name in s_map.keys():
            dn = dim_name
            if dn is None:
                dn = ""
            dn = str(dn).strip()
            if dn == "":
                continue
            att = s_map.get(dim_name, "neutral")
            info = agg[dn]
            info["count"] = info["count"] + 1
            info["attitudes"][att] = info["attitudes"][att] + 1
            if conf > 0:
                info["conf_sum"] = info["conf_sum"] + conf
                info["conf_n"] = info["conf_n"] + 1
            if info["example"] == "":
                ex = e_map.get(dn, "")
                if ex:
                    info["example"] = ex
        idx += 1

    lines = []
    lines.append("Total processed rows: " + str(len(df_all)) + "\n")
    lines.append("Sub-themes Summary (sorted by count):\n")

    items = list(agg.items())
    items.sort(key=lambda kv: (-kv[1]["count"], kv[0].lower()))

    j = 0
    while j < len(items):
        name, info = items[j]
        cnt = info["count"]
        att_pairs = []
        for k, v in info["attitudes"].most_common():
            att_pairs.append(str(k) + ":" + str(v))
        att_str = ", ".join(att_pairs)
        if info["conf_n"] > 0:
            conf_avg = info["conf_sum"] / float(info["conf_n"])
        else:
            conf_avg = 0.0
        example = info["example"] if info["example"] else "—"

        lines.append("- " + name + "\n")
        lines.append("  Count: " + str(cnt) + "\n")
        lines.append("  Attitudes: " + (att_str if att_str else "N/A") + "\n")
        lines.append("  Avg Overall Confidence: " + "{:.3f}".format(conf_avg) + "\n")
        lines.append("  Example: " + example + "\n")
        j += 1

    DIM_TXT.parent.mkdir(parents=True, exist_ok=True)
    with open(DIM_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("Summary updated (" + str(len(df_all)) + " rows)")

# ---- LLM: gemini ----
def call_llm_gemini(text, retries, pause):
    try:
        from google import genai
    except:
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
            except:
                raw = ""
            if raw == "":
                raise ValueError("Empty response")
            try:
                data = json.loads(raw)
            except:
                data = extract_first_json(raw)
            if not isinstance(data, dict):
                raise ValueError("Not a dict")
            if "confidence" not in data or "subthemes_open" not in data or "reason" not in data:
                raise ValueError("JSON keys mismatch")
            subs = norm_subs(data.get("subthemes_open", []))
            out = {
                "confidence": float(data.get("confidence", 0.0)),
                "subthemes_open": subs,
                "reason": str(data.get("reason", ""))[:200]
            }
            return out
        except Exception as e:
            last_err = e
            if attempt < retries:
                print("[warn] gemini retry {}/{}: {}".format(attempt+1, retries, str(e)))
                time.sleep(pause * (attempt + 1))
                attempt += 1
                continue
            print("[fatal] gemini: " + str(e))
            return {"confidence": 0.0, "subthemes_open": [], "reason": "error:" + str(last_err)}

# ---- LLM: openrouter ----
def is_limit_error(err):
    s = str(err).lower()
    keys = ["rate limit","limit exceeded","quota","429","free-models-per","per-min","too many requests"]
    k = 0
    while k < len(keys):
        if keys[k] in s:
            return True
        k += 1
    return False

def call_llm_openrouter(text, retries, pause):
    try:
        from openai import OpenAI
    except:
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
            {"role": "user", "content": "Content:\n" + str(text)}
        ],
        "stop": ["<｜"],
    }

    last_err = None
    attempt = 0
    while attempt <= retries:
        try:
            ok = False
            try:
                resp = client.chat.completions.create(response_format={"type":"json_object"}, **kwargs)
                ok = True
            except Exception as e0:
                if is_limit_error(e0):
                    raise e0
                resp = client.chat.completions.create(**kwargs)
                ok = True

            if not ok:
                raise ValueError("no response")

            raw = ""
            try:
                raw = (resp.choices[0].message.content or "").strip()
            except:
                raw = ""

            if raw == "":
                no_stop = dict(kwargs)
                try:
                    del no_stop["stop"]
                except:
                    pass
                resp2 = client.chat.completions.create(**no_stop)
                try:
                    raw = (resp2.choices[0].message.content or "").strip()
                except:
                    raw = ""

            if raw == "":
                raise ValueError("Empty response")

            try:
                data = json.loads(raw)
            except:
                data = extract_first_json(raw)

            if not isinstance(data, dict):
                raise ValueError("Not a dict")
            if "confidence" not in data or "subthemes_open" not in data or "reason" not in data:
                raise ValueError("JSON keys mismatch")

            subs = norm_subs(data.get("subthemes_open", []))
            out = {
                "confidence": float(data.get("confidence", 0.0)),
                "subthemes_open": subs,
                "reason": str(data.get("reason", ""))[:200]
            }
            return out

        except Exception as e:
            last_err = e
            if is_limit_error(e):
                print("[fatal] openrouter limit: " + str(e))
                return {"confidence": 0.0, "subthemes_open": [], "reason": "error(limit):" + str(last_err)}
            if attempt < retries:
                sleep_s = pause * (attempt + 1)
                print("[warn] openrouter retry {}/{}: {}; sleep {}s".format(attempt+1, retries, str(e), sleep_s))
                time.sleep(sleep_s)
                attempt += 1
                continue
            print("[fatal] openrouter: " + str(e))
            return {"confidence": 0.0, "subthemes_open": [], "reason": "error:" + str(last_err)}

def call_llm(text):
    if PROVIDER == "openrouter":
        return call_llm_openrouter(text, RETRIES, SLEEP_SECONDS)
    else:
        return call_llm_gemini(text, RETRIES, SLEEP_SECONDS)

# ---- input loader ----
def load_input_df(path_obj):
    df = None
    try:
        df = pd.read_csv(path_obj, encoding="utf-8-sig", dtype=str)
    except:
        try:
            df = pd.read_csv(path_obj, dtype=str)
        except Exception as e:
            raise RuntimeError("Cannot read input: " + str(e))

    if df is None:
        raise RuntimeError("Empty input")

    cols_lower = {}
    for c in df.columns:
        cols_lower[c.lower()] = c

    if "text" in cols_lower:
        col_text = cols_lower["text"]
        df["text"] = df[col_text].fillna("").astype(str)
        return df[["text"]].copy()

    title_col = None
    content_col = None
    if "title" in cols_lower:
        title_col = cols_lower["title"]
    if "content" in cols_lower:
        content_col = cols_lower["content"]
    elif "selftext" in cols_lower:
        content_col = cols_lower["selftext"]
    elif "body" in cols_lower:
        content_col = cols_lower["body"]

    if title_col is None and content_col is None:
        raise RuntimeError("Need 'text' or Title/Content columns")

    if title_col is None:
        title_series = None
    else:
        title_series = df[title_col].fillna("").astype(str)

    if content_col is None:
        content_series = None
    else:
        content_series = df[content_col].fillna("").astype(str)

    if title_series is None and content_series is not None:
        out_series = content_series
    elif content_series is None and title_series is not None:
        out_series = title_series
    else:
        out_series = (title_series.str.strip() + " — " + content_series.str.strip()).str.strip(" —")

    out = pd.DataFrame({"text": out_series})
    return out

# ---- main ----
def main():
    df = load_input_df(CSV_IN)
    df["text"] = df["text"].fillna("").astype(str)
    df["Content"] = df["text"]

    n_done = get_prev_progress(CSV_OUT)
    start_idx = n_done
    header_if_new = (n_done == 0)

    if start_idx >= len(df):
        print("All done (" + str(n_done) + " rows).")
        rebuild_subtheme_summary()
        return

    print("[provider=" + PROVIDER + "] Resume at " + str(start_idx+1) + "/" + str(len(df)) + " (done=" + str(n_done) + ").")

    try:
        smoke_text = df.iloc[start_idx]["Content"]
        smoke = call_llm(smoke_text)
        subs_n = 0
        try:
            subs_n = len(smoke.get("subthemes_open", []))
        except:
            subs_n = 0
        print("[smoke] overall_confidence=", smoke.get("confidence", 0.0), "subs_n=", subs_n)
    except Exception as e:
        print("[smoke warn]", str(e))

    try:
        i = start_idx
        while i < len(df):
            text_i = df.iloc[i]["Content"]
            r = call_llm(text_i)

            subs = r.get("subthemes_open", [])
            subs_valid = validate_subs_against_text(subs, text_i)
            flat = flatten_subs(subs_valid, r.get("confidence", 0.0))
            flat["text"] = text_i

            append_one_row(text_i, flat, header_if_new)
            header_if_new = False

            if ((i + 1) % 10 == 0) or ((i + 1) == len(df)):
                print("Processed " + str(i+1) + "/" + str(len(df)))

            time.sleep(SLEEP_SECONDS)
            i += 1

        print("Done.")
        rebuild_subtheme_summary()

    except KeyboardInterrupt:
        print("Interrupted. Progress saved.")
        rebuild_subtheme_summary()
    except Exception as e:
        print("[fatal] " + repr(e))
        rebuild_subtheme_summary()

if __name__ == "__main__":
    if PROVIDER == "gemini" and not os.getenv("GOOGLE_API_KEY"):
        print("GOOGLE_API_KEY missing (PROVIDER=gemini).")
    if PROVIDER == "openrouter" and not os.getenv("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY missing (PROVIDER=openrouter).")
    main()
