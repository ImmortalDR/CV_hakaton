"""Private allowlisted model/data handoff. Encoder fetched separately by hash."""
import argparse
import json
import os
from pathlib import Path
import zipfile
from enrich import file_hash
from package_local import sha,verify


def package(repo,out):
    os.umask(0o077)
    pipeline=repo/'dataset/training';builds=repo/'dataset/builds';root=builds/'trudvsem-model-v4'
    report=json.loads((root/'training-report.json').read_text())
    paths={}
    for name,h in report['code_sha256'].items():
        if file_hash(pipeline/name)!=h:raise ValueError('Measured code changed: '+name)
        paths['pipeline/'+name]=pipeline/name
    for name in ('package_v4.py','package_local.py','fetch_e5_v4.py','EXPERIMENT_V4.md'):
        paths['pipeline/'+name]=pipeline/name
    paths['pipeline/reports/v4-encoder-manifest.json']=pipeline/'reports/v4-encoder-manifest.json'
    for name in ('README_V4.md','RESULTS_V4.md','REVIEW_V4.md'):
        paths['docs/'+name]=pipeline/name
    for name in ('pairs.jsonl','pairs-report.json'):
        paths['data/'+name]=builds/'trudvsem-decisions-v4'/name
    for name in ('corpus.jsonl','corpus-report.json'):
        paths['data/'+name]=builds/'trudvsem-corpus-v4'/name
    for name in ('selection.json','training-report.json','test-embeddings.npz','test-scores.npz','replay.json','run-plan.json'):
        paths['model/'+name]=root/name
    for name,h in report['models'].items():
        f=root/(name+'.joblib')
        if file_hash(f)!=h:raise ValueError('Model changed: '+name)
        paths['model/'+name+'.joblib']=f
    for key,file in [('pairs_sha256','pairs.jsonl'),('corpus_sha256','corpus.jsonl')]:
        if file_hash(paths['data/'+file])!=report[key]:raise ValueError('Measured input changed')
    paths['LICENSE']=repo/'LICENSE'
    payload={}
    for name,path in paths.items():
        if path.is_symlink():raise ValueError('Symlinks forbidden')
        payload[name]=path.read_bytes()
    payload['LOCAL_ONLY.txt']=(
        'PRIVATE LOCAL HANDOFF: real profile text and derived model weights. Do not publish.\n'
        'Source: https://data.rcsi.science/data-catalog/datasets/186/ ; preserve source rights.\n'
        'Our MIT license does not relicense third-party data or E5. No certification.\n'
        'Python 3.12; install pipeline/requirements-v4.lock.txt in an isolated environment.\n'
        'Verify: python pipeline/package_local.py --verify ARCHIVE.zip\n'
        'Replay: python pipeline/experiment_v4.py replay --pairs data/pairs.jsonl --root model\n'
        'Inference encoder (explicit download, no text upload):\n'
        'python pipeline/fetch_e5_v4.py --out encoder\n'
        'Retrain to a fresh directory: python pipeline/experiment_v4.py train --pairs data/pairs.jsonl --corpus data/corpus.jsonl --encoder encoder --out retrained\n'
        'Set OPENBLAS_NUM_THREADS=2 and OMP_NUM_THREADS=2.\n'
    ).encode()
    manifest={'version':4,'mode':'local_only','encoder_weights_included':False,
              'files':{n:{'bytes':len(b),'sha256':sha(b)} for n,b in sorted(payload.items())}}
    payload['MANIFEST.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for n,b in sorted(payload.items()):
            info=zipfile.ZipInfo(n,(2026,10,10,0,0,0));info.external_attr=0o600<<16
            z.writestr(info,b,compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
    return verify(out)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2]);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(package(a.repo,a.out),indent=2))
