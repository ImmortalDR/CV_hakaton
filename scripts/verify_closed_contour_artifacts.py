"""Read-only structural verification; not a replacement for human/legal review."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
from urllib.parse import unquote

root = Path(__file__).resolve().parents[1]
base = root / 'docs/delivery/closed_contour'
backlog = json.loads((root/'docs/closed_contour_2026-10-21/BACKLOG_CLOSED_CONTOUR.json').read_text())
matrix = json.loads((base/'VERIFY_CLOSED_CONTOUR_MATRIX.json').read_text())
expected = {f'CC{i}' for i in range(15)} | {f'CCV{i}' for i in range(1, 4)}
rows = {r['id']: r for r in matrix['tasks']}
assert len(rows) == len(matrix['tasks']) == 18 and set(rows) == expected
assert {t['id'] for t in backlog['tasks']} == expected
allowed = {'PASS','PARTIAL','FAIL','NOT_RUN','HUMAN_ONLY','N/A'}
for t in backlog['tasks']:
    r = rows[t['id']]
    assert r['status'] == t['status'] and r['status'] in allowed
    assert r['must'] == (t['id'] in backlog['must_for_pitch_claim'])
    assert r['artifact'] == t['artifact']
    for filename in [r['artifact'], *r['evidence']]:
        assert (root/filename.split('#')[0]).is_file(), filename
    if r['status'] == 'PASS': assert r['evidence'] and r['finding']
print('PASS: 18 unique IDs, statuses/artifacts/evidence aligned')
for p in base.glob('*.md'):
    for link in re.findall(r'\]\(([^)]+)\)', p.read_text()):
        if '://' in link or link.startswith('#'): continue
        assert (p.parent/unquote(link.split('#')[0])).exists(), (str(p),link)
print('PASS: local Markdown link targets exist (anchors not validated)')
words = len((base/'PITCH_CLOSED_CONTOUR_90S.md').read_text().split())
assert words <= 190, words
print(f'PASS: pitch {words} whitespace-delimited words including title, <=190; oral timing NOT_RUN')
human = (base/'HUMAN_VERIFY_PROTOCOL_CLOSED_CONTOUR.md').read_text()
assert '☒' not in human and '[x]' not in human.lower() and 'HUMAN_ONLY' in human
assert matrix['human_approval']=='PENDING' and matrix['legal_review']=='NEEDED'
print('PASS: human/legal acceptance remains pending')
log = (base/'evidence/cc-dry-run-20261021T185211Z-233571.log').read_text()
for marker in ['STEP build','STEP up','health ok; demo=false','HTTP 401 expected=401','HTTP 404 expected=404',
               'HTTP 403 expected=403','STEP down','cleanup verified','EXIT_CODE=0']:
    assert marker in log, marker
script_hash = hashlib.sha256((root/'scripts/closed_contour_dry_run.sh').read_bytes()).hexdigest()
assert script_hash in (base/'VERIFY_CLOSED_CONTOUR_PROTOCOL.md').read_text()
print('PASS: dry-run evidence contains required lifecycle and negative checks; executed script SHA256 matches')
subprocess.run(['git','diff','--exit-code','cf91823219e76974a688e8c74f8d3f15dce54e84','--',
                'apps','compose.yaml','.env.example','scripts/configure.py','deploy'],cwd=root,check=True)
print('PASS: application/compose/configure/edge unchanged from reviewed base')
print('INFO: structural checks do not prove customer installation, ACL completeness, legal compliance or WIP byte equality')
