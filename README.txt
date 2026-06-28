120_CORE_DAILY_ENGINE_V2_CLOUD_SAFE

This is the daily-generator version.

Inputs:
- merged history CSV
- 120 core rule library CSV(s), such as core_rule_library_stable_only_filtered.csv

Outputs:
- 120_CORE_DAILY_CANDIDATE_MATRIX.csv
- 120_CORE_DAILY_PLAYLIST.csv
- 120_CORE_MANUAL_TEST_MATRIX.csv
- 120_CORE_MANUAL_TEST_SUMMARY.csv

It calculates:
- Core→Stream score/rank/row percentile
- Stream→Core rank/row percentile
- movement values
- movement agreement
- cadence proxy
- final arbitration score
