from pathlib import Path
from collections import Counter, defaultdict
import argparse, ast, csv, hashlib, json, re, sys, tomllib
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description='Automatic source scan; not a substitute for reading')
parser.add_argument('pass_number', type=int, choices=(1,2,3))
default_source = Path(__file__).resolve().parents[1] / 'Архив исходников для MVP обратного найма ФСП'
if (default_source / 'fsp_mvp_bundle/github').is_dir():
    default_source = default_source / 'fsp_mvp_bundle'
parser.add_argument('--source-root', type=Path, default=default_source)
parser.add_argument('--out-dir', type=Path, default=Path(__file__).resolve().parents[1] / 'audit/new_scan')
args = parser.parse_args()
ROOT = args.source_root.resolve()
if not (ROOT / 'github').is_dir():
    raise SystemExit(f'Missing source corpus: {ROOT}')
OUT = args.out_dir.resolve()
OUT.mkdir(parents=True, exist_ok=True)
PASS = args.pass_number
records = []
totals = defaultdict(Counter)
for p in sorted(ROOT.rglob('*')):
    if not p.is_file():
        continue
    rel = p.relative_to(ROOT)
    group = rel.parts[1] if rel.parts[0] == 'github' else rel.parts[0]
    raw = p.read_bytes()
    rec = {'path': str(rel), 'group': group, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    totals[group]['files'] += 1
    try:
        text = raw.decode('utf-8-sig')
        if '\x00' in text:
            raise UnicodeError()
    except UnicodeError:
        rec['kind'] = 'binary'
        totals[group]['binary'] += 1
        records.append(rec)
        continue
    totals[group]['text'] += 1
    totals[group]['lines'] += len(text.splitlines())
    rec['kind'] = 'text'
    if PASS == 1:
        rec['lines'] = len(text.splitlines())
        rec['headings'] = re.findall(r'^#{1,3} (.+)$', text, re.M)[:40]
        rec['symbols'] = re.findall(r'^\s*(?:export\s+)?(?:async\s+)?(?:def|class|function|interface|type|const)\s+(\w+)', text, re.M)[:100]
        if p.suffix in ('.json', '.ipynb'):
            try:
                obj = json.loads(text)
                rec['json'] = 'valid'
                if p.suffix == '.ipynb':
                    rec['code_cells'] = sum(c.get('cell_type') == 'code' for c in obj.get('cells', []))
                    rec['cell_code'] = [''.join(c.get('source', [])) for c in obj.get('cells', []) if c.get('cell_type') == 'code']
            except Exception as e:
                rec['parse_note'] = str(e)[:120]
        elif p.suffix == '.py':
            try:
                tree = ast.parse(text)
                rec['python'] = 'valid'
                rec['imports'] = sorted(set(n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module))
            except SyntaxError as e:
                rec['parse_note'] = f'{e.msg}:{e.lineno}'
        elif p.suffix == '.toml':
            try:
                rec['toml'] = 'valid' if isinstance(tomllib.loads(text), dict) else 'other'
            except Exception as e:
                rec['parse_note'] = str(e)[:120]
        elif p.suffix in ('.xml', '.svg'):
            try:
                ET.fromstring(text)
                rec['xml'] = 'valid'
            except Exception as e:
                rec['parse_note'] = str(e)[:120]
    elif PASS == 2:
        # Parse all literal relative JS imports, including dynamically loaded modules.
        deps = re.findall(r'(?:from\s*|import\s*\(\s*|require\s*\(\s*)[\"\']([^\"\']+)[\"\']', text)
        rec['imports'] = sorted(set(deps))
        missing = []
        if p.suffix in ('.ts','.tsx','.js','.jsx','.mjs','.mts','.vue'):
            for dep in deps:
                if not dep.startswith('.') or '*' in dep or '?' in dep:
                    continue
                target = p.parent / dep
                candidates = [target]
                if target.suffix in ('.js','.mjs'):
                    candidates += [target.with_suffix(x) for x in ('.ts','.tsx','.mts')]
                if not target.suffix:
                    candidates += [Path(str(target) + x) for x in ('.ts','.tsx','.js','.jsx','.mjs','.mts','.vue','.json')]
                    candidates += [target / ('index' + x) for x in ('.ts','.tsx','.js','.mjs')]
                if not any(c.exists() for c in candidates):
                    missing.append(dep)
        rec['unresolved_relative_imports'] = sorted(set(missing))
        rec['external_services'] = sorted(set(re.findall(r'\b(?:postgres|mongodb|redis|minio|celery|ollama|openai|anthropic|azure|s3|saml|oidc|keycloak)\b', text, re.I)))
    else:
        patterns = {
            'identity_access': r'contact_grant|consent|authorize|permission|role|tenant|organization_id',
            'assessment': r'grade|grading|item_bank|seed|variant|calibrat|difficulty|cooldown|retake',
            'matching': r'rank|matching|similarity|embedding|must_have|evidence|requirements',
            'invitations': r'invitation|invite|salary|accepted|rejected|contact',
            'evaluation': r'eval_set|test_size|GroupShuffleSplit|TargetEncoder|precision_at|ndcg|ground_truth',
            'potential_risk': r'express\.static|sendFile|model_dump|\.populate\(|predict_proba|privileged:|\.\./ee/|/ee/|Math\.random|random\.seed|trust_remote_code|torch\.load',
        }
        rec['signals'] = {k: len(re.findall(v,text,re.I)) for k,v in patterns.items()}
        rec['risk_lines'] = [f'{i}: {line.strip()[:240]}' for i,line in enumerate(text.splitlines(),1) if re.search(patterns['potential_risk'],line,re.I)][:60]
    records.append(rec)
dest = OUT / f'pass{PASS}.json'
dest.write_text(json.dumps(records,ensure_ascii=False))
print(json.dumps({'pass':PASS,'coverage':dict(totals),'record_count':len(records)},ensure_ascii=False,indent=2))
if PASS == 1:
    notes = [r for r in records if 'parse_note' in r]
    print('PARSE_NOTES',len(notes))
    for r in notes[:45]:
        print(r['path'],r['parse_note'])
if PASS == 2:
    missing = [r for r in records if r.get('unresolved_relative_imports')]
    print('FILES_WITH_UNRESOLVED_IMPORTS',len(missing))
    print('BY_PROJECT',dict(Counter(r['group'] for r in missing)))
    for r in missing[:25]:
        print(r['path'],r['unresolved_relative_imports'][:6])
