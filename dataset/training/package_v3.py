"""Explicit allowlist for a private, reproducible V3/V3-CV handoff."""
import argparse
import json
import os
from pathlib import Path
import zipfile

from enrich import file_hash
from package_local import sha, verify

FAMILIES=('base_pair','enriched_word','dual_pair','dense_pair','boosted_pair',
          'pairwise_dense','pairwise_dual','job_only','candidate_only')


def package(repo,out):
    os.umask(0o077)
    paths={}
    pipeline=repo/'dataset/training'
    for name in ('prepare.py','pairs.py','application_pairs.py','train.py','enrich.py',
                 'rank_features.py','experiment_v3.py','cross_validate_v3.py','predict_v3.py',
                 'package_local.py','package_v3.py','requirements.lock.txt','EXPERIMENT_V3.md','EXPERIMENT_V3_CV.md'):
        paths['pipeline/'+name]=pipeline/name
    for name in ('RESULTS_V3.md','README_V3.md'):
        paths['docs/'+name]=pipeline/name
    for name in ('v3-input-continuity.json','v3-secondary-analysis.json','v3-pairs.json',
                 'v3-training.json','v3-selection.json','v3-replay.json','v3-cv-training.json',
                 'v3-cv-selection.json','v3-cv-replay.json','v3-checks.json'):
        paths['docs/reports/'+name]=pipeline/'reports'/name
    paths['LICENSE']=repo/'LICENSE'
    for name in ('pairs.jsonl','pairs-report.json'):
        paths['data/v3/'+name]=repo/'dataset/builds/trudvsem-decisions-v3-final'/name
    for tag,directory in [('v3','trudvsem-model-v3'),('v3-cv','trudvsem-model-v3-cv')]:
        root=repo/'dataset/builds'/directory
        report=json.loads((root/'training-report.json').read_text())
        selection=json.loads((root/'selection.json').read_text())
        if file_hash(paths['data/v3/pairs.jsonl'])!=report['pairs_sha256']:
            raise ValueError('Pair checksum mismatch')
        for name,expected in report['code_sha256'].items():
            if file_hash(pipeline/name)!=expected:
                raise ValueError('Measured source code changed: '+name)
        for name in ('training-report.json','selection.json','split-manifest.json',
                     'test-predictions.jsonl','replay.json'):
            paths[f'models/{tag}/{name}']=root/name
        if tag=='v3-cv':
            paths[f'models/{tag}/oof-predictions.jsonl']=root/'oof-predictions.jsonl'
        for family in FAMILIES:
            if family not in selection['families']:
                continue
            model=root/(family+'.joblib')
            if file_hash(model)!=selection['families'][family]['artifact_sha256']:
                raise ValueError('Model checksum mismatch')
            paths[f'models/{tag}/{family}.joblib']=model
    paths['provenance/extractor-at-scan.py']=repo/'dataset/builds/trudvsem-enrichment-v3/extractor-at-scan.py'
    paths['provenance/enrichment-scan.json']=repo/'dataset/builds/trudvsem-enrichment-v3/complete.json'
    payload={}
    for name,path in paths.items():
        if path.is_symlink():
            raise ValueError('Symlinks forbidden')
        payload[name]=path.read_bytes()
    for name in ('docs/README_V3.md','docs/RESULTS_V3.md'):
        text=payload[name].decode()
        for protocol in ('EXPERIMENT_V3.md','EXPERIMENT_V3_CV.md'):
            text=text.replace('('+protocol+')','(../pipeline/'+protocol+')')
        text=text.replace('(README.md)','(https://github.com/ImmortalDR/CV_hakaton/blob/codex/fsp-mvp/dataset/training/README.md)')
        payload[name]=text.encode()
    payload['LOCAL_ONLY.txt']=(
        'PRIVATE LOCAL HANDOFF. Real profile texts and model weights: do not upload to public GitHub.\n'
        'Original source: https://data.rcsi.science/data-catalog/datasets/186/ (CC BY-SA).\n'
        'Root MIT license applies to our code, not to third-party data. No expert certification.\n'
        'Python 3.12. Install pipeline/requirements.lock.txt. Verify the ZIP with:\n'
        'python pipeline/package_local.py --verify ARCHIVE.zip\n'
        'Replay all saved model predictions and metrics without raw CSVs:\n'
        'OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python pipeline/experiment_v3.py replay --root data/v3 --out models/v3\n'
        'OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python pipeline/experiment_v3.py replay --root data/v3 --out models/v3-cv\n'
        'Retrain (new output directories required):\n'
        'OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python pipeline/experiment_v3.py run --root data/v3 --out retrained/v3\n'
        'OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python pipeline/cross_validate_v3.py --root data/v3 --out retrained/v3-cv\n'
        'Both experiments reuse the historical corpus; these are not blind external validation results.\n'
    ).encode()
    manifest={'version':3,'mode':'local_only','raw_source_files_included':False,
              'files':{name:{'bytes':len(data),'sha256':sha(data)} for name,data in sorted(payload.items())}}
    payload['MANIFEST.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(payload.items()):
            info=zipfile.ZipInfo(name,(2026,10,10,0,0,0))
            info.external_attr=0o600<<16
            z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    return verify(out)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(package(a.repo,a.out),indent=2))
