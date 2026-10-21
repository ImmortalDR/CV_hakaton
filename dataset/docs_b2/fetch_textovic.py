#!/usr/bin/env python3
"""Download Textovic/hh_vacancy into dataset/raw_sources/danila_hh/textovic (Danila B2)."""
from __future__ import annotations

import json
from pathlib import Path

from datasets import load_dataset

ROOT = Path("/root/hakaton/dataset/raw_sources/danila_hh/textovic")


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    print("loading Textovic/hh_vacancy...")
    ds = load_dataset("Textovic/hh_vacancy")
    print(ds)
    path = ROOT / "hf_dataset"
    ds.save_to_disk(str(path))
    split = list(ds.keys())[0]
    df = ds[split].to_pandas()
    print("rows", len(df), "cols", list(df.columns)[:30])
    df.head(20).to_json(ROOT / "sample20.json", force_ascii=False, orient="records")
    meta = {
        "source": "Textovic/hh_vacancy",
        "license": "Apache-2.0",
        "rows": int(len(df)),
        "columns": [str(c) for c in df.columns],
        "saved": str(path),
        "role": "text_matching_corpus",
        "note": "Danila B2 track; candidate-need labels are separate",
    }
    (ROOT / "MANIFEST.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("OK", meta)


if __name__ == "__main__":
    main()
