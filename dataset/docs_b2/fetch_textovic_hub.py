#!/usr/bin/env python3
"""Download Textovic/hh_vacancy via huggingface_hub (no NumPy 2 / pyarrow)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path("/root/hakaton/dataset/raw_sources/danila_hh/textovic")
OUT = ROOT / "repo"


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    print("downloading snapshot Textovic/hh_vacancy...")
    path = snapshot_download(
        repo_id="Textovic/hh_vacancy",
        repo_type="dataset",
        local_dir=str(OUT),
    )
    print("saved", path)
    files = []
    for dirpath, _, filenames in os.walk(OUT):
        for name in filenames:
            fp = Path(dirpath) / name
            if ".cache" in fp.parts:
                continue
            files.append({"path": str(fp.relative_to(OUT)), "bytes": fp.stat().st_size})
    files.sort(key=lambda x: x["path"])
    meta = {
        "source": "Textovic/hh_vacancy",
        "license": "Apache-2.0",
        "method": "huggingface_hub.snapshot_download",
        "saved": str(path),
        "files": files[:200],
        "file_count": len(files),
        "role": "text_matching_corpus",
        "note": "Danila B2; candidate-need labels separate",
    }
    (ROOT / "MANIFEST.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("OK files=", len(files), "total_bytes=", sum(f["bytes"] for f in files))


if __name__ == "__main__":
    main()
