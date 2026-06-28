
from pathlib import Path
from datetime import datetime
import zipfile
import pandas as pd
import numpy as np
import streamlit as st

VERSION = "120_CORE_DAILY_ENGINE_V2_CLOUD_SAFE_2026_06_28"

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "INPUTS"
OUTPUTS = ROOT / "OUTPUTS"
INPUTS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)

def to_num(x, default=0.0):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default

def norm4(x):
    s = ''.join(ch for ch in str(x) if ch.isdigit())
    if len(s) == 0:
        return ""
    return s.zfill(4)[-4:]

def stream_col(df):
    for c in ["StreamKey", "stream", "Stream", "StreamName"]:
        if c in df.columns:
            return c
    return ""

def date_col(df):
    for c in ["Date", "date", "DrawDate", "PLAY_DATE"]:
        if c in df.columns:
            return c
    return ""

def result_col(df):
    for c in ["Result4", "Result", "winning_4digit", "Winner", "result"]:
        if c in df.columns:
            return c
    return ""

def make_seed_traits(seed):
    seed = norm4(seed)
    if len(seed) != 4:
        return {}
    digs = [int(x) for x in seed]
    cnt = {str(i): seed.count(str(i)) for i in range(10)}
    even = sum(1 for d in digs if d % 2 == 0)
    odd = 4 - even
    high = sum(1 for d in digs if d >= 5)
    low = 4 - high
    spread = max(digs) - min(digs)
    unique = len(set(digs))
    max_rep = max(cnt.values())
    pairs = int(max_rep == 2 and unique == 3)
    trip = int(max_rep == 3)
    quad = int(max_rep == 4)
    consec = sum(1 for a,b in zip(digs, digs[1:]) if abs(a-b)==1)
    ssum = sum(digs)
    traits = {
        "seed": seed,
        "seed_sum": str(ssum),
        "seed_sum_mod3": str(ssum % 3),
        "seed_sum_mod4": str(ssum % 4),
        "seed_sum_mod5": str(ssum % 5),
        "seed_spread": str(spread),
        "seed_unique_digits": str(unique),
        "unique": str(unique),
        "max_rep": str(max_rep),
        "seed_even_cnt": str(even),
        "seed_odd_cnt": str(odd),
        "seed_high_cnt": str(high),
        "seed_low_cnt": str(low),
        "even": str(even),
        "odd": str(odd),
        "high": str(high),
        "low": str(low),
        "seed_has_pair": str(pairs),
        "seed_has_trip": str(trip),
        "seed_has_quad": str(quad),
        "seed_consec_links": str(consec),
        "consec_links": str(consec),
        "seed_parity_pattern": ''.join("E" if d%2==0 else "O" for d in digs),
        "parity_pattern": ''.join("E" if d%2==0 else "O" for d in digs),
        "seed_highlow_pattern": ''.join("H" if d>=5 else "L" for d in digs),
        "highlow_pattern": ''.join("H" if d>=5 else "L" for d in digs),
        "seed_repeat_shape": "quad" if quad else "triple" if trip else "one_pair" if pairs else "all_unique",
        "structure": "quad" if quad else "triple" if trip else "AABC" if pairs else "ABCD",
        "sum_bucket": "sum_0_9" if ssum <= 9 else "sum_10_13" if ssum <= 13 else "sum_14_17" if ssum <= 17 else "sum_18_21" if ssum <= 21 else "sum_22_plus",
        "spread_bucket": "spread_0_2" if spread <= 2 else "spread_3_4" if spread <= 4 else "spread_5_6" if spread <= 6 else "spread_7_plus",
        "seed_pos1": str(digs[0]),
        "seed_pos2": str(digs[1]),
        "seed_pos3": str(digs[2]),
        "seed_pos4": str(digs[3]),
    }
    for i in range(10):
        traits[f"cnt{i}"] = str(cnt[str(i)])
        traits[f"has{i}"] = "1" if cnt[str(i)] else "0"
        traits[f"no{i}"] = "1" if cnt[str(i)] == 0 else "0"
        traits[f"seed_cnt{i}"] = str(cnt[str(i)])
        traits[f"seed_has{i}"] = "1" if cnt[str(i)] else "0"
    return traits

def result_core_member(result):
    r = norm4(result)
    if len(r) != 4:
        return "", ""
    counts = {d: r.count(d) for d in set(r)}
    if sorted(counts.values()) != [1,1,2]:
        return "", ""
    core = ''.join(sorted(counts.keys()))
    member = ''.join(sorted(r))
    return core, member

def read_csv(path):
    return pd.read_csv(path, dtype=str, low_memory=False, encoding="utf-8-sig")

def load_rule_library(files):
    frames = []
    for f in files:
        try:
            df = read_csv(f)
            frames.append(df)
        except Exception:
            pass
    if not frames:
        return pd.DataFrame()
    rules = pd.concat(frames, ignore_index=True)
    if "enabled" in rules.columns:
        rules = rules[rules["enabled"].astype(str).str.lower().isin(["1","1.0","true","yes"])]
    if "target_core" not in rules.columns:
        if "scope_value" in rules.columns:
            rules["target_core"] = rules["scope_value"]
        elif "core" in rules.columns:
            rules["target_core"] = rules["core"]
    return rules.fillna("")

def rule_weight(rule):
    lift = to_num(rule.get("lift_vs_competitor", rule.get("lift", 1)), 1)
    precision = to_num(rule.get("precision", rule.get("winner_rate", 0)), 0)
    support = to_num(rule.get("support", rule.get("rows", 0)), 0)
    hits = to_num(rule.get("target_hits", rule.get("winner_rows", 0)), 0)
    base = np.log(max(lift, 1e-9)) * 8
    rel = min(np.log1p(support) / 5, 1.5)
    hitrel = min(np.log1p(hits) / 4, 1.5)
    return round(base + precision*5 + rel + hitrel, 6)

def match_rule(traits, rule):
    # Stable core library format.
    ok = True
    t1 = str(rule.get("trait_1","")).strip()
    v1 = str(rule.get("value_1","")).strip()
    t2 = str(rule.get("trait_2","")).strip()
    v2 = str(rule.get("value_2","")).strip()
    if t1:
        ok = ok and str(traits.get(t1, "")) == v1
    if t2:
        ok = ok and str(traits.get(t2, "")) == v2
    # 035 style fallback.
    sig = str(rule.get("signal","")).strip()
    val = str(rule.get("value","")).strip()
    if sig and val:
        sigs = sig.split("+")
        vals = val.split("|")
        if len(sigs) == len(vals):
            for s,v in zip(sigs, vals):
                if str(traits.get(s.strip(), "")) != v.strip():
                    ok = False
        else:
            ok = ok and str(traits.get(sig, "")) == val
    return bool(ok)

def prepare_history(history):
    dc = date_col(history)
    sc = stream_col(history)
    rc = result_col(history)
    if not dc or not sc or not rc:
        raise ValueError("History must contain date, stream, and result columns.")
    h = history.copy()
    h[dc] = pd.to_datetime(h[dc], errors="coerce")
    h["Result4_norm"] = h[rc].map(norm4)
    h = h.dropna(subset=[dc])
    h = h[h["Result4_norm"].str.len() == 4]
    h = h.sort_values([sc, dc]).copy()
    h["seed"] = h.groupby(sc)["Result4_norm"].shift(1)
    h["winner_core"], h["winner_member"] = zip(*h["Result4_norm"].map(result_core_member))
    h = h.rename(columns={dc:"date", sc:"stream"})
    return h[["date","stream","Result4_norm","seed","winner_core","winner_member"]].copy()

def build_test_candidate_matrix(history, rules, start_date=None):
    h = prepare_history(history)
    if start_date:
        h = h[h["date"] >= pd.to_datetime(start_date)].copy()
    h = h[h["seed"].astype(str).str.len() == 4].copy()
    cores = sorted([str(x).zfill(3) for x in rules["target_core"].dropna().astype(str).unique() if str(x).strip() != ""])
    if not cores:
        raise ValueError("No target_core values found in rule library.")
    rule_by_core = {c: rules[rules["target_core"].astype(str).str.zfill(3)==c].to_dict("records") for c in cores}
    rows = []
    for _, hr in h.iterrows():
        traits = make_seed_traits(hr["seed"])
        for core in cores:
            total = 0.0
            fired = []
            for rule in rule_by_core.get(core, []):
                if match_rule(traits, rule):
                    w = rule_weight(rule)
                    total += w
                    fired.append(str(rule.get("combined_rule_id", rule.get("rule_id",""))) + f":{w:.2f}")
            d = {
                "date": hr["date"].date().isoformat(),
                "stream": hr["stream"],
                "seed": hr["seed"],
                "candidate_core": core,
                "core_to_stream_score": round(total, 6),
                "rules_fired_count": len(fired),
                "rules_fired": " | ".join(fired[:20]),
                "actual_result": hr["Result4_norm"],
                "winner_core": hr["winner_core"],
                "winner_member": hr["winner_member"],
                "is_winner_core": 1 if core == str(hr["winner_core"]).zfill(3) else 0,
            }
            d.update(traits)
            rows.append(d)
    mat = pd.DataFrame(rows)
    return add_rank_percentile_cadence_movement(mat)

def build_daily_candidate_matrix(history, rules):
    h = prepare_history(history)
    last = h.sort_values("date").groupby("stream").tail(1).copy()
    next_date = h["date"].max() + pd.Timedelta(days=1)
    cores = sorted([str(x).zfill(3) for x in rules["target_core"].dropna().astype(str).unique() if str(x).strip() != ""])
    rule_by_core = {c: rules[rules["target_core"].astype(str).str.zfill(3)==c].to_dict("records") for c in cores}
    rows = []
    for _, hr in last.iterrows():
        traits = make_seed_traits(hr["Result4_norm"])
        for core in cores:
            total = 0.0
            fired = []
            for rule in rule_by_core.get(core, []):
                if match_rule(traits, rule):
                    w = rule_weight(rule)
                    total += w
                    fired.append(str(rule.get("combined_rule_id", rule.get("rule_id",""))) + f":{w:.2f}")
            d = {
                "date": next_date.date().isoformat(),
                "stream": hr["stream"],
                "seed": hr["Result4_norm"],
                "candidate_core": core,
                "core_to_stream_score": round(total, 6),
                "rules_fired_count": len(fired),
                "rules_fired": " | ".join(fired[:20]),
            }
            d.update(traits)
            rows.append(d)
    mat = pd.DataFrame(rows)
    return add_rank_percentile_cadence_movement(mat)

def add_rank_percentile_cadence_movement(mat):
    if mat.empty:
        return mat
    out = mat.copy()
    out["core_to_stream_score_num"] = out["core_to_stream_score"].map(lambda x: to_num(x, 0))
    # Core -> Stream: rank 78 streams inside each core/date.
    out = out.sort_values(["date","candidate_core","core_to_stream_score_num"], ascending=[True, True, False])
    out["StreamRankWithinCore"] = out.groupby(["date","candidate_core"]).cumcount() + 1
    out["CoreToStream_RowPercentile"] = 1 - ((out["StreamRankWithinCore"] - 1) / out.groupby(["date","candidate_core"])["stream"].transform("count").clip(lower=1))
    # Stream -> Core: rank cores inside each stream/date.
    out = out.sort_values(["date","stream","core_to_stream_score_num"], ascending=[True, True, False])
    out["CoreRankWithinStream"] = out.groupby(["date","stream"]).cumcount() + 1
    out["StreamToCore_RowPercentile"] = 1 - ((out["CoreRankWithinStream"] - 1) / out.groupby(["date","stream"])["candidate_core"].transform("count").clip(lower=1))
    # Movement values based on prior date for same stream/core.
    out = out.sort_values(["candidate_core","stream","date"]).copy()
    out["Prev_StreamRankWithinCore"] = out.groupby(["candidate_core","stream"])["StreamRankWithinCore"].shift(1)
    out["StreamMovementWithinCore"] = out["StreamRankWithinCore"] - out["Prev_StreamRankWithinCore"]
    out = out.sort_values(["stream","candidate_core","date"]).copy()
    out["Prev_CoreRankWithinStream"] = out.groupby(["stream","candidate_core"])["CoreRankWithinStream"].shift(1)
    out["CoreMovementWithinStream"] = out["CoreRankWithinStream"] - out["Prev_CoreRankWithinStream"]
    out["MovementAgreement"] = np.where(
        out["StreamMovementWithinCore"].isna() | out["CoreMovementWithinStream"].isna(), "",
        np.where(np.sign(out["StreamMovementWithinCore"]) == np.sign(out["CoreMovementWithinStream"]), "SAME_DIRECTION", "OPPOSITE_DIRECTION")
    )
    out["MovementMagnitude"] = out["StreamMovementWithinCore"].abs().fillna(0) + out["CoreMovementWithinStream"].abs().fillna(0)
    # Simple cadence proxy: prior occurrences since same stream/core winner in test matrix.
    if "is_winner_core" in out.columns:
        out = out.sort_values(["stream","candidate_core","date"]).copy()
        gaps = []
        last_hit = {}
        for idx, row in out.iterrows():
            key = (row["stream"], row["candidate_core"])
            prev = last_hit.get(key, None)
            gaps.append("" if prev is None else idx - prev)
            if int(row.get("is_winner_core",0)) == 1:
                last_hit[key] = idx
        out["StreamCoreCadenceGapProxy"] = gaps
    # Final arbitration score uses both percentiles plus raw evidence and movement.
    out["FinalArbitrationScore"] = (
        out["core_to_stream_score_num"] +
        out["CoreToStream_RowPercentile"].astype(float) * 10 +
        out["StreamToCore_RowPercentile"].astype(float) * 10 -
        out["CoreRankWithinStream"].astype(float) * 0.05 -
        out["StreamRankWithinCore"].astype(float) * 0.03
    ).round(6)
    return out.sort_values(["date","stream","FinalArbitrationScore"], ascending=[True, True, False])

def make_playlist(matrix, max_cores_per_stream=1, max_rows=0):
    out = matrix.sort_values(["date","stream","FinalArbitrationScore"], ascending=[True, True, False]).copy()
    out = out.groupby(["date","stream"]).head(int(max_cores_per_stream)).copy()
    out = out.sort_values(["date","FinalArbitrationScore"], ascending=[True, False])
    if max_rows:
        out = out.groupby("date").head(int(max_rows)).copy()
    out.insert(0, "PlaylistRank", out.groupby("date").cumcount()+1)
    return out

def summarize_test(matrix):
    if "is_winner_core" not in matrix.columns:
        return pd.DataFrame()
    daily = matrix.copy()
    rows = []
    for topn in [1,2,3,5,10]:
        x = daily[daily["CoreRankWithinStream"] <= topn]
        winners = daily[daily["is_winner_core"].astype(int)==1]
        captured = x[x["is_winner_core"].astype(int)==1]
        rows.append({
            "test": f"CoreRankWithinStream<=Top{topn}",
            "candidate_rows": len(x),
            "winner_rows_total": len(winners),
            "captured_winners": len(captured),
            "capture_rate": len(captured)/len(winners) if len(winners) else 0,
            "plays_per_captured_winner": len(x)/len(captured) if len(captured) else None,
        })
    return pd.DataFrame(rows)

def write_zip(paths, zip_path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as z:
        for p in paths:
            p=Path(p)
            if p.exists():
                z.write(p, p.name)

st.set_page_config(page_title="120 Core Daily Engine V2", layout="wide")
st.title("120 Core Daily Engine V2")
st.caption(VERSION)

st.markdown("Builds a 120-core candidate matrix from **history + core rule libraries**, then calculates **Core→Stream**, **Stream→Core**, both row percentiles, cadence proxy, movement, arbitration score, and playlist.")

tab1, tab2, tab3, tab4 = st.tabs(["Inputs", "Generate Daily", "Manual Test / Backtest", "Diagnostics"])

with tab1:
    st.subheader("Upload / Manage Inputs")
    files = st.file_uploader("Upload history and rule library CSVs", type=["csv"], accept_multiple_files=True)
    if files:
        for f in files:
            (INPUTS / f.name).write_bytes(f.getvalue())
        st.success(f"Saved {len(files)} files to INPUTS.")
    if st.button("List INPUTS"):
        rows=[]
        for p in INPUTS.glob("*"):
            rows.append({"file":p.name,"size_mb":round(p.stat().st_size/1024/1024,3)})
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

with tab2:
    st.subheader("Generate Next-Day Candidate Matrix and Playlist")
    csvs = list(INPUTS.glob("*.csv"))
    history_options = [p.name for p in csvs if "history" in p.name.lower() or "merged" in p.name.lower()]
    rule_options = [p.name for p in csvs if "rule" in p.name.lower() or "library" in p.name.lower()]
    hist_name = st.selectbox("History file", [""] + history_options)
    rule_names = st.multiselect("Core rule library file(s)", rule_options, default=rule_options[:1])
    max_per_stream = st.number_input("Max cores per stream in playlist", 1, 5, 1, key="dailymax")
    max_rows = st.number_input("Optional max daily playlist rows; 0=no limit", 0, 500, 0, key="dailyrows")
    if st.button("Generate Daily Matrix + Playlist", type="primary"):
        if not hist_name or not rule_names:
            st.error("Select history and at least one core rule library.")
        else:
            history = read_csv(INPUTS / hist_name)
            rules = load_rule_library([INPUTS / r for r in rule_names])
            matrix = build_daily_candidate_matrix(history, rules)
            playlist = make_playlist(matrix, max_per_stream, max_rows)
            mpath = OUTPUTS / "120_CORE_DAILY_CANDIDATE_MATRIX.csv"
            ppath = OUTPUTS / "120_CORE_DAILY_PLAYLIST.csv"
            matrix.to_csv(mpath, index=False)
            playlist.to_csv(ppath, index=False)
            zpath = OUTPUTS / "OUTPUTS_120_CORE_DAILY_ENGINE_V2.zip"
            write_zip([mpath, ppath], zpath)
            st.success(f"Built matrix rows={len(matrix)} and playlist rows={len(playlist)}")
            st.dataframe(playlist.head(200), use_container_width=True)
            with open(ppath,"rb") as f:
                st.download_button("Download playlist", f, file_name=ppath.name)
            with open(mpath,"rb") as f:
                st.download_button("Download full matrix", f, file_name=mpath.name)

with tab3:
    st.subheader("Manual Testing / Backtest Since Cutoff")
    st.write("Use this when you add post-06/17 results. It tests historical dates by using each stream's prior draw as the seed.")
    csvs = list(INPUTS.glob("*.csv"))
    history_options = [p.name for p in csvs if "history" in p.name.lower() or "merged" in p.name.lower()]
    rule_options = [p.name for p in csvs if "rule" in p.name.lower() or "library" in p.name.lower()]
    hist_name2 = st.selectbox("Backtest history file", [""] + history_options, key="bh")
    rule_names2 = st.multiselect("Backtest rule library file(s)", rule_options, default=rule_options[:1], key="br")
    start_date = st.text_input("Start date for manual test", "2026-06-18")
    if st.button("Run Manual Test", type="primary"):
        if not hist_name2 or not rule_names2:
            st.error("Select history and rule library.")
        else:
            history = read_csv(INPUTS / hist_name2)
            rules = load_rule_library([INPUTS / r for r in rule_names2])
            matrix = build_test_candidate_matrix(history, rules, start_date=start_date)
            summary = summarize_test(matrix)
            playlist = make_playlist(matrix, 1, 0)
            mpath = OUTPUTS / "120_CORE_MANUAL_TEST_MATRIX.csv"
            spath = OUTPUTS / "120_CORE_MANUAL_TEST_SUMMARY.csv"
            ppath = OUTPUTS / "120_CORE_MANUAL_TEST_TOP1_PLAYLIST.csv"
            matrix.to_csv(mpath,index=False)
            summary.to_csv(spath,index=False)
            playlist.to_csv(ppath,index=False)
            st.success(f"Manual test complete. Matrix rows={len(matrix)}")
            st.dataframe(summary, use_container_width=True)
            st.dataframe(playlist.head(200), use_container_width=True)
            with open(spath,"rb") as f:
                st.download_button("Download summary", f, file_name=spath.name)
            with open(mpath,"rb") as f:
                st.download_button("Download test matrix", f, file_name=mpath.name)

with tab4:
    st.subheader("Outputs")
    if st.button("List OUTPUTS"):
        rows=[]
        for p in OUTPUTS.glob("*"):
            rows.append({"file":p.name,"size_mb":round(p.stat().st_size/1024/1024,3)})
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
