"""Save the text of each COA executive summary PDF, and of each report that is a PDF, page by
page, beside the PDF in raw/.

Usage (in a throwaway environment, not a dependency of the repo):
    python -m venv <somewhere outside the repo>
    <venv>/python -m pip install pypdf cryptography
    <venv>/python -I scripts/pdf_pages.py

Writes raw/<year>/<lgu>/<name>.pages.txt for every raw/<year>/<lgu>/*Executive-Summary*.pdf:
the text of each page after a line "=== PDF page N ===". scripts/extract_phase1.py reads these
files to cite the page of an item COA gives only in the executive summary, and to check that
the page shows the same amounts as the copy of the summary inside the Word report.

It does the same for every full report COA posted as a PDF (raw/<year>/<lgu>/extracted/**/
*_Audit_Report.pdf; only Valencia CY 2023), so the figures read from it by hand can be checked
against the page they cite.

The PDFs open without a password but carry an owner password (AES), which is why pypdf needs
cryptography. Only text is extracted; nothing in the PDFs is executed.
"""
from __future__ import annotations

import sys
from pathlib import Path

from pypdf import PdfReader

RAW = Path(__file__).resolve().parent.parent / "raw"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    done = 0
    pdfs = sorted(RAW.glob("20*/*/*Executive-Summary*.pdf")) + sorted(RAW.glob("20*/*/extracted/**/*_Audit_Report.pdf"))
    for pdf in pdfs:
        reader = PdfReader(pdf)
        if reader.is_encrypted:
            reader.decrypt("")
        parts = []
        for n, page in enumerate(reader.pages, 1):
            parts.append(f"=== PDF page {n} ===\n{page.extract_text() or ''}\n")
        out = pdf.with_suffix(".pages.txt")
        out.write_text("".join(parts), encoding="utf-8")
        done += 1
        print(f"{pdf.relative_to(RAW)}: {len(reader.pages)} pages")
    print(f"{done} PDFs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
