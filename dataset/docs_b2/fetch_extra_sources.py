#!/usr/bin/env python3
"""Try to fetch Mendeley OS RF + note Kaggle blockers (Danila sources 2–3)."""
from __future__ import annotations

import json
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path("/root/hakaton/dataset/raw_sources/danila_hh")
OS_DIR = ROOT / "os_rf_mendeley"
DE_DIR = ROOT / "data_engineer_kaggle"
STATUS = ROOT / "SOURCES_STATUS.json"

UA = "Mozilla/5.0 (compatible; FSP-dataset-b2/1.0; research)"


def try_download(url: str, dest: Path) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read(200)
            code = getattr(resp, "status", 200)
            ctype = resp.headers.get("Content-Type", "")
            # if HTML login page, fail
            if b"<html" in data[:200].lower() or "text/html" in ctype:
                return {"url": url, "ok": False, "reason": f"html_or_login code={code} ctype={ctype}"}
            # re-open full download via curl for large files
    except Exception as e:
        return {"url": url, "ok": False, "reason": str(e)}

    # use curl -L for full file
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "curl",
        "-fsSL",
        "-A",
        UA,
        "-o",
        str(dest),
        url,
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        return {"url": url, "ok": False, "reason": p.stderr[-500:] or p.stdout[-500:]}
    size = dest.stat().st_size if dest.exists() else 0
    if size < 1000:
        return {"url": url, "ok": False, "reason": f"too_small bytes={size}"}
    return {"url": url, "ok": True, "path": str(dest), "bytes": size}


def main() -> None:
    OS_DIR.mkdir(parents=True, exist_ok=True)
    DE_DIR.mkdir(parents=True, exist_ok=True)

    mendeley_urls = [
        # common Mendeley zip patterns (may 403 without cookie)
        "https://prod-dcd-datasets-cache-zipfiles.s3.eu-west-1.amazonaws.com/2xyz5rwhcn-1.zip",
        "https://data.mendeley.com/datasets/2xyz5rwhcn/1/files/zip?download=true",
    ]
    mendeley_attempts = []
    mendeley_ok = None
    for u in mendeley_urls:
        r = try_download(u, OS_DIR / "2xyz5rwhcn-1.zip")
        mendeley_attempts.append(r)
        if r.get("ok"):
            mendeley_ok = r
            break

    # Kaggle: no credentials on server
    kaggle_cli = subprocess.run(["which", "kaggle"], capture_output=True, text=True)
    kaggle_status = {
        "ok": False,
        "reason": "no_kaggle_credentials_in_dataset_env",
        "cli_present": bool(kaggle_cli.stdout.strip()),
        "datasets": [
            "olkhovaya/hh-ru-data-engineer-jobs-june-2026",
            "anastasiavdovina/russian-job-market-vacancies-from-hh-ru-2026",
        ],
        "action_needed": "Put kaggle.json in /root/.kaggle/ or upload zips to raw_sources/danila_hh/",
    }

    status = {
        "textovic": {"ok": True, "path": str(ROOT / "textovic/repo/cleaned_data.csv")},
        "os_rf_mendeley": {
            "ok": bool(mendeley_ok),
            "attempts": mendeley_attempts,
            "license_claimed": "CC BY 4.0",
            "doi": "10.17632/2xyz5rwhcn.1",
        },
        "data_engineer_kaggle": kaggle_status,
        "market_hh_kaggle": {
            **kaggle_status,
            "redistribution": "unknown — local-only if obtained",
        },
    }
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
