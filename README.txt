120_CORE_DECISION_ENGINE_V1

Includes:
- Streamlit app: app.py
- Local CLI: cli.py
- Streamlit Cloud requirements.txt

Run locally:
Double-click RUN_STREAMLIT_LOCAL.bat

Cloud:
Upload this folder to GitHub and deploy app.py on Streamlit Community Cloud.
Do not put the 7GB master file in Streamlit Community Cloud.

Inputs for Rule DB:
01_TOP_OVERALL_SIGNALS.csv
02_TOP_PER_CORE_SIGNALS.csv
03_TOP_PER_STREAM_SIGNALS.csv
04_TOP_PER_MEMBER_SIGNALS.csv
05_TOP_PAIR_COMBO_SIGNALS.csv

Inputs for scoring:
A candidate/daily matrix CSV.

Outputs:
OUTPUTS/120_CORE_RULE_DB_FROM_035.csv
OUTPUTS/120_CORE_SCORED_CANDIDATES.csv
OUTPUTS/120_CORE_DAILY_PLAYLIST.csv
