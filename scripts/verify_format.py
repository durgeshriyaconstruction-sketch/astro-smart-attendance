#!/usr/bin/env python3
"""
Checks the finished PDF and DOCX against the supplied worksheet format and
prints a verdict per requirement. Exit code 1 if anything is missing.
"""
import json
import os
import sys

from docx import Document
from pypdf import PdfReader

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from format_spec import REQUIREMENTS, score  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(HERE, "Creative-Ideation-Worksheet-Astro-Smart-Attendance.pdf")
DOCX = os.path.join(HERE, "Creative-Ideation-Worksheet-Astro-Smart-Attendance.docx")
REPORT = os.path.join(HERE, "format-report.json")


def pdf_text():
    r = PdfReader(PDF)
    return "\n".join(p.extract_text() or "" for p in r.pages)


def docx_text():
    d = Document(DOCX)
    chunks = [p.text for p in d.paragraphs]
    for sec in d.sections:
        chunks.extend(p.text for p in sec.header.paragraphs)
        chunks.extend(p.text for p in sec.footer.paragraphs)
    for t in d.tables:
        for row in t.rows:
            for cell in row.cells:
                chunks.append(cell.text)
    return "\n".join(chunks)


def main():
    pt, dt = pdf_text(), docx_text()
    pres = score(pt)
    dres = score(dt)

    print(f"PDF  {os.path.getsize(PDF):>7} bytes · {len(PdfReader(PDF).pages)} pages")
    print(f"DOCX {os.path.getsize(DOCX):>7} bytes · {len(Document(DOCX).tables)} tables")
    print()

    fails = 0
    group = None
    for (g, label, ok_p, fp, tp, where, miss_p), (_, _, ok_d, fd, td, _, miss_d) in zip(pres, dres):
        if g != group:
            print(f"--- {g}")
            group = g
        mark = "PASS" if (ok_p and ok_d) else "FAIL"
        if mark == "FAIL":
            fails += 1
        print(f"  [{mark}] {label:52s} PDF {fp}/{tp}  DOCX {fd}/{td}   ({where})")
        for m in miss_p:
            print(f"          pdf missing: {m}")
        for m in miss_d:
            print(f"          docx missing: {m}")

    total = len(pres)
    print()
    print(f"{total - fails}/{total} requirements satisfied in both files")

    json.dump({
        "pdf": {"size": os.path.getsize(PDF), "pages": len(PdfReader(PDF).pages)},
        "docx": {"size": os.path.getsize(DOCX), "tables": len(Document(DOCX).tables)},
        "requirements": [
            {"group": g, "label": l, "pdf_ok": ok_p, "docx_ok": ok_d,
             "pdf_found": f"{fp}/{tp}", "docx_found": f"{fd}/{td}", "where": w}
            for (g, l, ok_p, fp, tp, w, _), (_, _, ok_d, fd, td, _, _) in zip(pres, dres)
        ],
        "failed": fails,
        "total": total,
    }, open(REPORT, "w"), indent=2, ensure_ascii=False)
    print("report ->", REPORT)

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
