"""Private allowlisted offline model/data handoff, including pinned encoder."""
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
    for name in ('package_v4.py','package_local.py','fetch_e5_v4.py','retrieval_v4.py','check_v4.py','rank_v4.py','cv_v4.py','EXPERIMENT_V4.md','EXPERIMENT_V4_CV.md'):
        paths['pipeline/'+name]=pipeline/name
    paths['pipeline/reports/v4-encoder-manifest.json']=pipeline/'reports/v4-encoder-manifest.json'
    for name in ('README_V4.md','RESULTS_V4.md','REVIEW_V4.md','DATA_CARD_V4.md','EXPERIMENT_V4.md','EXPERIMENT_V4_CV.md'):
        paths['docs/'+name]=pipeline/name
    paths['docs/review_v4_coverage.csv']=pipeline/'review_v4_coverage.csv'
    for name in ('v4-pairs.json','v4-corpus.json','v4-training.json','v4-selection.json','v4-replay.json',
                 'v4-retrieval-pool.json','v4-retrieval.json','v4-checks.json','v4-source-continuity.json','v4-encoder-manifest.json',
                 'v4-cv-training.json','v4-cv-selection.json','v4-cv-replay.json','v4-preparation.json','v4-inference.json','v4-start-code.json','v4-execution.json'):
        paths['docs/reports/'+name]=pipeline/'reports'/name
    for name in ('pairs.jsonl','pairs-report.json'):
        paths['data/'+name]=builds/'trudvsem-decisions-v4'/name
    for name in ('corpus.jsonl','corpus-report.json'):
        paths['data/'+name]=builds/'trudvsem-corpus-v4'/name
    for name in ('selection.json','training-report.json','train-embeddings.npz','validation-embeddings.npz','test-embeddings.npz','test-scores.npz','replay.json','run-plan.json'):
        paths['model/'+name]=root/name
    for name,h in report['models'].items():
        f=root/(name+'.joblib')
        if file_hash(f)!=h:raise ValueError('Model changed: '+name)
        paths['model/'+name+'.joblib']=f
    for name,h in report['encoder']['files'].items():
        f=builds/'e5-small-onnx'/name
        if file_hash(f)!=h['sha256']:raise ValueError('Encoder changed: '+name)
        paths['encoder/'+name]=f
    paths['encoder/manifest.json']=builds/'e5-small-onnx/manifest.json'
    cvroot=builds/'trudvsem-model-v4-cv'
    cvreport=json.loads((cvroot/'training-report.json').read_text())
    for name,h in cvreport['code_sha256'].items():
        if file_hash(pipeline/name)!=h:raise ValueError('Measured CV code changed: '+name)
    if cvreport['pairs_sha256']!=report['pairs_sha256'] or cvreport['corpus_sha256']!=report['corpus_sha256']:raise ValueError('CV input mismatch')
    for name in ('selection.json','training-report.json','test-embeddings.npz','test-scores.npz','oof-scores-private.npz','replay.json'):
        paths['model-cv/'+name]=cvroot/name
    for name,h in cvreport['models'].items():
        f=cvroot/(name+'.joblib')
        if file_hash(f)!=h:raise ValueError('CV model changed')
        paths['model-cv/'+name+'.joblib']=f
    retrieval=builds/'trudvsem-retrieval-v4'
    retrieval_report=json.loads((retrieval/'retrieval-report.json').read_text())
    if file_hash(pipeline/'retrieval_v4.py')!=retrieval_report['code_sha256']:raise ValueError('Measured retrieval code changed')
    if retrieval_report['model_sha256']!=report['models']['word_cosine']:raise ValueError('Retrieval model mismatch')
    for name,h in retrieval_report['pool']['files'].items():
        if file_hash(retrieval/name)!=h:raise ValueError('Retrieval pool changed: '+name)
    for name in ('documents.jsonl','queries.jsonl','pool-report.json','retrieval-report.json','embeddings.npz','per-query-private.json'):
        paths['retrieval/'+name]=retrieval/name
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
        'CV replay: python pipeline/experiment_v4.py replay --pairs data/pairs.jsonl --root model-cv\n'
        'Pinned E5 ONNX/tokenizer included under encoder; no network needed for inference.\n'
        'Source model: https://huggingface.co/intfloat/multilingual-e5-small\n'
        'ONNX export: https://huggingface.co/Xenova/multilingual-e5-small\n'
        'Additional checks: python pipeline/check_v4.py --pairs data/pairs.jsonl --model model --retrieval retrieval --encoder encoder --out checked.json\n'
        'Retrain to a fresh directory: python pipeline/experiment_v4.py train --pairs data/pairs.jsonl --corpus data/corpus.jsonl --encoder encoder --out retrained\n'
        'Set OPENBLAS_NUM_THREADS=2 and OMP_NUM_THREADS=2.\n'
    ).encode()
    manifest={'version':4,'mode':'local_only','encoder_weights_included':True,
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
