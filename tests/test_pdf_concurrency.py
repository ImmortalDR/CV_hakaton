from concurrent.futures import ThreadPoolExecutor
import pymupdf
from fsp.pdf import profile_pdf


def test_parallel_documents_do_not_crash_or_mix_contacts():
    def render(i):
        email=f'isolated-{i}@example.org'
        p=dict(display_name=f'Кандидат №{i} · ё Ё № ₽',specialization='python',verified_grade='Junior',skills=['python'],contacts={'email':email,'phone':'000'} if i%2 else None,evidence=[],achievements=[],demo=True)
        data=profile_pdf(p)
        with pymupdf.open(stream=data,filetype='pdf') as doc:
            text=''.join(page.get_text() for page in doc)
        assert p['display_name'] in text
        assert (email in text)==bool(i%2)
        assert all(f'isolated-{other}@example.org' not in text for other in range(60) if other!=i)
    with ThreadPoolExecutor(max_workers=30) as pool:
        list(pool.map(render,range(60)))
