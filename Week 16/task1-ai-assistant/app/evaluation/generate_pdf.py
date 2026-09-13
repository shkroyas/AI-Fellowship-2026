"""Render the current audit and assessed write-up from Markdown source."""
from pathlib import Path
import re
from fpdf import FPDF


class ReportPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(55, 65, 81)
        self.cell(0, 7, 'AI Fellowship | Week 16 | Royas Shakya', new_x='LMARGIN', new_y='NEXT')
        self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', size=8)
        self.cell(0, 5, f'Page {self.page_no()}', align='C')


def clean(text):
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = text.translate(str.maketrans({'—': '-', '–': '-', '“': chr(34), '”': chr(34), '’': chr(39)}))
    return text.replace('**', '').replace('`', '').encode('latin-1', 'replace').decode('latin-1')


def render(source, target):
    pdf = ReportPDF()
    pdf.set_margins(15, 12, 15)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    lines = source.read_text().splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            pdf.ln(2)
            index += 1
            continue
        if line.startswith('|'):
            rows = []
            while index < len(lines) and lines[index].startswith('|'):
                row = [clean(cell.strip()) for cell in lines[index].strip('|').split('|')]
                if not all(re.fullmatch(r'[-: ]+', cell) for cell in row):
                    rows.append(row)
                index += 1
            pdf.set_font('Helvetica', size=8)
            with pdf.table(line_height=4, padding=2, col_widths=(1, 1.4, 2) if len(rows[0])==3 else None) as table:
                for cells in rows:
                    row = table.row()
                    for cell in cells:
                        row.cell(cell)
            pdf.ln(3)
            continue
        if line.startswith('#'):
            pdf.ln(2)
            pdf.set_text_color(28, 65, 100)
            pdf.set_font('Helvetica', 'B', 15 if line.startswith('# ') else 11)
            line = line.lstrip('# ')
        else:
            pdf.set_text_color(35, 35, 35)
            pdf.set_font('Helvetica', size=9)
        pdf.multi_cell(0, 4.5, clean(line) or ' ', new_x='LMARGIN', new_y='NEXT')
        index += 1
    pdf.output(str(target))
    print(target.name)


def main():
    root = Path(__file__).resolve().parents[3]
    render(root / 'docs/SUBMISSION_REPORT.md', root / 'docs/SUBMISSION_REPORT.pdf')
    render(root / 'docs/ASSESSMENT.md', root / 'docs/ASSESSMENT.pdf')


if __name__ == '__main__':
    main()
