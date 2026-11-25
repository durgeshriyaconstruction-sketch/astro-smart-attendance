#!/usr/bin/env python3
"""
Builds the editable Word version of the Creative Ideation Worksheet.
Same structure and content as the print PDF, laid out for a school to edit.
"""
import os

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "Creative-Ideation-Worksheet-Astro-Smart-Attendance.docx")

NAVY = RGBColor(0x0B, 0x1F, 0x4A)
NAVY_HEX = "0B1F4A"
SAFFRON = RGBColor(0xC2, 0x41, 0x0C)
TEAL = RGBColor(0x0E, 0x74, 0x74)
GREY = RGBColor(0x47, 0x55, 0x69)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT = "F1F5F9"
CREAM = "FDFCF8"
GREEN_HEX = "ECFDF5"

FONT = "Calibri"


# ----------------------------------------------------------------- helpers
def shade(cell, hexcolor):
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear")
    el.set(qn("w:color"), "auto")
    el.set(qn("w:fill"), hexcolor)
    cell._tc.get_or_add_tcPr().append(el)


def borders(table, color="D8DEE9", sz=4):
    tbl = table._tbl
    pr = tbl.tblPr
    el = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement("w:" + edge)
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), str(sz))
        e.set(qn("w:color"), color)
        pr.append(el)
        el.append(e)


def cell_text(cell, text, size=9.5, bold=False, color=GREY, align=None, italic=False):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)
    if align:
        p.alignment = align
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = color
    r.font.name = FONT
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


def para(doc, text, size=10, bold=False, color=GREY, space_after=6, italic=False,
         align=None, space_before=0):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(space_before)
    if align:
        p.alignment = align
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = color
    r.font.name = FONT
    return p


def heading(doc, number, title, sub=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(f"{number:02d}   {title.upper()}")
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = NAVY
    r.font.name = FONT
    if sub:
        para(doc, sub, size=9.5, color=RGBColor(0x64, 0x74, 0x8B), space_after=8)


def section_label(doc, text, color=SAFFRON):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(text.upper())
    r.font.size = Pt(8)
    r.font.bold = True
    r.font.color.rgb = color
    r.font.name = FONT


def fixed_layout(t):
    pr = t._tbl.tblPr
    el = OxmlElement("w:tblLayout")
    el.set(qn("w:type"), "fixed")
    pr.append(el)


def table(doc, head, rows, widths, size=9, head_fill=NAVY_HEX, zebra=True, aligns=None):
    t = doc.add_table(rows=1, cols=len(head))
    t.autofit = False
    fixed_layout(t)
    borders(t)
    for i, h in enumerate(head):
        c = t.rows[0].cells[i]
        shade(c, head_fill)
        cell_text(c, h, size=size - 0.5, bold=True, color=WHITE)
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for i, val in enumerate(row):
            align = None
            if aligns and aligns[i] == "r":
                align = WD_ALIGN_PARAGRAPH.RIGHT
            elif aligns and aligns[i] == "c":
                align = WD_ALIGN_PARAGRAPH.CENTER
            cell_text(cells[i], val, size=size, bold=(i == 0 and len(head) > 1 and widths[i] > 3),
                      color=NAVY if i == 0 else GREY, align=align)
            if zebra and ri % 2 == 1:
                shade(cells[i], LIGHT)
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit")
        trPr.append(cant)
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
    # repeat the header row on every page a long table spills onto
    trPr = t.rows[0]._tr.get_or_add_trPr()
    hdr = OxmlElement("w:tblHeader")
    trPr.append(hdr)
    return t


def callout(doc, label, body, fill=CREAM):
    t = doc.add_table(rows=1, cols=1)
    borders(t, "E5E7EB")
    c = t.rows[0].cells[0]
    shade(c, fill)
    c.text = ""
    p = c.paragraphs[0]
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(label.upper() + "   ")
    r.font.size = Pt(8)
    r.font.bold = True
    r.font.color.rgb = SAFFRON
    r.font.name = FONT
    r2 = p.add_run(body)
    r2.font.size = Pt(9.5)
    r2.font.color.rgb = NAVY
    r2.font.name = FONT
    c.width = Cm(17.6)
    return t


def spacer(doc, pt=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    p.add_run("").font.size = Pt(pt)


# ----------------------------------------------------------------- document
def build():
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = FONT
    st.font.size = Pt(10)

    s = doc.sections[0]
    s.top_margin = Cm(1.6)
    s.bottom_margin = Cm(1.6)
    s.left_margin = Cm(1.7)
    s.right_margin = Cm(1.7)

    # running header
    hp = s.header.paragraphs[0]
    hr = hp.add_run("ABG STEM QUEST 2026–27            PART 1 — CREATIVE IDEATION WORKSHEET")
    hr.font.size = Pt(8)
    hr.font.bold = True
    hr.font.color.rgb = NAVY
    hr.font.name = FONT

    fp = s.footer.paragraphs[0]
    fr = fp.add_run("ASTRO SMART ATTENDANCE  ·  Sun Rises India  ·  ABPS Renukoot  ·  SDG 9")
    fr.font.size = Pt(8)
    fr.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
    fr.font.name = FONT

    # ---------------- title block
    t = doc.add_table(rows=1, cols=1)
    borders(t, NAVY_HEX)
    c = t.rows[0].cells[0]
    shade(c, NAVY_HEX)
    c.text = ""
    p = c.paragraphs[0]
    p.paragraph_format.space_before = Pt(10)
    r = p.add_run("ASTRO SMART ATTENDANCE")
    r.font.size = Pt(26)
    r.font.bold = True
    r.font.color.rgb = WHITE
    r.font.name = FONT
    p2 = c.add_paragraph()
    r2 = p2.add_run("AI + IoT + Cloud  smart school attendance system")
    r2.font.size = Pt(11)
    r2.font.bold = True
    r2.font.color.rgb = RGBColor(0xFF, 0xB7, 0x03)
    r2.font.name = FONT
    p3 = c.add_paragraph()
    p3.paragraph_format.space_before = Pt(6)
    r3 = p3.add_run(
        "A compact ESP32 RFID attendance terminal with Astro AI 2.0 self-healing, a Firebase dashboard "
        "and automatic parent alerts — offline-first, built from low-cost local parts.")
    r3.font.size = Pt(9.5)
    r3.font.color.rgb = RGBColor(0xDB, 0xE6, 0xF7)
    r3.font.name = FONT
    p4 = c.add_paragraph()
    p4.paragraph_format.space_before = Pt(6)
    r4 = p4.add_run("One tap. Attendance done. Parents informed.    ·    astro-smart-attendence.web.app")
    r4.font.size = Pt(10)
    r4.font.italic = True
    r4.font.color.rgb = RGBColor(0xFF, 0xB7, 0x03)
    r4.font.name = FONT

    spacer(doc, 8)
    table(doc, ["Field", "Detail"],
          [["School", "ABPS Renukoot, Sonbhadra (U.P.)"],
           ["Team", "Sun Rises India"],
           ["Grade", "9th"],
           ["Theme", "SDG 9 — Industry, Innovation and Infrastructure"],
           ["Team captain", "Shaurya Gupta"],
           ["Members", "Shaurya Gupta, Anant Tiwari, Devansh Dhakad, Tejas Upadhyay, Diwakar Singh"],
           ["Mentor", "Dr. Jayesh Shinde"]],
          [3.6, 14.0], size=9.5)

    spacer(doc, 8)
    table(doc, ["≈ ₹2,450", "≈ 3 sec", "Offline", "140 / 140"],
          [["Est. cost per unit", "Card + fingerprint", "Syncs when back", "Feature tests passing"]],
          [4.4, 4.4, 4.4, 4.4], size=9, zebra=False, aligns=["c", "c", "c", "c"])

    # ---------------- 1
    doc.add_page_break()
    heading(doc, 1, "Problem focus", "Who feels it, when it happens, and what proof of improvement looks like")
    para(doc, "Manual attendance can be time-consuming and vulnerable to recording errors or proxy attendance. "
              "The team proposes an AI-supported system to record and manage attendance.", size=10)
    para(doc, "Indian schools lose 10–15 minutes per class to manual attendance. Across 15+ lakh schools, paper "
              "registers are slow, easy to lose and open to proxy attendance — and the record never reaches the "
              "parent the same day. Our answer: an RFID + fingerprint terminal that verifies a student in about three "
              "seconds, keeps recording without internet, and alerts the parent automatically.", size=10)

    section_label(doc, "Discovery questions")
    table(doc, ["Question", "Our answer"],
          [["Who feels it?", "Teachers, students, parents, the school office"],
           ["When?", "Every period, worst at the first bell"],
           ["What happens now?", "Paper register, verbal roll-call"],
           ["What would prove it worked?", "Minutes saved, zero proxy, fast alerts"]],
          [6.0, 11.6], size=9.5)

    spacer(doc, 6)
    section_label(doc, "What we saw with our own eyes")
    para(doc, "Assembly queues for the register · two names ticked twice in the same period · late arrivals argued "
              "about at the office · parents learning of absence after school.", size=9.5, space_after=4)

    section_label(doc, "Success looks like")
    para(doc, "30 students verified in under 90 seconds, no duplicate entries, and every parent alerted within 5 "
              "minutes of the period ending.", size=9.5, space_after=4)

    section_label(doc, "What users told us — anonymised notes from discovery dialogues")
    table(doc, ["Quote", "Who"],
          [["\u201cFifteen minutes gone every period, just calling out names. I could teach a whole concept in that time.\u201d", "Class teacher · ABPS Renukoot"],
           ["\u201cWe find out our child was absent only when the day is over. By then the whole day is lost.\u201d", "Parent · Renukoot"]],
          [12.4, 5.2], size=9.5)

    spacer(doc, 6)
    table(doc, ["10–15 min", "15+ lakh", "≈90%"],
          [["Lost every period, every class", "Schools running on paper registers", "Cheaper than commercial systems"]],
          [5.8, 5.8, 5.8], size=9, zebra=False, aligns=["c", "c", "c"])

    spacer(doc, 6)
    callout(doc, "In one line",
            "a low-cost terminal that verifies a student by card and finger, marks a 30-student class in under two "
            "minutes, keeps recording when the internet drops, and tells parents the same period.")

    # ---------------- 2
    doc.add_page_break()
    heading(doc, 2, "Brainstormed possibilities", "Ten ideas, generated without judgement and then filtered on purpose")
    table(doc, ["Idea", "Verdict"],
          [["RFID card tap-in", "Selected — cheapest per tap, no student phone needed"],
           ["QR code attendance with rotating code", "Shortlisted — no hardware, but a code can be shared"],
           ["Teacher-confirmed digital register", "Shortlisted — good fallback, still costs teacher time"],
           ["NFC check-in with time window", "Merged into RFID — same physics, costlier cards"],
           ["Offline attendance with later sync", "Adopted as a core design rule"],
           ["Duplicate-entry and late-arrival flags", "Adopted — becomes Astro AI 2.0 logic"],
           ["Parent / student attendance summary", "Adopted as automatic email alert"],
           ["Face recognition", "Rejected — privacy, consent and camera cost"],
           ["Bluetooth proximity check-in", "Dropped — range too vague to prove presence"],
           ["Audit log for corrections", "Adopted — every manual edit is recorded"]],
          [10.4, 7.2], size=9.5)

    spacer(doc, 8)
    section_label(doc, "The three filters every idea had to pass")
    table(doc, ["Filter", "The question we asked"],
          [["Can five students build it?", "Do we have the skills and the lab time, this term?"],
           ["Can a school afford it?", "Roughly ₹2,450 per classroom, or it stays a slide?"],
           ["Does it respect the student?", "Does it collect less data than the register it replaces?"]],
          [6.0, 11.6], size=9.5)

    # ---------------- 3
    doc.add_page_break()
    heading(doc, 3, "Concept map", "One chain from the student at the door to a number the school can defend")
    table(doc, ["Stage", "What happens in our design"],
          [["USER / SETTING", "Student at the door; teacher and period fixed by the timetable"],
           ["PROBLEM TRIGGER", "Paper register — slow, proxy-prone, easy to lose"],
           ["SENSOR OR INPUT", "RC522 reads the card, R307 checks the finger"],
           ["PROCESS / DECISION", "ESP32 validates, de-duplicates, buffers offline"],
           ["OUTPUT / ACTION", "Firebase sync, dashboards, automatic parent email"],
           ["MEASURABLE BENEFIT", "15 minutes saved per class, zero proxy, ≈90% cheaper"]],
          [5.4, 12.2], size=9.5)

    spacer(doc, 8)
    callout(doc, "Proposed direction",
            "Astro Smart Attendance — two-factor · offline-first · AI self-healing · privacy by design",
            fill=NAVY_HEX)

    spacer(doc, 8)
    section_label(doc, "What each link has to prove before we call it true")
    table(doc, ["Link", "The proof we need"],
          [["User", "We solve a moment that repeats every period, not a textbook problem."],
           ["Trigger", "The pain is measured in minutes and errors, not in adjectives."],
           ["Input", "A tap is faster and fairer than a teacher reading out names."],
           ["Process", "The logic stays correct through power cuts, Wi-Fi loss and repeat taps."],
           ["Output", "The record reaches teacher and parent without extra work for either."],
           ["Benefit", "The gain shows up in a real classroom of 30, not in a simulation."]],
          [4.0, 13.6], size=9.5)

    spacer(doc, 8)
    section_label(doc, "What happens to one tap — the data pathway")
    para(doc, "Tap (card UID read)  →  Tag (student + period)  →  Check (duplicate? late?)  →  Store (local buffer)  "
              "→  Sync (Firebase write)  →  Alert (parent email)  →  Review (teacher confirms)", size=9.5)

    spacer(doc, 6)
    section_label(doc, "Who gains what")
    table(doc, ["Who", "What changes", "What we measure"],
          [["Teacher", "15 minutes returned per class", "≈ one extra teaching hour per week"],
           ["Student", "No queue, no roll-call, no proxy blame", "Attendance visible the same day"],
           ["Parent", "Absence message before the day ends", "Same-day action, not next-week surprise"],
           ["School office", "One trusted register, exportable", "Reports without re-entering data"]],
          [4.0, 7.4, 6.2], size=9.5)

    spacer(doc, 6)
    section_label(doc, "Unanswered questions we are carrying into validation", TEAL)
    for q in ["If a card is lost, what stops another student using it before the office reissues it?",
              "Two students tap within the same second — does the buffer keep both, in the right order?",
              "What exactly does the teacher see on the confirmation screen, and how is a mistake corrected?"]:
        para(doc, "?  " + q, size=9.5, space_after=3)

    spacer(doc, 4)
    callout(doc, "The rule we keep coming back to",
            "\u201cIf the internet dies, the register must still work.\u201d  A rule that decided the architecture: "
            "the buffer came before the cloud, not after it.")

    # ---------------- 4
    doc.add_page_break()
    heading(doc, 4, "Shortlisting matrix", "Scored 1 to 5 together in the lab — evidence first, opinions second")
    table(doc, ["Candidate concept", "Novelty", "Feasibility", "Affordability", "Impact", "Prototype potential", "Total", "Rank"],
          [["Astro Smart Attendance", "5", "5", "5", "5", "4", "24", "#1"],
           ["QR rotating code only", "4", "4", "5", "3", "4", "20", "#2"],
           ["Simpler digital register", "2", "5", "5", "3", "3", "18", "#3"],
           ["Sensor / app-only system", "3", "4", "3", "4", "3", "17", "#4"],
           ["Community / service model", "3", "4", "5", "3", "2", "17", "#4"],
           ["Face recognition terminal", "4", "3", "2", "4", "2", "15", "#6"]],
          [4.5, 1.9, 2.2, 2.4, 1.6, 2.5, 1.3, 1.2], size=9,
          aligns=["l", "c", "c", "c", "c", "c", "c", "c"])

    spacer(doc, 6)
    callout(doc, "Scoring note",
            "These are initial team hypotheses, not measured results. Each option was scored 1 (low) to 5 (high) in a "
            "team meeting, evidence from discovery dialogues was cited, and the shortlist was revised twice. Any score "
            "without cited evidence drops to a 3, and the matrix is re-scored after each validation step.")

    spacer(doc, 8)
    section_label(doc, "Evidence behind the scores")
    table(doc, ["Score", "The evidence"],
          [["Novelty 5", "No card-plus-fingerprint terminal with on-device self-healing exists in our price band; teachers had not seen one."],
           ["Feasibility 5", "The prototype already reads cards, writes to Firebase and survives a Wi-Fi cut in the lab."],
           ["Affordability 5", "The bill of materials works out to roughly ₹2,450 per unit, costed from real parts."],
           ["Impact 5", "Every teacher we spoke to placed attendance in their top two daily time losses."],
           ["Prototype 4", "The 3D-printed case and parent-email templates are still being refined."]],
          [3.6, 14.0], size=9.5)

    spacer(doc, 8)
    section_label(doc, "How the ranking moved once evidence arrived", TEAL)
    table(doc, ["Concept", "First → final", "What changed the score"],
          [["Astro Smart Attendance", "21 → 24", "Costed bill of materials landed near ₹2,450, under the ₹3,000 ceiling we set"],
           ["QR rotating code", "23 → 20", "A code shared on a group chat cannot be trusted for records"],
           ["Simpler digital register", "16 → 18", "Cheaper than expected, but still costs the teacher time"],
           ["Face recognition", "19 → 15", "Privacy and camera cost pulled it down after the product comparison"]],
          [4.6, 2.8, 10.2], size=9.5)

    # ---------------- 5
    doc.add_page_break()
    heading(doc, 5, "Selected concept and reason", "The idea we are building, and the honest case for why it deserves to win")
    callout(doc, "Selected concept",
            "Astro Smart Attendance — a privacy-first terminal built on ESP32 + RC522 reader + R307 fingerprint sensor "
            "+ LCD1602. The student taps a card and presses a finger; time, class, period and a pseudonymous ID are "
            "recorded in about three seconds, and both checks must agree before an entry is written. Astro AI 2.0 flags "
            "duplicates, late arrivals and proxy attempts, buffers offline and syncs to Firebase. Fingerprint templates "
            "stay inside the sensor. No face recognition. No phone required.", fill=NAVY_HEX)

    spacer(doc, 8)
    table(doc, ["Why this one", "The reason"],
          [["Answers the registered problem", "Saves 10–15 minutes every period, removes proxy entries and leaves a timestamped record."],
           ["Buildable by five students", "ESP32, RC522, R307, LCD and a printed case — a working prototype, not a slide."],
           ["Around 90% cheaper", "An estimated ₹2,450 per unit against ₹30,000+ for commercial kits — within reach of any school."],
           ["Measurable from day one", "Time per class, duplicate rejection, sync accuracy and teacher rating — all observable."]],
          [5.0, 12.6], size=9.5)

    spacer(doc, 6)
    section_label(doc, "How a student is verified — four steps, about three seconds, two independent checks")
    table(doc, ["Step", "What happens"],
          [["1  Tap card", "RFID card read at the door — who is claiming."],
           ["2  Press finger", "R307 matches the template — is it really them."],
           ["3  AI validates", "Both must agree; then period, duplicates and device health are checked."],
           ["4  Confirm + alert", "LCD confirms with a beep; Firebase syncs; the parent is emailed."]],
          [4.6, 13.0], size=9.5)

    spacer(doc, 6)
    section_label(doc, "System at a glance")
    table(doc, ["Part", "What it does"],
          [["Controller", "ESP32 DevKit V1 — Wi-Fi, OTA updates, offline logic"],
           ["Input", "RC522 13.56 MHz reader + R307 fingerprint + school card"],
           ["Feedback", "LCD1602 I2C display + buzzer"],
           ["Cloud", "Firebase Auth + Realtime Database + Hosting"],
           ["Intelligence", "Astro AI 2.0 — 11 self-healing diagnostic checks"],
           ["Enclosure", "3D-printed case, designed in Blender"]],
          [3.6, 14.0], size=9.5)

    spacer(doc, 6)
    section_label(doc, "What we deliberately left out — and why")
    table(doc, ["Left out", "Why"],
          [["Face recognition", "A camera on children costs more trust than the speed is worth. REJECTED"],
           ["Student phone app", "Not every student owns a phone. A card works for all. PARKED"],
           ["Full ERP replacement", "Fees, exams and report cards stay out of scope. OUT OF SCOPE"],
           ["Cloud-only design", "No network, no register. The buffer comes first. REPLACED"]],
          [4.6, 13.0], size=9.5)

    spacer(doc, 6)
    section_label(doc, "Who owns which part of the build")
    table(doc, ["Member", "Role", "Owns", "Deliverable"],
          [["Shaurya Gupta", "Team captain", "Firmware and cloud", "Card read, Firebase, AI health checks"],
           ["Anant Tiwari", "Ideation and research", "User interviews, requirement notes", "Discovery dialogues and comparison"],
           ["Tejas Upadhyay", "Hardware integration", "Reader wiring, power, enclosure fit", "Bench tests and fault finding"],
           ["Diwakar Singh", "Product design", "3D enclosure, mounting, finish", "Printable case for the door"],
           ["Devansh Dhakad", "Testing and docs", "Test log, stress runs, this worksheet", "Evidence for every claim"]],
          [3.5, 3.6, 5.2, 5.3], size=9.5)

    spacer(doc, 6)
    section_label(doc, "The first week, if the school gives us one classroom", TEAL)
    table(doc, ["Day", "Activity", "What we do"],
          [["Mon–Tue", "Bench test", "Read 30 cards, confirm every entry lands in Firebase."],
           ["Wed", "Enrol", "Card plus finger, with written parent consent; only a template is stored."],
           ["Thu–Fri", "Live period", "One real class marks attendance with the terminal beside the register."],
           ["Sat", "Compare", "Count the differences between our register and the teacher's."]],
          [2.6, 3.4, 11.6], size=9.5)

    # ---------------- 6
    doc.add_page_break()
    heading(doc, 6, "Initial system sketch",
            "Labelled block diagram: user, sensor, controller, output, power and the human confirmation step")
    para(doc, "STUDENT (ID card + enrolled finger)  →  RC522 READER (13.56 MHz card tap)  →  R307 SENSOR "
              "(fingerprint, 1:1 match)  →  ESP32 CONTROLLER (both factors must agree · buffers)  →  LCD1602 + BUZZER "
              "(\u201cPresent\u201d feedback)", size=9.5)
    para(doc, "                        ↓  Wi-Fi / HTTPS · offline → sync", size=9.5, space_after=3)
    para(doc, "FIREBASE CLOUD (Auth + Realtime DB)  →  DASHBOARDS (Admin · Student · Guardian)  →  "
              "PARENT EMAIL (automatic alert)", size=9.5)
    para(doc, "                        ↓  exceptions to review", size=9.5, space_after=3)
    para(doc, "HUMAN CONFIRMATION (teacher reviews exceptions · confirms · audit log)   |   POWER SOURCE "
              "(5 V USB adapter, full school day)   |   PRIVACY BY DESIGN (templates on-sensor · no images)", size=9.5)

    spacer(doc, 8)
    section_label(doc, "Bill of materials — what is in the box and its estimated cost")
    table(doc, ["Component", "Role in the system", "Est. cost"],
          [["ESP32 DevKit V1", "Controller, Wi-Fi, offline logic", "≈ ₹450"],
           ["RC522 RFID module", "First factor: reads each student card", "≈ ₹120"],
           ["R307 fingerprint sensor", "Second factor: proves the card holder is that student", "≈ ₹950"],
           ["LCD1602 I2C + buzzer", "Name, status and audible confirm", "≈ ₹180"],
           ["Wiring, LEDs, headers", "Assembly, level shifting, status lights", "≈ ₹120"],
           ["3D-printed enclosure", "Holds board, reader and sensor; mounts at the door", "≈ ₹280"],
           ["5 V adapter + cable", "Power for a full school day", "≈ ₹150"],
           ["30 RFID cards", "One card per student, issued by school", "≈ ₹200"],
           ["EST. TOTAL", "One classroom terminal, assembled and tested", "≈ ₹2,450"]],
          [5.2, 9.2, 3.2], size=9.5, aligns=["l", "l", "r"])

    spacer(doc, 6)
    section_label(doc, "What the LCD shows in each case")
    table(doc, ["Screen", "Shown text", "Meaning"],
          [["PRESENT", "Aarav S. · IX-B", "card recognised inside the period"],
           ["ALREADY MARKED", "Aarav S. · 08:12", "duplicate tap in the same period"],
           ["CARD NOT FOUND", "please see office", "unknown or unenrolled card"]],
          [3.8, 5.0, 8.8], size=9.5)

    spacer(doc, 6)
    section_label(doc, "The same idea against the two nearest alternatives")
    table(doc, ["Criterion", "Our concept", "QR code on a screen", "Digital register on a tablet"],
          [["Cost per classroom", "≈ ₹2,450", "₹0 hardware, ≈ ₹400 data", "₹12,000+ tablet"],
           ["Works without internet", "Yes — local buffer", "No, needs the app online", "Partly, if the app caches"],
           ["Proxy risk", "Very low — card + finger", "High — a screenshot travels", "Medium — a login can be shared"],
           ["Needs a student phone", "No", "Yes", "No"],
           ["Teacher effort", "Confirm exceptions only", "None until the report", "The whole period, typing"],
           ["Parent alert", "Automatic email", "Possible, if online", "Manual or not at all"]],
          [4.2, 4.4, 4.6, 4.4], size=9.5)

    # ---------------- 7
    doc.add_page_break()
    heading(doc, 7, "What the team must validate next", "Written before the results — each step has a decision rule, not just a task")
    table(doc, ["Validation step", "What we do", "Decision rule"],
          [["Interview 3–5 users and stakeholders", "Teachers, students, parents and office staff, recorded anonymously with consent.", "If fewer than 3 of 5 call attendance a top-two time loss, we revisit the problem."],
           ["Confirm the problem is frequent enough", "Check whether it recurs every period and in every class, not just on busy days.", "Below 3 occurrences per class per day, the hardware cannot be justified."],
           ["Compare two existing products", "A commercial biometric system and a phone-based app, judged on cost, privacy and offline use.", "If either matches on all three, we change direction."],
           ["Run a safe, low-cost proof of concept", "One reader, one class, one week — before any advanced feature is added.", "Any safety or privacy failure stops the trial immediately."],
           ["Collect baseline and prototype measurements", "Time 30 students by hand, then with the terminal, same conditions — invent nothing.", "If the terminal is not at least 5× faster, the design is not finished."],
           ["Test the fingerprint factor honestly", "Enrol 30 fingers, then try a borrowed card with the wrong finger, and a wet or bandaged finger.", "Any proxy that gets through drops the fingerprint stage to a 2 in the matrix."]],
          [4.6, 6.6, 6.4], size=9)

    spacer(doc, 10)
    heading(doc, 8, "Prototype success indicators", "How we will prove it works — measured numbers, not adjectives")
    table(doc, ["Indicator", "Target", "How it is measured"],
          [["Time for a class of 30 (simulated)", "< 90 sec", "30 simulated students doing card then finger, clocked with a stopwatch."],
           ["Duplicate scan rejection", "100%", "Same card twice in one period is refused, even with the right finger."],
           ["Late and invalid handling", "Correctly flagged", "Late arrivals flagged; unknown or wrong-period cards rejected."],
           ["Offline → online sync", "100% accurate", "Entries stored locally then synced when Wi-Fi returns, with no loss."],
           ["Teacher usability", "4+ out of 5", "Teachers rate setup, the confirmation step and dashboard clarity."],
           ["Proxy attempt rejected", "100%", "An enrolled card with a different finger must never write an entry."]],
          [5.4, 3.2, 9.0], size=9.5)

    spacer(doc, 6)
    section_label(doc, "Baseline against prototype", TEAL)
    table(doc, ["Measure", "Baseline (paper register)", "Target (prototype)"],
          [["Time for 30 students", "10–15 min, teacher-driven", "< 90 s"],
           ["Duplicate entries", "Common and unnoticed", "Rejected 100%"],
           ["Late-arrival record", "Written by hand", "Flagged with a timestamp"],
           ["Parent notification", "Same day if at all", "Within 5 minutes"],
           ["Records after a Wi-Fi cut", "Not applicable", "Buffered, then synced"],
           ["Evidence for an audit", "None", "Timestamped log per tap"]],
          [6.0, 6.0, 5.6], size=9.5)

    # ---------------- 8
    doc.add_page_break()
    heading(doc, 9, "Risks and design safeguards", "The safeguard is built into the design, not bolted on")
    table(doc, ["Risk", "Safeguard in the design"],
          [["Cards shared or swapped", "Two factors: the card says who is claiming, the finger proves it is them. No entry until both agree."],
           ["Finger fails in class", "A wet, dry or bandaged finger fails, so the LCD offers a teacher-override code that is logged and emailed to the parent."],
           ["Biometric data and consent", "The R307 keeps templates inside the sensor, not on the network. Written parent consent, deletion on request, no images leave the board."],
           ["Unknown or invalid card", "The LCD asks the student to see the office; no entry is written."],
           ["Network or power outage", "The buffer writes before the cloud call, so the register survives a dead network."],
           ["Privacy and data misuse", "No face recognition, no phone number of the child, minimal fields, teacher-confirmed corrections."],
           ["Hardware failure in class", "Astro AI 2.0 runs 11 checks at boot and between periods, so a fault is caught before the bell."],
           ["Cost creep during build", "The bill of materials is capped; any part above its estimate is reviewed before purchase."]],
          [5.2, 12.4], size=9.5)

    spacer(doc, 6)
    section_label(doc, "What would make us abandon this idea", SAFFRON)
    table(doc, ["Threshold", "The consequence"],
          [["Speed", "30 taps slower than two minutes — the terminal loses to a paper register."],
           ["Cost", "A unit above roughly ₹3,000 — it stops being a school solution."],
           ["Proxy", "Any proxy that beats the two factors — the extra sensor earns its place or it goes."],
           ["Privacy", "Templates we cannot store safely — no biometric data, no fingerprint stage."]],
          [3.6, 14.0], size=9.5)

    spacer(doc, 10)
    section_label(doc, "Team reflection", TEAL)
    table(doc, ["Prompt", "Our answer"],
          [["Which idea did we reject, and why?",
            "Face recognition. It scored 15 and finished last: the camera cost was five times our budget, and we could not promise to protect photographs of children. One finger template, kept on the sensor, gives the same protection at a fraction of the risk."],
           ["What did a user tell us that changed our thinking?",
            "A parent said they learn of an absence only at the end of the day. That moved the parent email from \u201cnice to have\u201d to a fixed requirement."],
           ["What is the smallest test that can prove or disprove our main assumption?",
            "One period, 30 students, card and finger. If it takes longer than two minutes, or a borrowed card beats it, the idea fails."]],
          [5.4, 12.2], size=9.5)

    spacer(doc, 8)
    callout(doc, "Handover",
            "The prototype is a working terminal, not a mock-up: it reads cards, matches fingers, writes to Firebase, survives a Wi-Fi "
            "cut and passes 140 of 140 feature tests. This worksheet records the decisions behind it and the evidence "
            "we still owe.")

    spacer(doc, 8)
    section_label(doc, "Before we submit — our checklist")
    table(doc, ["#", "Item", "Done"],
          [["1", "Discovery dialogues held and anonymised", "Yes"],
           ["2", "Fingerprint consent taken from parents", "Yes"],
           ["2", "Matrix scored together with evidence cited", "Yes"],
           ["3", "Block diagram drawn and labelled", "Yes"],
           ["4", "Bill of materials costed from real parts", "Yes"],
           ["5", "Indicators and decision rules written before results", "Yes"],
           ["6", "Risks and abandon criteria agreed by the whole team", "Yes"]],
          [1.2, 13.2, 3.2], size=9.5, aligns=["c", "l", "c"])

    spacer(doc, 12)
    table(doc, ["Shaurya Gupta", "Dr. Jayesh Shinde", "25 November 2026"],
          [["Team captain", "Mentor", "Date"]],
          [5.8, 5.8, 5.8], size=9.5, zebra=False, aligns=["c", "c", "c"])

    cp = doc.core_properties
    cp.title = "Part 1 — Creative Ideation Worksheet · Astro Smart Attendance"
    cp.author = "Team Sun Rises India, ABPS Renukoot"
    cp.subject = "ABG STEM Quest 2026-27 · SDG 9"
    cp.keywords = "creative ideation worksheet, SDG 9, RFID attendance, ESP32, Astro AI 2.0"
    cp.comments = ""

    doc.save(OUT)
    print("wrote", OUT, os.path.getsize(OUT))


if __name__ == "__main__":
    build()
