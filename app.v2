
from pathlib import Path
import zipfile
import pandas as pd
import numpy as np
import streamlit as st

VERSION = "120_CORE_DECISION_ENGINE_V1_1_CLOUD_SAFE_2026_06_28"

SIGNAL_FILES = [
    "01_TOP_OVERALL_SIGNALS.csv",
    "02_TOP_PER_CORE_SIGNALS.csv",
    "03_TOP_PER_STREAM_SIGNALS.csv",
    "04_TOP_PER_MEMBER_SIGNALS.csv",
    "05_TOP_PAIR_COMBO_SIGNALS.csv",
]

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "INPUTS"
OUTPUTS = ROOT / "OUTPUTS"
INPUTS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)

CORE_COLS = ["core", "candidate_core", "chosen_core"]
STREAM_COLS = ["stream", "StreamName", "stream_name"]
DATE_COLS = ["date", "PLAY_DATE", "DrawDate"]
SCORE_COLS = ["FinalScore", "final_score", "CoreAffinityScore_NOT_READY", "StreamRankScore"]

def read_csv_any(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, low_memory=False, encoding="utf-8-sig")

def to_num(x, default=0.0):
    try:
        if pd.isna(x): return default
        return float(x)
    except Exception:
        return default

def first_existing(df, candidates):
    lower = {str(c).lower(): c for c in df.columns}
    for c in candidates:
        if c in df.columns: return c
        if str(c).lower() in lower: return lower[str(c).lower()]
    return ""

def classify_action(lift):
    lift = to_num(lift, 1)
    if lift >= 1.25: return "PROMOTE"
    if lift <= 0.75: return "SUPPRESS"
    return "IGNORE"

def score_signal(row):
    lift = to_num(row.get("lift", 1), 1)
    rows = to_num(row.get("rows", 0), 0)
    wins = to_num(row.get("winner_rows", 0), 0)
    rate = to_num(row.get("winner_rate", 0), 0)
    action = classify_action(lift)
    if action == "IGNORE": return 0.0
    base = np.log(max(lift, 1e-12)) * 10
    support = min(np.log1p(rows) / 10, 1.5)
    win_support = min(np.log1p(wins) / 5, 1.5)
    purity = min(rate * 100, 5)
    raw = base * (0.45 + 0.25 * support + 0.25 * win_support) + purity
    return round(raw if action == "PROMOTE" else -abs(raw), 6)

def build_rule_db_from_signal_folder(input_dir: Path):
    rows = []
    for fname in SIGNAL_FILES:
        p = input_dir / fname
        if not p.exists():
            continue
        df = read_csv_any(p)
        for _, r in df.iterrows():
            d = r.to_dict()
            action = classify_action(d.get("lift", 1))
            if action == "IGNORE": continue
            score = score_signal(d)
            if abs(score) < 0.5: continue
            rows.append({
                "source_file": fname,
                "action": action,
                "scope": d.get("scope", "overall"),
                "scope_value": d.get("scope_value", ""),
                "signal": d.get("signal", ""),
                "value": d.get("value", ""),
                "lift": to_num(d.get("lift", 1), 1),
                "rows": int(to_num(d.get("rows", 0), 0)),
                "winner_rows": int(to_num(d.get("winner_rows", 0), 0)),
                "winner_rate": to_num(d.get("winner_rate", 0), 0),
                "score_delta": score,
                "enabled": 1,
            })
    out = pd.DataFrame(rows)
    if out.empty: return out
    out = out.drop_duplicates(subset=["scope", "scope_value", "signal", "value", "action"])
    out = out.sort_values(["action", "score_delta", "winner_rows", "rows"], ascending=[True, False, False, False])
    out.insert(0, "rule_id", [f"R{i+1:05d}" for i in range(len(out))])
    return out

def split_combo(signal, value):
    sigs = str(signal).split("+")
    vals = str(value).split("|")
    if len(sigs) > 1 and len(sigs) == len(vals):
        return [(s.strip(), v.strip()) for s, v in zip(sigs, vals)]
    return [(str(signal).strip(), str(value).strip())]

def match_value(candidate_value, rule_value):
    cv = str(candidate_value).strip()
    rv = str(rule_value).strip()
    try:
        x = float(cv)
        if rv.startswith("<="): return x <= float(rv[2:])
        if rv.startswith(">="): return x >= float(rv[2:])
        if rv.startswith("<"): return x < float(rv[1:])
        if rv.startswith(">"): return x > float(rv[1:])
    except Exception:
        pass
    return cv == rv

def rule_matches(row, rule):
    scope = str(rule.get("scope", "overall"))
    scope_value = str(rule.get("scope_value", "")).strip()
    if scope == "core" and scope_value:
        core_val = str(row.get("core", row.get("candidate_core", row.get("chosen_core", "")))).strip()
        if core_val != scope_value: return False
    if scope == "stream" and scope_value:
        stream_val = str(row.get("stream", row.get("StreamName", row.get("stream_name", "")))).strip()
        if stream_val != scope_value: return False
    if scope == "member_top1" and scope_value:
        member_val = str(row.get("member_top1", row.get("chosen_member", row.get("member", "")))).strip()
        if member_val != scope_value: return False
    for sig, val in split_combo(rule.get("signal", ""), rule.get("value", "")):
        if sig not in row: return False
        if not match_value(row.get(sig, ""), val): return False
    return True

def score_candidates(candidate_df, rule_df):
    if candidate_df.empty: return candidate_df.copy()
    rules = rule_df.copy()
    if not rules.empty and "enabled" in rules.columns:
        rules = rules[rules["enabled"].astype(str).str.lower().isin(["1", "1.0", "true", "yes"])]
    score_col = first_existing(candidate_df, SCORE_COLS)
    scored_rows = []
    for _, row in candidate_df.iterrows():
        d = row.to_dict()
        score = to_num(d.get(score_col, 0), 0) if score_col else 0
        fired = []
        promote = suppress = 0
        for _, rr in rules.iterrows():
            r = rr.to_dict()
            if rule_matches(d, r):
                delta = to_num(r.get("score_delta", 0), 0)
                score += delta
                if str(r.get("action")) == "PROMOTE": promote += 1
                if str(r.get("action")) == "SUPPRESS": suppress += 1
                fired.append(f"{r.get('rule_id','')}/{r.get('action')}:{r.get('signal')}={r.get('value')}({delta:.2f})")
        d["BaseScoreUsed"] = round(to_num(d.get(score_col, 0), 0), 6) if score_col else 0
        d["DecisionScore"] = round(score, 6)
        d["PromoteRulesFired"] = promote
        d["SuppressRulesFired"] = suppress
        d["RulesFiredCount"] = len(fired)
        d["RulesFired"] = " | ".join(fired[:25])
        scored_rows.append(d)
    out = pd.DataFrame(scored_rows)
    date_col = first_existing(out, DATE_COLS)
    stream_col = first_existing(out, STREAM_COLS)
    core_col = first_existing(out, CORE_COLS)
    sort_cols, asc = [], []
    if date_col: sort_cols.append(date_col); asc.append(True)
    if stream_col: sort_cols.append(stream_col); asc.append(True)
    sort_cols.append("DecisionScore"); asc.append(False)
    out = out.sort_values(sort_cols, ascending=asc)
    if date_col and stream_col:
        out["CoreRankWithinStream"] = out.groupby([date_col, stream_col]).cumcount() + 1
    elif stream_col:
        out["CoreRankWithinStream"] = out.groupby([stream_col]).cumcount() + 1
    else:
        out["CoreRankWithinStream"] = np.arange(len(out)) + 1
    if date_col and core_col and stream_col:
        out = out.sort_values([date_col, core_col, "DecisionScore"], ascending=[True, True, False])
        out["StreamRankWithinCore"] = out.groupby([date_col, core_col]).cumcount() + 1
        out = out.sort_values(sort_cols, ascending=asc)
    elif core_col:
        out["StreamRankWithinCore"] = out.groupby([core_col]).cumcount() + 1
    return out

def best_playlist(scored_df, max_cores_per_stream=1, max_rows=None):
    if scored_df.empty: return scored_df.copy()
    stream_col = first_existing(scored_df, STREAM_COLS)
    date_col = first_existing(scored_df, DATE_COLS)
    group_cols = []
    if date_col: group_cols.append(date_col)
    if stream_col: group_cols.append(stream_col)
    if group_cols:
        out = scored_df.sort_values(group_cols + ["DecisionScore"], ascending=[True]*len(group_cols)+[False])
        out = out.groupby(group_cols).head(int(max_cores_per_stream)).copy()
    else:
        out = scored_df.sort_values(["DecisionScore"], ascending=False).copy()
    if max_rows: out = out.head(int(max_rows)).copy()
    out.insert(0, "PlaylistRank", np.arange(len(out)) + 1)
    return out

def write_zip(paths, zip_path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as z:
        for p in paths:
            p = Path(p)
            if p.exists(): z.write(p, p.name)

st.set_page_config(page_title="120 Core Decision Engine", layout="wide")
st.title("120 Core Decision Engine V1.1 Cloud Safe")
st.caption(VERSION)
st.warning("V1.1 is cloud-safe: single app.py, no package imports. It still requires validation before trusting capture claims.")

tab1, tab2, tab3, tab4 = st.tabs(["1 Build Rule DB", "2 Score Candidates", "3 Playlist", "4 Diagnostics"])

with tab1:
    st.subheader("Build Rule DB from 035 Signal Outputs")
    st.code("\\n".join(SIGNAL_FILES))
    uploaded = st.file_uploader("Upload 035 signal CSVs", type=["csv"], accept_multiple_files=True)
    if uploaded:
        for f in uploaded:
            (INPUTS / f.name).write_bytes(f.getvalue())
        st.success(f"Saved {len(uploaded)} uploaded files.")
    if st.button("Build / Refresh Rule DB", type="primary"):
        rules = build_rule_db_from_signal_folder(INPUTS)
        if rules.empty:
            st.error("No usable signal files found.")
        else:
            out = OUTPUTS / "120_CORE_RULE_DB_FROM_035.csv"
            rules.to_csv(out, index=False)
            st.success(f"Built {out.name} with {len(rules)} rules.")
            st.dataframe(rules.head(200), use_container_width=True)
    rule_path = OUTPUTS / "120_CORE_RULE_DB_FROM_035.csv"
    if rule_path.exists():
        st.success(f"Rule DB ready: {rule_path.name}")
        with open(rule_path, "rb") as f:
            st.download_button("Download Rule DB", f, file_name=rule_path.name)

with tab2:
    st.subheader("Score Candidate / Daily Matrix")
    cand_upload = st.file_uploader("Upload candidate CSV", type=["csv"], key="candidate")
    if cand_upload:
        (INPUTS / cand_upload.name).write_bytes(cand_upload.getvalue())
        st.success(f"Saved candidate: {cand_upload.name}")
    candidates = [p for p in INPUTS.glob("*.csv") if not p.name.startswith(("01_","02_","03_","04_","05_"))]
    cand_name = st.selectbox("Candidate file", [""] + [p.name for p in candidates])
    if st.button("Score Candidate File", type="primary"):
        rule_path = OUTPUTS / "120_CORE_RULE_DB_FROM_035.csv"
        if not rule_path.exists():
            st.error("Build Rule DB first.")
        elif not cand_name:
            st.error("Select or upload a candidate CSV.")
        else:
            rules = read_csv_any(rule_path)
            cand = read_csv_any(INPUTS / cand_name)
            scored = score_candidates(cand, rules)
            out = OUTPUTS / "120_CORE_SCORED_CANDIDATES.csv"
            scored.to_csv(out, index=False)
            st.success(f"Scored candidates written: {out.name} rows={len(scored)}")
            st.dataframe(scored.head(200), use_container_width=True)
            with open(out, "rb") as f:
                st.download_button("Download scored candidates", f, file_name=out.name)

with tab3:
    st.subheader("Generate Playlist")
    scored_path = OUTPUTS / "120_CORE_SCORED_CANDIDATES.csv"
    if not scored_path.exists():
        st.info("Score candidates first.")
    else:
        max_per_stream = st.number_input("Max cores per stream", min_value=1, max_value=5, value=1)
        max_rows = st.number_input("Optional max playlist rows; 0 = no limit", min_value=0, value=0)
        if st.button("Build Playlist", type="primary"):
            scored = read_csv_any(scored_path)
            playlist = best_playlist(scored, max_cores_per_stream=int(max_per_stream), max_rows=int(max_rows) if max_rows else None)
            out = OUTPUTS / "120_CORE_DAILY_PLAYLIST.csv"
            playlist.to_csv(out, index=False)
            zip_path = OUTPUTS / "OUTPUTS_120_CORE_DECISION_ENGINE_V1_1.zip"
            write_zip([OUTPUTS/"120_CORE_RULE_DB_FROM_035.csv", scored_path, out], zip_path)
            st.success(f"Playlist written: {out.name} rows={len(playlist)}")
            st.dataframe(playlist.head(200), use_container_width=True)
            with open(out, "rb") as f:
                st.download_button("Download playlist CSV", f, file_name=out.name)
            with open(zip_path, "rb") as f:
                st.download_button("Download output ZIP", f, file_name=zip_path.name)

with tab4:
    if st.button("List working files"):
        rows = []
        for folder in [INPUTS, OUTPUTS]:
            for p in folder.glob("*"):
                rows.append({"folder": folder.name, "name": p.name, "size_mb": round(p.stat().st_size/1024/1024, 3)})
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
