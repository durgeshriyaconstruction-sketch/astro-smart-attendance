#!/usr/bin/env python3
"""
The literal requirements of the supplied ABG STEM Quest Creative Ideation
Worksheet format, expressed as checkable strings.

Every entry is a phrase the format document actually contains, or a named
element it explicitly asks a student to show. `verify_format.py` tests each
one against the finished PDF and DOCX, so the compliance report is computed
rather than claimed.
"""

# group, label, list of required phrases (all must be present), where it is answered
REQUIREMENTS = [
    ("Header", "Programme name",
     ["ABG STEM QUEST 2026"], "Running header, every page"),
    ("Header", "Document title",
     ["CREATIVE IDEATION WORKSHEET"], "Pill, every page"),
    ("Header", "Team and school line",
     ["Sun Rises India", "Grade 9", "ABPS Renukoot"], "Cover badge and team panel"),
    ("Header", "Team captain",
     ["Shaurya Gupta"], "Team panel, captain row"),
    ("Header", "Members",
     ["Anant Tiwari", "Devansh Dhakad", "Tejas Upadhyay", "Diwakar Singh"], "Team panel, member row"),
    ("Header", "Theme",
     ["SDG 9"], "Team panel and footer"),

    ("1. Problem focus", "Section heading",
     ["Problem focus"], "Numbered block, page 1"),
    ("1. Problem focus", "Discovery question, all four parts",
     ["Who feels it", "What happens now", "prove it worked"], "Four discovery-question rows"),
    ("1. Problem focus", "The registered problem, in our own numbers",
     ["10–15 minutes", "proxy"], "Problem card and size-of-problem strip"),

    ("2. Brainstormed possibilities", "Section heading",
     ["Brainstormed possibilities"], "Numbered block, page 2"),
    ("2. Brainstormed possibilities", "All ten ideas from the format",
     ["RFID card tap", "QR code attendance", "digital register", "NFC check-in",
      "Face recognition", "Bluetooth proximity", "Offline attendance",
      "Duplicate", "attendance summary", "Audit log"], "Ten idea cards with a verdict each"),
    ("2. Brainstormed possibilities", "Filtering on purpose",
     ["build it", "afford", "respect"], "Three filter cards and a filter matrix"),

    ("3. Concept map", "Section heading",
     ["Concept map"], "Numbered block, page 3"),
    ("3. Concept map", "The six stage labels, verbatim",
     ["USER / SETTING", "PROBLEM TRIGGER", "SENSOR OR INPUT",
      "PROCESS / DECISION", "OUTPUT / ACTION", "MEASURABLE BENEFIT"], "Six drawn chain stages"),
    ("3. Concept map", "Proposed direction line",
     ["Proposed direction", "Astro Smart Attendance"], "Direction band"),

    ("4. Shortlisting matrix", "Section heading",
     ["Shortlisting matrix"], "Numbered block, page 4"),
    ("4. Shortlisting matrix", "The five criteria, verbatim",
     ["Novelty", "Feasibility", "Affordability", "Impact", "Prototype potential"], "Matrix column headers"),
    ("4. Shortlisting matrix", "Scoring note: hypotheses, 1 to 5, cited evidence",
     ["initial team hypotheses", "1 (low) to 5 (high)", "evidence"], "Scoring-note panel"),
    ("4. Shortlisting matrix", "Four candidate types from the format",
     ["Simpler digital register", "Sensor / app-only", "Community / service", "Face recognition"],
     "Six scored rows"),

    ("5. Selected concept and reason", "Section heading",
     ["Selected concept"], "Numbered block, page 5"),
    ("5. Selected concept and reason", "Registration of time, class and pseudonymous ID",
     ["pseudonymous"], "Concept band"),
    ("5. Selected concept and reason", "Selection rationale, all three legs",
     ["registered problem", "prototype", "measurable"], "Four reason cards"),

    ("6. Initial system sketch", "Section heading",
     ["Initial system sketch"], "Numbered block, page 6"),
    ("6. Initial system sketch", "All six named blocks the format asks for",
     ["STUDENT", "RC522 READER", "ESP32 CONTROLLER", "LCD1602", "HUMAN CONFIRMATION", "POWER SOURCE"],
     "Drawn block diagram"),
    ("6. Initial system sketch", "The bracketed prompt is answered, not left blank",
     ["labelled block diagram"], "Section subtitle"),

    ("7. What the team must validate next", "Section heading",
     ["must validate next"], "Numbered block, page 7"),
    ("7. What the team must validate next", "Five validation duties",
     ["3–5", "frequent enough", "two existing products", "proof of concept",
      "invent nothing"], "Five rows, each with a decision rule"),

    ("8. Prototype success indicators", "Section heading",
     ["Prototype success indicators"], "Numbered block, page 7"),
    ("8. Prototype success indicators", "The five indicators, verbatim",
     ["class of 30", "Duplicate scan rejection", "Late and invalid", "sync", "Teacher usability"],
     "Six indicator cards with targets"),

    ("9. Risks and design safeguards", "Section heading",
     ["Risks and design safeguards"], "Numbered block, page 8"),
    ("9. Risks and design safeguards", "Risk-to-safeguard pairing",
     ["Safeguard", "card", "network", "privacy"], "Six risk rows"),

    ("Two-factor verification", "The fingerprint sensor is named and costed",
     ["R307", "second factor", "≈ ₹950"], "BOM row, diagram block and concept band"),
    ("Two-factor verification", "Proxy prevention stated as a safeguard",
     ["proxy", "both agree"], "Risk row and concept band"),
    ("Two-factor verification", "Biometric privacy handled, not ignored",
     ["templates", "consent"], "Risk row and concept band"),
    ("Two-factor verification", "Validated, not assumed",
     ["wrong finger"], "Sixth validation duty with a decision rule"),

    ("Team reflection", "All three reflection prompts",
     ["reject", "changed our thinking", "smallest test"], "Three answered reflection cards"),
]


def normalise(text):
    """Whitespace-free, lower-case form: survives per-character drawn headings."""
    out = []
    for ch in text:
        if ch.isspace():
            continue
        if ch in "\u2013\u2014\u2012":
            out.append("-")
        elif ch in "\u2018\u2019":
            out.append("'")
        elif ch in "\u201c\u201d":
            out.append('"')
        else:
            out.append(ch.lower())
    return "".join(out)


def score(text):
    """Return a list of (group, label, ok, found, total, where, missing)."""
    hay = normalise(text)
    results = []
    for group, label, phrases, where in REQUIREMENTS:
        missing = [p for p in phrases if normalise(p) not in hay]
        results.append((group, label, not missing, len(phrases) - len(missing),
                        len(phrases), where, missing))
    return results
