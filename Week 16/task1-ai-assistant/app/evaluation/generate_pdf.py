"""Render the current submission Markdown; metrics are never hard-coded here."""
from pathlib import Path
import re
from fpdf import FPDF

def clean(text):
    return re.sub(r'\[([^]]+)\]\(([^)]+)\)',r'\1 (\2)',text).replace('**','').replace('`','')

def render(source, target):
    pdf=FPDF()
    pdf.set_auto_page_break(auto=True,margin=15)
    fonts=Path('/usr/share/fonts/truetype/dejavu')
    if not (fonts/'DejaVuSans.ttf').exists():
        raise RuntimeError('Install DejaVu Sans before rendering Unicode documentation')
    pdf.add_font('DejaVu',fname=str(fonts/'DejaVuSans.ttf'))
    pdf.add_font('DejaVu',style='B',fname=str(fonts/'DejaVuSans-Bold.ttf'))
    pdf.add_page(); lines=source.read_text().splitlines(); i=0
    while i<len(lines):
        line=lines[i]
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                cells=[clean(c.strip()) for c in lines[i].strip('|').split('|')]
                if not all(re.fullmatch(r'[:\- ]+',c or '-') for c in cells): rows.append(cells)
                i+=1
            if rows:
                pdf.set_font('DejaVu',size=7.5)
                with pdf.table(line_height=4.3,padding=1) as table:
                    for cells in rows:
                        row=table.row()
                        for cell in cells: row.cell(cell)
            pdf.ln(3);continue
        heading=line.startswith('#')
        pdf.set_font('DejaVu',style='B' if heading else '',size=12 if heading else 9)
        if not line.startswith('```'):
            pdf.multi_cell(0,6 if heading else 4.5,text=clean(line.lstrip('# ') if heading else line) or ' ',new_x='LMARGIN',new_y='NEXT')
        i+=1
    pdf.output(str(target))

if __name__=='__main__':
    root=Path(__file__).resolve().parents[3]
    render(root/'docs/SUBMISSION_REPORT.md',root/'docs/SUBMISSION_REPORT.pdf')
    render(root/'docs/ASSESSMENT.md',root/'docs/ASSESSMENT.pdf')
