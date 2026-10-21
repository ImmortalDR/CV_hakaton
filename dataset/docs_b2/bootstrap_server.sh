#!/usr/bin/env bash
set -euo pipefail
cd /root/hakaton/dataset
mkdir -p raw_sources/danila_hh/textovic docs_b2
if [[ ! -x .venv-danila/bin/python ]]; then
  python3 -m venv .venv-danila
fi
.venv-danila/bin/pip install -U pip
.venv-danila/bin/pip install 'datasets>=2.19' huggingface_hub pyarrow pandas
.venv-danila/bin/python docs_b2/fetch_textovic.py
du -sh raw_sources/danila_hh/textovic
cat raw_sources/danila_hh/textovic/MANIFEST.json
