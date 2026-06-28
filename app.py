
from pathlib import Path
import pandas as pd
import streamlit as st
from engine.core_engine import VERSION, SIGNAL_FILES, build_rule_db_from_signal_folder, read_csv_any, score_candidates, best_playlist, write_zip

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "INPUTS"
OUTPUTS = ROOT / "OUTPUTS"
INPUTS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)

st.set_page_config(page_title="120 Core Decision Engine", layout="wide")
st.title("120 Core Decision Engine V1")
st.caption(VERSION)
st.warning("V1 is the unified app shell: Rule DB → candidate scoring → playlist. It does not claim final 75% capture until validated outputs prove it.")

tab1, tab2, tab3, tab4 = st.tabs(["1 Build Rule DB", "2 Score Candidates", "3 Playlist", "4 Diagnostics"])

with tab1:
    st.subheader("Build Rule DB from 035 Signal Outputs")
    st.code("\\n".join(SIGNAL_FILES))
    uploaded = st.file_uploader("Optional: upload 035 signal CSVs here", type=["csv"], accept_multiple_files=True)
    if uploaded:
        for f in uploaded:
            (INPUTS / f.name).write_bytes(f.getvalue())
        st.success(f"Saved {len(uploaded)} uploaded files to INPUTS.")
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
    cand_upload = st.file_uploader("Upload candidate CSV", type=["csv"], key="cand")
    if cand_upload:
        cand_path = INPUTS / cand_upload.name
        cand_path.write_bytes(cand_upload.getvalue())
        st.success(f"Saved candidate: {cand_upload.name}")
    candidates = [p for p in INPUTS.glob("*.csv") if not p.name.startswith(("01_","02_","03_","04_","05_"))]
    cand_name = st.selectbox("Candidate file in INPUTS", [""] + [p.name for p in candidates])
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
    st.subheader("Generate Playlist from Scored Candidates")
    scored_path = OUTPUTS / "120_CORE_SCORED_CANDIDATES.csv"
    if not scored_path.exists():
        st.info("Score candidates first.")
    else:
        max_per_stream = st.number_input("Max cores per stream", min_value=1, max_value=5, value=1, step=1)
        max_rows = st.number_input("Optional max playlist rows; 0 = no limit", min_value=0, value=0, step=1)
        if st.button("Build Playlist", type="primary"):
            scored = read_csv_any(scored_path)
            playlist = best_playlist(scored, max_cores_per_stream=int(max_per_stream), max_rows=int(max_rows) if max_rows else None)
            out = OUTPUTS / "120_CORE_DAILY_PLAYLIST.csv"
            playlist.to_csv(out, index=False)
            zip_path = OUTPUTS / "OUTPUTS_120_CORE_DECISION_ENGINE_V1.zip"
            write_zip([OUTPUTS/"120_CORE_RULE_DB_FROM_035.csv", scored_path, out], zip_path)
            st.success(f"Playlist written: {out.name} rows={len(playlist)}")
            st.dataframe(playlist.head(200), use_container_width=True)
            with open(out, "rb") as f:
                st.download_button("Download playlist CSV", f, file_name=out.name)
            with open(zip_path, "rb") as f:
                st.download_button("Download output ZIP", f, file_name=zip_path.name)

with tab4:
    st.subheader("Diagnostics")
    if st.button("List INPUTS / OUTPUTS"):
        rows = []
        for folder in [INPUTS, OUTPUTS]:
            for p in folder.glob("*"):
                rows.append({"folder": folder.name, "name": p.name, "size_mb": round(p.stat().st_size/1024/1024, 3)})
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
