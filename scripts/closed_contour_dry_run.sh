#!/usr/bin/env bash
# Disposable installation from committed source. Never operates on base compose at runtime.
set -Eeuo pipefail
umask 077
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
mkdir -p docs/delivery/closed_contour/evidence tmp
stamp=$(date -u +%Y%m%dT%H%M%SZ)
project="fsp-cc-dryrun-${stamp,,}-$$"
log="$root/docs/delivery/closed_contour/evidence/cc-dry-run-$stamp-$$.log"
exec > >(tee "$log") 2>&1
printf 'UTC=%s project=%s\n' "$stamp" "$project"
printf 'source_sha=%s\n' "$(git rev-parse HEAD)"
work=$(mktemp -d "$root/tmp/cc-install.XXXXXXXX")
ready=false
# Use only the local daemon; ignore shell COMPOSE_* and application credentials.
docker_local() { env -i PATH="$PATH" HOME="$HOME" COMPOSE_PARALLEL_LIMIT=1 docker --host unix:///var/run/docker.sock "$@"; }
compose() { docker_local compose --project-directory "$work" --env-file "$work/.env" -p "$project" -f "$work/isolated.json" "$@"; }
cleanup() {
  rc=$?
  trap - EXIT
  set +e
  if "$ready"; then
    echo 'STEP down disposable project (including its disposable volume)'
    compose down --volumes --remove-orphans --timeout 20
    down_rc=$?
    if (( down_rc != 0 )); then rc=1; fi
    remaining=$(docker_local ps -aq --filter "label=com.docker.compose.project=$project")
    volumes=$(docker_local volume ls -q --filter "label=com.docker.compose.project=$project")
    if [[ -n "$remaining$volumes" ]]; then echo 'FAIL disposable resources remain'; rc=1; else echo 'cleanup verified: no project containers or volumes'; fi
  fi
  # work is exclusively mktemp-created by this invocation; contains generated secrets.
  rm -rf -- "$work"
  printf 'EXIT_CODE=%s\n' "$rc"
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
command -v python3 >/dev/null
docker_local compose version
docker_local info --format 'Docker server={{.ServerVersion}}'
echo 'STEP copy committed source and configure'
git archive HEAD | tar -x -C "$work"
python3 "$work/scripts/configure.py"
# Only synthetic smoke; exercise non-demo boot without customer SMTP credentials.
python3 - "$work/.env" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
p.write_text(p.read_text().replace('DEMO_MODE=true', 'DEMO_MODE=false'))
PY
docker_local compose --project-directory "$work" --env-file "$work/.env" -p "$project" -f "$work/compose.yaml" config --format json > "$work/resolved.json"
python3 - "$work" "$project" <<'PY'
import json, sys
from pathlib import Path
w, project = Path(sys.argv[1]), sys.argv[2]
d = json.loads((w/'resolved.json').read_text())
d['name'] = project
d['services'].pop('edge', None)
d['volumes'] = {'fsp_db': {'name': project + '_fsp_db'}}
d['networks'] = {'default': {'name': project + '_default'}}
for name, s in d['services'].items():
    assert name in {'db', 'api', 'web', 'task-worker'}
    for key in ('container_name','network_mode','profiles'):
        assert key not in s, (name, key)
    s.pop('ports', None)
    if 'build' in s:
        # Build contexts were resolved inside this invocation's private copy.
        assert Path(s['build']['context']).is_relative_to(w)
    s['cpus'] = 1.0
    s['mem_limit'] = '512m'
    for v in s.get('volumes', []):
        assert v['type'] == 'volume' and v['source'] == 'fsp_db'
d['services']['web']['ports'] = [{'target':80, 'published':'0', 'host_ip':'127.0.0.1', 'protocol':'tcp'}]
(w/'isolated.json').write_text(json.dumps(d))
print('isolation verified: local daemon, unique volume/network, no edge, no DB host port, loopback ephemeral web')
PY
ready=true
compose config --quiet
echo 'STEP build'
compose build
echo 'STEP up'
compose up -d --wait --wait-timeout 180 db api task-worker web
compose ps
endpoint=$(compose port web 80)
[[ "$endpoint" =~ ^127\.0\.0\.1:[0-9]+$ ]]
python3 - "http://$endpoint" <<'PY'
import json, sys, urllib.request, urllib.error
base = sys.argv[1]
def request(path, code=200, payload=None, header=True):
    headers = {'Content-Type':'application/json'}
    if header: headers['X-Requested-With'] = 'fsp-web'
    req = urllib.request.Request(base+path, data=None if payload is None else json.dumps(payload).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r: status, data = r.status, r.read()
    except urllib.error.HTTPError as e: status, data = e.code, e.read()
    assert status == code, (path, status, code)
    print(f'API {path} HTTP {status} expected={code}')
    return json.loads(data)
health = request('/api/health')
assert health['status']=='ok' and health['demo'] is False
print('health ok; demo=false')
assert request('/api/catalog')['demo'] is False
assert '/api/me/profile' in request('/api/openapi.json')['paths']
request('/api/me/profile', 401)
request('/api/auth/demo', 404, {'account':'candidate'})
request('/api/auth/demo', 403, {'account':'candidate'}, False)
print('minimum API and negative access checks passed')
PY
echo 'STEP verify worker process'
compose exec -T task-worker python -c "from pathlib import Path; assert b'fsp.task_worker' in Path('/proc/1/cmdline').read_bytes(); print('worker process ok')"
