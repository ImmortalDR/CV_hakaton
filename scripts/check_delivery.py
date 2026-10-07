"""Read-only checks for exported specifications, documents and actual logs."""

import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pymupdf
from docx import Document
from pptx import Presentation

root = Path(__file__).resolve().parents[1]
out = root / "docs/delivery"
junit = ET.parse(out / "tests.junit.xml").getroot()
suites = list(junit.iter("testsuite"))
tests = sum(int(s.get("tests", 0)) for s in suites)
assert tests == 36
assert all(int(s.get("failures", 0)) == int(s.get("errors", 0)) == 0 for s in suites)
api = json.loads((out / "openapi.json").read_text())
live = httpx.get("http://127.0.0.1:3080/api/openapi.json").json()
assert api == live
assert sum(len(v) for v in api["paths"].values()) == 27
assert all(
    "responses" in operation
    for path in api["paths"].values()
    for operation in path.values()
)
assert "SessionCookie" in api["components"]["securitySchemes"]
deck = Presentation(root / "demo/FSP_MVP.pptx")
assert len(deck.slides) == 8
with pymupdf.open(root / "demo/FSP_MVP.pdf") as pdf:
    assert len(pdf) == 8
    slide_text = "\n".join(page.get_text() for page in pdf)
    for text in [
        "Данила",
        "Никита",
        "Тимофей",
        "0,80",
        "0,475",
        "36 тестов",
        "Следующий этап",
    ]:
        assert text in slide_text, text
    for placeholder in [
        "Имя Фамилия",
        "Расскажите,",
        "Опишите ваши",
        "Кол-во участников: __",
    ]:
        assert placeholder not in slide_text
    slide_pages = len(pdf)
with pymupdf.open(out / "FSP_MVP.pdf") as pdf:
    doc_text = "\n".join(page.get_text() for page in pdf)
    document_pages = len(pdf)
    assert all(len(page.get_text()) > 100 for page in pdf)
    for keyword in ["Архитектура", "Матрица", "API 1.0.0", "Keycloak", "235/240"]:
        assert keyword.lower() in doc_text.lower(), keyword
with pymupdf.open(root / "audit/current/docx-preview/FSP_MVP.pdf") as rendered_docx:
    docx_render_pages = len(rendered_docx)
    for page in rendered_docx:
        for x0, y0, x1, y1, *_ in page.get_text("blocks"):
            assert (
                x0 >= 0
                and y0 >= 0
                and x1 <= page.rect.width + 1
                and y1 <= page.rect.height + 1
            )
docx = Document(out / "FSP_MVP.docx")
assert len(docx.paragraphs) > 100 and len(docx.tables) >= 5
audit = json.loads((root / "audit/current/pip-audit-final.json").read_text())
assert not any(d["vulns"] for d in audit["dependencies"])
npm = json.loads((root / "audit/current/npm-audit.json").read_text())
assert npm["metadata"]["vulnerabilities"]["total"] == 0
integrity = json.loads((out / "input-integrity.json").read_text())
assert integrity["ok"]
load = json.loads((out / "load-results.json").read_text())
assert load["all"]["errors"] == 0
browser = json.loads((out / "browser-result.json").read_text())
assert browser["status"] == "pass"
recording = json.loads((root / "demo/browser-result.json").read_text())
assert recording["status"] == "pass"
video = json.loads(
    subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size",
            "-show_entries",
            "stream=codec_name,width,height",
            "-of",
            "json",
            str(root / "demo/walkthrough.webm"),
        ]
    )
)
assert 180 <= float(video["format"]["duration"]) <= 300
artifacts = [
    "demo/FSP_MVP.pptx",
    "demo/FSP_MVP.pdf",
    "demo/walkthrough.webm",
    "docs/delivery/FSP_MVP.docx",
    "docs/delivery/FSP_MVP.pdf",
    "docs/delivery/openapi.json",
]
result = {
    "status": "pass",
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "unit_integration_tests": tests,
    "openapi_operations": 27,
    "openapi_models": len(api["components"]["schemas"]),
    "presentation_slides": slide_pages,
    "documentation_pdf_pages": document_pages,
    "docx_paragraphs": len(docx.paragraphs),
    "docx_render_pages": docx_render_pages,
    "docx_tables": len(docx.tables),
    "dependency_audits": {
        "npm_known_vulnerabilities": 0,
        "pip_known_vulnerabilities": 0,
        "scope": "runtime dependencies, current advisory databases; not a full security audit",
    },
    "preserved_inputs": integrity["checked_files"],
    "video": video,
    "visual_review": "All eight slide renders reviewed; contrast/overlap fixed. Documentation PDF pages reviewed. Desktop/mobile UI and video captures inspected.",
    "artifacts": {
        name: {
            "bytes": (root / name).stat().st_size,
            "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest(),
        }
        for name in artifacts
    },
}
(out / "release-checks.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n"
)
print(json.dumps(result, ensure_ascii=False, indent=2))
