import csv
from flask import jsonify, request, abort, session
from werkzeug.security import check_password_hash, generate_password_hash

from config import (
    USERS_DIR, USERS_CSV, REDDIT_DB,
    SR_OVERALL, SR_DIM_DIR, SR_SUB_DIR, SR_MAP_CSV, MAP_CSV
)
from utils import (
    _s, _split_pipes, _json_try, _to_ymd_series, _normalize_parent_id,
    _read_sql, _read_csv_safe, _slugify, _is_valid_email
)
from models import (
    load_posts, load_comments_by_tag, load_sbi_info, load_sbi_table,
    _read_json_file, _load_mapping, _read_mapping_exploded, _load_users
)

def register_routes(app):
    # ----- Health -----
    @app.get("/health")
    def health():
        return jsonify({"ok": True})

    # ----- Culture Analysis APIs -----
    @app.get("/api/ca/overall")
    def ca_overall():
        data = _read_json_file(SR_OVERALL)
        if data is None:
            abort(404, f"overall_sr.json not found at {SR_OVERALL}")
        return jsonify(data)

    @app.get("/api/ca/dimension/<name>")
    def ca_dimension(name):
        slug = _slugify(name)
        cand = [SR_DIM_DIR / f"{slug}.json", SR_DIM_DIR / f"{name}.json"]
        for p in cand:
            data = _read_json_file(p)
            if data is not None:
                return jsonify(data)
        abort(404, f"dimension '{name}' not found in {SR_DIM_DIR}")

    @app.get("/api/ca/subthemes")
    def ca_subthemes():
        dim = request.args.get("dimension", "").strip()
        m = _load_mapping()
        subs = m["by_dim"].get(dim, [])
        seen, out = set(), []
        for s in subs:
            if s["name"] in seen:
                continue
            seen.add(s["name"])
            out.append(s)
        return jsonify({"dimension": dim, "subthemes": out})

    @app.get("/api/ca/subtheme/by-file/<path:filename>")
    def ca_subtheme_by_file(filename):
        p = (SR_SUB_DIR / filename).resolve()
        data = _read_json_file(p)
        if data is None:
            abort(404, f"subtheme file '{filename}' not found in {SR_SUB_DIR}")
        return jsonify(data)

    @app.get("/api/ca/index")
    def ca_index():
        m = _load_mapping()
        dims = sorted(m["by_dim"].keys())
        if not dims:
            dims = [p.stem.replace("_"," ").title() for p in SR_DIM_DIR.glob("*.json")]
        return jsonify({
            "dimensions": dims,
            "subtheme_count_by_dim": {k: len(v) for k, v in m["by_dim"].items()}
        })

    # ----- SBI -----
    @app.get("/api/sbi")
    def api_sbi():
        year = request.args.get("year", type=int)
        if not year:
            return jsonify({"code": 400, "message": "year is required"}), 400
        month = request.args.get("month", type=int)
        info = load_sbi_info(year, month)
        return jsonify(info)

    @app.get("/api/sbi/years")
    def api_sbi_years():
        t = load_sbi_table()
        years = sorted(t["year"].unique().tolist())
        return jsonify({"years": years})

    # ----- Sentiment Aggregate -----
    @app.get("/api/sentiment_stats")
    def api_sentiment_stats():
        posts = load_posts().copy()

        y = request.args.get("year", type=int)
        m = request.args.get("month", type=int)
        if y or m:
            tt = pd.to_datetime(posts["time"], errors="coerce", utc=False, format="mixed")
            posts = posts.assign(_y=tt.dt.year, _m=tt.dt.month)
            if y:
                posts = posts[posts["_y"] == y]
            if m:
                posts = posts[posts["_m"] == m]

        dim = (request.args.get("dimension") or "").strip()
        if dim:
            posts = posts[posts["dimensions"].apply(lambda arr: isinstance(arr, list) and dim in arr)]

        only_sub = (request.args.get("subtheme") or "").strip()

        pos = 0
        neg = 0
        for _, r in posts.iterrows():
            ss = r.get("subs_sentiment")
            if not isinstance(ss, dict):
                continue
            if only_sub:
                val = str(ss.get(only_sub, "")).lower().strip()
                if val == "positive":
                    pos += 1
                elif val == "negative":
                    neg += 1
            else:
                for v in ss.values():
                    vv = str(v).lower().strip()
                    if vv == "positive":
                        pos += 1
                    elif vv == "negative":
                        neg += 1

        return jsonify({"positive": int(pos), "negative": int(neg)})

    # ----- Dimension / Subtheme counts -----
    import pandas as pd  # local import to avoid circulars
    @app.get("/api/dimension_counts")
    def api_dimension_counts():
        year  = request.args.get("year", type=int)
        month = request.args.get("month", type=int)

        def from_db(y=None, m=None):
            posts = load_posts().copy()
            if y or m:
                tt = pd.to_datetime(posts["time"], errors="coerce", utc=False, format="mixed")
                posts = posts.assign(_y=tt.dt.year, _m=tt.dt.month)
                if y: posts = posts[posts["_y"] == y]
                if m: posts = posts[posts["_m"] == m]

            rows = []
            for _, r in posts.iterrows():
                dims = r.get("dimensions")
                if isinstance(dims, list):
                    for d in dims:
                        if d: rows.append({"dimension": str(d)})
            if not rows:
                return []
            df = pd.DataFrame(rows)
            g = df.groupby("dimension", as_index=False).size().rename(columns={"size": "count"})
            g = g.sort_values("count", ascending=False)
            return [{"name": str(r["dimension"]), "count": int(r["count"])} for _, r in g.iterrows()]

        if year or month:
            return jsonify(from_db(year, month))

        try:
            df = _read_csv_safe(DIM_CSV if isinstance(DIM_CSV, Path) else Path(DIM_CSV))
            cols = {c.lower(): c for c in df.columns}
            dim_col = cols.get("dimension") or cols.get("dimensions") or cols.get("dim")
            cnt_col = cols.get("count") or cols.get("counts") or cols.get("value") or cols.get("total")
            if dim_col and cnt_col:
                g = df.groupby(dim_col, as_index=False)[cnt_col].sum().sort_values(cnt_col, ascending=False)
                return jsonify([{"name": str(r[dim_col]), "count": int(r[cnt_col])} for _, r in g.iterrows()])
        except Exception:
            pass

        return jsonify(from_db())

    @app.get("/api/subtheme_counts")
    def api_subtheme_counts():
        dim   = (request.args.get("dimension") or "").strip()
        year  = request.args.get("year", type=int)
        month = request.args.get("month", type=int)

        map_df = _read_mapping_exploded(SR_MAP_CSV, MAP_CSV)
        map_df["subtheme"] = map_df["subtheme"].astype(str).str.strip()
        map_df["dimension"] = map_df["dimension"].astype(str).str.strip()

        allowed_subs = None
        if dim:
            allowed_subs = set(map_df.loc[map_df["dimension"] == dim, "subtheme"].unique().tolist())

        posts = load_posts().copy()
        if year or month:
            tt = pd.to_datetime(posts["time"], errors="coerce", utc=False, format="mixed")
            posts = posts.assign(_y=tt.dt.year, _m=tt.dt.month)
            if year:  posts = posts[posts["_y"] == year]
            if month: posts = posts[posts["_m"] == month]

        if dim:
            posts = posts[posts["dimensions"].apply(lambda arr: isinstance(arr, list) and dim in arr)]

        counter = {}
        def bump(name: str):
            name = (name or "").strip()
            if not name:
                return
            if allowed_subs is not None and name not in allowed_subs:
                return
            counter[name] = counter.get(name, 0) + 1

        for _, r in posts.iterrows():
            ss = r.get("subs_sentiment")
            used = False
            if isinstance(ss, dict) and ss:
                for k in ss.keys():
                    bump(str(k))
                    used = True
            if not used:
                subs = r.get("subthemes")
                if isinstance(subs, list):
                    for k in subs:
                        bump(str(k))

        out = [{"name": k, "count": int(v)} for k, v in counter.items()]
        out.sort(key=lambda x: x["count"], reverse=True)
        return jsonify(out)

    # ----- Posts listing -----
    @app.get("/api/posts")
    def api_posts():
        posts = load_posts()

        # Fill comment_count from DB if not provided in file
        if posts["comment_count_file"].isna().all():
            forum_tags = posts[posts["type"] == "forum"]["tag"].tolist()
            if forum_tags:
                placeholders = ",".join(["?"] * len(forum_tags))
                sql = f"SELECT Tag, COUNT(1) AS cnt FROM reddit WHERE Tag IN ({placeholders}) GROUP BY Tag"
                cdf = _read_sql(REDDIT_DB, sql, tuple(forum_tags))
                cmt_map = dict(zip(cdf["Tag"].astype(str), cdf["cnt"].astype(int)))
            else:
                cmt_map = {}
            posts = posts.assign(
                comment_count=posts.apply(
                    lambda r: int(cmt_map.get(str(r["tag"]), 0)) if r["type"] == "forum" else 0, axis=1
                )
            )
        else:
            posts = posts.assign(
                comment_count=posts.apply(
                    lambda r: int(r["comment_count_file"] or 0) if r["type"] == "forum" else 0, axis=1
                )
            )

        # Filters
        import pandas as pd
        y = request.args.get("year", type=int)
        m = request.args.get("month", type=int)
        if y or m:
            tt = pd.to_datetime(posts["time"], errors="coerce", utc=False, format="mixed")
            posts = posts.assign(_y=tt.dt.year, _m=tt.dt.month)
            if y: posts = posts[posts["_y"] == y]
            if m: posts = posts[posts["_m"] == m]

        dim = (request.args.get("dimension") or "").strip()
        sub = (request.args.get("subtheme") or "").strip()
        sent = (request.args.get("sentiment") or "").strip().lower()  # "positive"/"negative" / ""

        if dim:
            posts = posts[posts["dimensions"].apply(lambda arr: isinstance(arr, list) and dim in arr)]

        if sub:
            def has_subtheme(r):
                ss = r.get("subs_sentiment")
                if isinstance(ss, dict) and sub in ss:
                    if sent in ("positive", "negative"):
                        return str(ss.get(sub, "")).lower().strip() == sent
                    return True
                subs = r.get("subthemes")
                if isinstance(subs, list) and sub in subs:
                    if sent in ("positive", "negative"):
                        return True
                    return True
                return False
            posts = posts[posts.apply(has_subtheme, axis=1)]
        elif sent in ("positive", "negative"):
            def has_sentiment_any(r):
                ss = r.get("subs_sentiment")
                if not isinstance(ss, dict):
                    return False
                return any(str(v).lower().strip() == sent for v in ss.values())
            posts = posts[posts.apply(has_sentiment_any, axis=1)]

        q = (request.args.get("q") or "").strip().lower()
        if q:
            posts = posts[
                posts["title"].str.lower().str.contains(q, na=False)
                | posts["content"].str.lower().str.contains(q, na=False)
                | posts["author"].str.lower().str.contains(q, na=False)
                | posts["source"].str.lower().str.contains(q, na=False)
                | posts["dimensions"].apply(lambda arr: any(q in d.lower() for d in (arr or [])))
            ]

        # Pagination
        try:
            page = max(1, int(request.args.get("page", 1)))
            size = min(100, max(1, int(request.args.get("size", 10))))
        except Exception:
            page, size = 1, 10

        start, end = (page - 1) * size, (page - 1) * size + size
        page_df = posts.iloc[start:end].copy()

        items = [{
            "id": _s(r["id"]),
            "tag": _s(r["tag"]),
            "title": _s(r["title"]),
            "author": _s(r["author"]),
            "time": _s(r["time"]),
            "score": int(r["score"]),
            "comment_count": int(r["comment_count"]),
            "is_post": bool(r["type"] == "forum"),
            "type": _s(r["type"]),
            "source": _s(r["source"]),
            "dimensions": list(r["dimensions"] or []),
        } for _, r in page_df.iterrows()]

        return jsonify({"total": int(len(posts)), "page": page, "size": size, "items": items})

    # ----- Post detail -----
    @app.get("/api/posts/<post_id>")
    def api_post_detail(post_id: str):
        posts = load_posts()
        row = posts[(posts["id"] == str(post_id)) | (posts["tag"] == str(post_id))].head(1)
        if row.empty:
            abort(404, description=f"post {post_id} not found")
        r = row.iloc[0]
        data = {
            "id": _s(r["id"]),
            "tag": _s(r["tag"]),
            "title": _s(r["title"]),
            "content": _s(r["content"]),
            "author": _s(r["author"]),
            "time": _s(r["time"]),
            "score": int(r["score"]),
            "source": _s(r["source"]),
            "type": _s(r["type"]),
            "is_post": bool(r["type"] == "forum"),
            "dimensions": list(r["dimensions"] or []),
            "subthemes": list(r["subthemes"] or []),
            "subs_sentiment": r["subs_sentiment"] if isinstance(r["subs_sentiment"], dict) else {},
        }
        return jsonify(data)

    # ----- Post comments -----
    @app.get("/api/posts/<post_id>/comments")
    def api_post_comments(post_id: str):
        posts = load_posts()
        row = posts[(posts["id"] == str(post_id)) | (posts["tag"] == str(post_id))].head(1)
        if row.empty:
            abort(404, description=f"post {post_id} not found")
        r = row.iloc[0]

        if str(r["type"]) != "forum":
            return jsonify({"total": 0, "page": 1, "size": 100, "items": []})

        tag = _s(r["tag"])
        df = load_comments_by_tag(tag).copy()

        import pandas as pd
        df["level"] = df["depth"].apply(lambda d: 1 if int(d) == 0 else 2)
        try:
            t = pd.to_datetime(df["time"], errors="coerce", utc=False, format="mixed")
            df = df.assign(_t=t)
        except Exception:
            df = df.assign(_t=pd.NaT)

        parents = df[df["level"] == 1].sort_values(by=["score", "_t"], ascending=[False, False])
        total_parents = int(len(parents))

        try:
            page = max(1, int(request.args.get("page", 1)))
            size = min(10000, max(1, int(request.args.get("size", 10))))
        except Exception:
            page, size = 1, 10

        start, end = (page - 1) * size, (page - 1) * size + size
        page_parents = parents.iloc[start:end].copy()

        parent_ids = set(page_parents["comment_id"].map(_normalize_parent_id))
        df["comment_id_norm"] = df["comment_id"].map(_normalize_parent_id)
        children = df[(df["level"] == 2) & (df["parent_id_norm"].isin(parent_ids))].copy()

        ordered = []
        pmap = { _normalize_parent_id(r["comment_id"]): r for _, r in page_parents.iterrows() }
        grouped = {pid: [] for pid in parent_ids}
        for _, cr in children.iterrows():
            grouped.setdefault(cr["parent_id_norm"], []).append(cr)
        for pid, pr in pmap.items():
            ordered.append(pr)
            for cr in grouped.get(pid, []):
                ordered.append(cr)

        import pandas as pd
        items = [{
            "comment_id": _s(r["comment_id"]),
            "comment_id_norm": _s(r.get("comment_id_norm", _normalize_parent_id(r["comment_id"]))),
            "author": _s(r["author"]),
            "content": _s(r["content"]),
            "score": int(r["score"]),
            "time": _s(r["time"]),
            "depth": int(r["depth"]),
            "level": int(r["level"]),
            "parent_id": _s(r["parent_id"]),
            "parent_comment_id_norm": _s(r["parent_id_norm"]),
        } for _, r in pd.DataFrame(ordered).iterrows()]

        return jsonify({"total": total_parents, "page": page, "size": size, "items": items})

    # ----- Auth -----
    @app.post("/api/login")
    def api_login():
        data = request.get_json(silent=True) or {}
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", "")).strip()
        remember = bool(data.get("remember", False))
        if not email or not password:
            return jsonify({"message": "Email and password are required"}), 400
        users = _load_users()
        user_row = users.get(email)
        # support hash or plain password (compat with original)
        ok = False
        if user_row:
            if user_row.get("password_hash"):
                try:
                    ok = check_password_hash(user_row["password_hash"], password)
                except Exception:
                    ok = False
            elif user_row.get("password") is not None:
                ok = (user_row["password"] == password)
        if not user_row or not ok:
            return jsonify({"message": "Invalid credentials"}), 401
        session["user"] = {"email": user_row["email"], "name": user_row["name"], "role": user_row["role"]}
        session.permanent = bool(remember)
        return jsonify({"message": "Login success", "user": session["user"]}), 200

    @app.post("/api/logout")
    def api_logout():
        session.pop("user", None)
        return jsonify({"message": "Logged out"}), 200

    @app.get("/api/me")
    def api_me():
        user = session.get("user")
        if not user:
            return jsonify({"message": "Unauthorized"}), 401
        return jsonify({"user": user}), 200

    @app.post("/api/register")
    def api_register():
        data = request.get_json(silent=True) or {}
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", "")).strip()
        name = (str(data.get("name", "")).strip() or email.split("@")[0])
        role = (str(data.get("role", "")).strip() or "user")
        if not email or not password:
            return jsonify({"message": "Email and password are required"}), 400
        if not _is_valid_email(email):
            return jsonify({"message": "Invalid email format"}), 400
        if len(password) < 6:
            return jsonify({"message": "Password must be at least 6 characters"}), 400
        users = _load_users()
        if email in users:
            return jsonify({"message": "Email already registered"}), 409
        USERS_DIR.mkdir(parents=True, exist_ok=True)
        password_hash = generate_password_hash(password)
        file_exists = USERS_CSV.exists()
        with open(USERS_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["email", "password_hash", "name", "role"])
            if not file_exists:
                writer.writeheader()
            writer.writerow({"email": email, "password_hash": password_hash, "name": name, "role": role})
        session["user"] = {"email": email, "name": name, "role": role}
        return jsonify({"message": "Register success", "user": session["user"]}), 201
