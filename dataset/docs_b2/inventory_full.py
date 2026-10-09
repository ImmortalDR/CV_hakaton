#!/usr/bin/env python3
"""Full inventory of /root/hakaton/dataset for Danila's 'what is already there'."""
from __future__ import annotations

import json
from pathlib import Path

root = Path("/root/hakaton/dataset")


def du_mb(p: Path) -> float:
    if p.is_file():
        return p.stat().st_size / 1e6
    total = 0
    for f in p.rglob("*"):
        if f.is_file():
            try:
                total += f.stat().st_size
            except OSError:
                pass
    return total / 1e6


def main() -> None:
    out = {"root": str(root), "trees": {}}

    # top-level
    top = {}
    for p in sorted(root.iterdir()):
        if p.name.startswith("."):
            continue
        top[p.name] = {
            "type": "dir" if p.is_dir() else "file",
            "mb": round(du_mb(p), 1),
        }
    out["top_level"] = top

    # raw_sources detail
    rs = root / "raw_sources"
    raw = {}
    for p in sorted(rs.iterdir()):
        if not p.is_dir():
            continue
        files = []
        for f in sorted(p.rglob("*")):
            if f.is_file() and ".cache" not in f.parts:
                files.append(
                    {
                        "path": str(f.relative_to(rs)),
                        "mb": round(f.stat().st_size / 1e6, 2),
                    }
                )
        # keep biggest / summary
        files_sorted = sorted(files, key=lambda x: -x["mb"])
        raw[p.name] = {
            "mb_total": round(du_mb(p), 1),
            "file_count": len(files),
            "top_files": files_sorted[:15],
        }
    out["raw_sources"] = raw

    # builds
    builds = {}
    bd = root / "builds"
    if bd.is_dir():
        for p in sorted(bd.iterdir()):
            if p.is_dir():
                builds[p.name] = {"mb": round(du_mb(p), 1)}
    out["builds"] = builds

    # danila_hh summary
    dh = rs / "danila_hh"
    out["danila_hh"] = {
        "mb": round(du_mb(dh), 1) if dh.is_dir() else 0,
        "note": "added 2026-10-09 Textovic+Mendeley+IT_vacancies+labels",
    }

    # training-relevant map (Danila: RF vacancies + responses)
    out["training_priority_per_danila"] = {
        "primary_rf_vacancies": "raw_sources/trudvsem/vacancies.csv (~21GB)",
        "primary_rf_responses": [
            "raw_sources/trudvsem/responses.csv",
            "raw_sources/trudvsem/invitations.csv",
            "raw_sources/trudvsem/curricula_vitae.csv",
        ],
        "secondary_external": [
            "tianchi (CN job match events)",
            "confit",
            "talentclef",
            "careercorpus",
        ],
        "danila_hh_role": "extra RU vacancy text corpora for text matching pilot; not a replacement for trudvsem responses",
        "eval_builds_role": "synthetic FSP eval — not the main train corpus Danila means",
    }

    path = root / "raw_sources/danila_hh/SERVER_INVENTORY.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2)[:8000])
    print("\n... saved", path)


if __name__ == "__main__":
    main()
