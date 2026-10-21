"""Explicit download command for pinned public weights; never uploads text."""
import argparse
import json
import os
from pathlib import Path
from urllib.request import urlopen
from enrich import file_hash
from prepare import write_json


def fetch(manifest_path,out):
    os.umask(0o077);out.mkdir(parents=True,exist_ok=True)
    m=json.loads(manifest_path.read_text())
    for name,info in m['files'].items():
        target=out/name
        if target.exists():
            if file_hash(target)!=info['sha256']:raise ValueError('Existing file differs: '+name)
            continue
        target.parent.mkdir(parents=True,exist_ok=True)
        temp=target.with_suffix(target.suffix+'.partial')
        with urlopen(info['url'],timeout=120) as r,temp.open('wb') as f:
            while block:=r.read(1024*1024):f.write(block)
        if file_hash(temp)!=info['sha256'] or temp.stat().st_size!=info['bytes']:raise ValueError('Downloaded checksum mismatch')
        temp.replace(target)
    write_json(out/'manifest.json',m)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,default=Path(__file__).with_name('reports')/'v4-encoder-manifest.json');p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();fetch(a.manifest,a.out)
