
from pathlib import Path
import argparse
from engine.core_engine import build_rule_db_from_signal_folder, read_csv_any, score_candidates, best_playlist, write_zip, VERSION

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "INPUTS"
OUTPUTS = ROOT / "OUTPUTS"
INPUTS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)

def main():
    p = argparse.ArgumentParser(description="120 Core Decision Engine CLI")
    p.add_argument("--build-rules", action="store_true")
    p.add_argument("--score", type=str, default="")
    p.add_argument("--playlist", action="store_true")
    p.add_argument("--max-cores-per-stream", type=int, default=1)
    args = p.parse_args()
    print(VERSION)
    if args.build_rules:
        rules = build_rule_db_from_signal_folder(INPUTS)
        out = OUTPUTS / "120_CORE_RULE_DB_FROM_035.csv"
        rules.to_csv(out, index=False)
        print(f"RULE_DB={out} rows={len(rules)}")
    if args.score:
        rule_path = OUTPUTS / "120_CORE_RULE_DB_FROM_035.csv"
        if not rule_path.exists():
            raise SystemExit("Build rules first: --build-rules")
        cand_path = INPUTS / args.score
        if not cand_path.exists():
            raise SystemExit(f"Candidate not found in INPUTS: {args.score}")
        rules = read_csv_any(rule_path)
        cand = read_csv_any(cand_path)
        scored = score_candidates(cand, rules)
        out = OUTPUTS / "120_CORE_SCORED_CANDIDATES.csv"
        scored.to_csv(out, index=False)
        print(f"SCORED={out} rows={len(scored)}")
    if args.playlist:
        scored_path = OUTPUTS / "120_CORE_SCORED_CANDIDATES.csv"
        if not scored_path.exists():
            raise SystemExit("Score candidates first: --score file.csv")
        scored = read_csv_any(scored_path)
        playlist = best_playlist(scored, max_cores_per_stream=args.max_cores_per_stream)
        out = OUTPUTS / "120_CORE_DAILY_PLAYLIST.csv"
        playlist.to_csv(out, index=False)
        zip_path = OUTPUTS / "OUTPUTS_120_CORE_DECISION_ENGINE_V1.zip"
        write_zip([OUTPUTS/"120_CORE_RULE_DB_FROM_035.csv", scored_path, out], zip_path)
        print(f"PLAYLIST={out} rows={len(playlist)}")
        print(f"ZIP={zip_path}")

if __name__ == "__main__":
    main()
