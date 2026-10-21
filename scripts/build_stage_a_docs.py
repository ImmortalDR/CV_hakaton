"""Build only Stage A documentation; never modify the presentation."""
from pathlib import Path
from xml.sax.saxutils import escape
from docx import Document
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

root = Path(__file__).resolve().parents[1]
out = root / 'docs/delivery'
font = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
pdfmetrics.registerFont(TTFont('DejaVu', font))
styles = getSampleStyleSheet()
for style in styles.byName.values():
    style.fontName = 'DejaVu'
    style.fontSize = 9
    style.leading = 13
story = []
doc = Document()
for name in ['CHANGELOG_STAGE_A.md', 'FOR_JURY.md', 'STAGE_A_SMOKE.md']:
    path = out / name
    if not path.exists(): continue
    for line in path.read_text().splitlines():
        if line.startswith('#'):
            text = line.lstrip('# ')
            doc.add_heading(text, level=min(3, len(line)-len(line.lstrip('#'))))
            story.append(Paragraph(escape(text), styles['Heading2']))
        elif line:
            doc.add_paragraph(line)
            story.append(Paragraph(escape(line), styles['Normal']))
        else:
            story.append(Spacer(1, 6))
doc.save(out / 'STAGE_A.docx')
SimpleDocTemplate(str(out / 'STAGE_A.pdf'), title='ФСП — сдача этапа A', author='Нанотехнологический альянс').build(story)
print('STAGE_A.docx and STAGE_A.pdf generated; presentation untouched')
