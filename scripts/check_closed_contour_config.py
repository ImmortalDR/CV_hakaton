"""Fail closed on tracked runtime env files or changed example credentials.

This narrow deterministic hygiene check is not a repository-wide secret scanner.
"""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
for name in filter(None, tracked):
    base = Path(name).name
    assert not (base == '.env' or base.startswith('.env.') and base != '.env.example'), 'Tracked runtime env file'
print('PASS: runtime .env files absent from git index')
p = subprocess.run(['git', 'check-ignore', '--no-index', '-q', '.env'], cwd=root)
assert p.returncode == 0, '.env must be ignored'
print('PASS: .env ignored')
values = {}
for line in (root / '.env.example').read_text().splitlines():
    if line.strip() and not line.lstrip().startswith('#'):
        key, value = line.split('=', 1)
        values[key] = value
assert values['POSTGRES_PASSWORD'] == 'replace_with_random_value'
assert values['SMTP_PASSWORD'] == '' and values['SMTP_USER'] == ''
assert set(values) == {'POSTGRES_PASSWORD','DEMO_MODE','PUBLIC_URL','BIND_ADDRESS','COOKIE_SECURE',
                      'SMTP_HOST','SMTP_PORT','SMTP_TLS','SMTP_USER','SMTP_PASSWORD','SMTP_FROM'}
assert values['BIND_ADDRESS'] == '127.0.0.1'
assert values['PUBLIC_URL'] == 'http://localhost:3080'
assert values['SMTP_HOST'] == '' and values['SMTP_FROM'] == 'noreply@example.org'
print('PASS: example contains only approved placeholders and loopback defaults')
