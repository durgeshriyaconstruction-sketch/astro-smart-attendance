#!/usr/bin/env python3
"""Read back the generated deck and print its text for verification."""
from pptx import Presentation

prs = Presentation("Astro-Smart-Attendance-Concept-Proposal.pptx")
for i, sl in enumerate(prs.slides, 1):
    print(f"\n===== SLIDE {i} =====")
    for sh in sl.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip():
            print(sh.text_frame.text.replace("\n", " | "))
        if sh.has_table:
            for r in sh.table.rows:
                print(" || ".join(c.text for c in r.cells))
