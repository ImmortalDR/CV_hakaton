#!/usr/bin/env python3
"""Regular self-check against Danila B2 acceptance criteria."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("/root/hakaton/dataset/raw_sources/danila_hh")
CHECKS = []


def ok(name: str, cond: bool, detail: str = "") -> None:
    CHECKS.append({"check": name, "pass": bool(cond), "detail": detail})


def main() -> None:
    textovic = ROOT / "textovic/repo/cleaned_data.csv"
    ok("textovic_csv", textovic.is_file(), f"bytes={textovic.stat().st_size if textovic.is_file() else 0}")
    man = ROOT / "textovic/MANIFEST.json"
    ok("textovic_manifest", man.is_file())

    v1 = ROOT / "labels/candidate_need_pairs.jsonl"
    v2 = ROOT / "labels/candidate_need_pairs_v2.jsonl"
    ok("pairs_v1", v1.is_file(), f"lines={sum(1 for _ in v1.open()) if v1.is_file() else 0}")
    ok("pairs_v2", v2.is_file(), f"lines={sum(1 for _ in v2.open()) if v2.is_file() else 0}")

    r1 = ROOT / "models/tfidf_pilot_report.json"
    r2 = ROOT / "models/tfidf_pilot_report_v2.json"
    ok("report_v1", r1.is_file())
    ok("report_v2", r2.is_file())
    if r2.is_file():
        rep = json.loads(r2.read_text(encoding="utf-8"))
        acc = rep.get("test", {}).get("accuracy")
        # v2 must not claim perfect self-match
        ok("v2_not_trivial_perfect", acc is not None and acc < 0.99, f"test_acc={acc}")
        means = rep.get("train_score_means", {})
        ok(
            "v2_pos_gt_neg_scores",
            means.get("relevant", 0) > means.get("not_relevant", 1),
            str(means),
        )

    src = ROOT / "SOURCES_STATUS.json"
    ok("sources_status", src.is_file())
    if src.is_file():
        st = json.loads(src.read_text(encoding="utf-8"))
        ok("mendeley_key_present", "os_rf_mendeley" in st)
        ok("kaggle_key_present", "data_engineer_kaggle" in st)

    bridge = ROOT / "trudvsem_bridge/MANIFEST.json"
    ok("trudvsem_bridge", bridge.is_file(), "RF bridge sample")

    mendeley_csv = ROOT / "os_rf_mendeley/vacancies_russian_operating_systems.csv"
    mendeley_man = ROOT / "os_rf_mendeley/MANIFEST.json"
    ok("mendeley_csv", mendeley_csv.is_file(), f"bytes={mendeley_csv.stat().st_size if mendeley_csv.is_file() else 0}")
    ok("mendeley_manifest", mendeley_man.is_file())
    if mendeley_man.is_file():
        mm = json.loads(mendeley_man.read_text(encoding="utf-8"))
        ok("mendeley_ok_flag", mm.get("ok") is True, str(mm.get("usable_rows")))
    if src.is_file():
        st = json.loads(src.read_text(encoding="utf-8"))
        ok("mendeley_status_ok", st.get("os_rf_mendeley", {}).get("ok") is True)

    osrf_pairs = ROOT / "labels/candidate_need_pairs_osrf.jsonl"
    ok("osrf_pairs", osrf_pairs.is_file(), f"lines={sum(1 for _ in osrf_pairs.open()) if osrf_pairs.is_file() else 0}")

    itvac_man = ROOT / "it_vacancies_kaggle_alt/MANIFEST.json"
    ok("itvac_manifest", itvac_man.is_file())
    if itvac_man.is_file():
        im = json.loads(itvac_man.read_text(encoding="utf-8"))
        ok("itvac_ok", im.get("ok") is True, f"usable={im.get('usable_rows')} pairs={im.get('pairs')}")
    if src.is_file():
        st2 = json.loads(src.read_text(encoding="utf-8"))
        ok("kaggle_alt_status_ok", st2.get("data_engineer_kaggle", {}).get("ok") is True)
    itvac_pairs = ROOT / "labels/candidate_need_pairs_itvac.jsonl"
    ok("itvac_pairs", itvac_pairs.is_file(), f"lines={sum(1 for _ in itvac_pairs.open()) if itvac_pairs.is_file() else 0}")
    combined = ROOT / "labels/candidate_need_pairs_combined.jsonl"
    ok("combined_pairs", combined.is_file(), f"lines={sum(1 for _ in combined.open()) if combined.is_file() else 0}")

    hq = ROOT / "labels/human_queue_v2.jsonl"
    ok("human_queue", hq.is_file() and hq.stat().st_size > 0)

    out = {
        "passed": sum(1 for c in CHECKS if c["pass"]),
        "failed": sum(1 for c in CHECKS if not c["pass"]),
        "checks": CHECKS,
    }
    (ROOT / "SELF_CHECK.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if out["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
