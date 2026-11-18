# ABG STEM Quest 2026–27 · Part 1 — Creative Ideation Worksheet

**Team Sun Rises India · Astro Smart Attendance v26.7.13**

📄 **Deliverable:** [`Astro_Smart_Attendance_Creative_Ideation_Worksheet.pdf`](./Astro_Smart_Attendance_Creative_Ideation_Worksheet.pdf) — 17 A4 pages, print-ready.

| Page | Content |
|---|---|
| 01 | Cover |
| 02 | Project at a glance · team · contents · built-with |
| 03–04 | **Section 1** Problem Focus — story, roll-call cost, paper trail, discovery questions, 3 interviews |
| 05 | **Section 2** Brainstormed Possibilities — 12 idea cards + "the pattern we noticed" |
| 06 | **Section 3** Concept Map — 6-stage chain → direction selected |
| 07 | **Section 4** Shortlisting Matrix — heat-map, criteria, 25/25 justification |
| 08–10 | **Section 5** Selected Concept & Reason — 6-step flow, offline-first, Astro AI 2.0, enclosure, 5 reasons |
| 11 | **Section 6** Initial System Sketch — redrawn block diagram |
| 12 | **Section 7** Validation — table, roadmap, write-in sheets for interviews 4 & 5 |
| 13 | **Section 8** Prototype Success Indicators — honest status (lab / verified / pilot) |
| 14 | **Section 9** Risks & Design Safeguards |
| 15–16 | **Team Reflection** — eliminated ideas, stakeholder insight, minimum experiment, pilot log, declaration |
| 17 | Back cover |

## Rebuild

```bash
cd worksheet
npm install
node build.mjs            # → PDF
node build.mjs --preview  # → also PNG previews in .preview/
```

The source is `src/index.html` + `src/styles.css`. Icons are Lucide (inlined at build), fonts are Space Grotesk, Inter, Instrument Serif and JetBrains Mono (via Fontsource). The build script checks every A4 page for overflowing content.

## Editorial notes (changes made to the original text)

The team's wording is kept almost word-for-word. A few phrases were tightened so judges can't catch the worksheet contradicting itself or over-claiming:

1. **Price consistency.** "Device cost confirmed at Rs. 1,500 per unit" → "Rs. 1,500 per RFID unit · Rs. 2,412 with fingerprint". The chosen concept is the dual-biometric one, and Section 4 already lists ₹2,412 for it.
2. **Stress tests are labelled "simulated"** everywhere ("10 million *simulated* stress-test cycles"). Section 7 already says this. Keeping it the same everywhere stops anyone reading it as 10 million real scans.
3. **Idea 09 worry:** "NoSQL alone cannot do this" → "hard to do well with NoSQL alone". The original claim isn't technically true.
4. **Fingerprint privacy safeguard:** "only a 256-byte template … reconstruction is mathematically impossible" → "only a compact numerical template is ever stored … the template is a set of numbers, not a picture". R307 templates are larger than 256 bytes (the 256-byte figure is one character buffer). Also, "mathematically impossible" is a claim that biometrics experts often challenge.
5. **Interview quotes** appear as *"What we heard"*, not inside quotation marks, because the original notes are reported speech.

### Design additions (not in the original text; remove freely)

- p04 stat boxes "Up to 8×", "1+ hr", "6 rooms" (taken from the interview notes).
- p10 pull-quote "Designed for Renukoot first…"; p15 one-line "Lesson:" boxes under each dropped idea.
- p12 write-in sheets for interviews 4 & 5; p16 hand-fill pilot log table.
- p12 sub-line "after the pilot, every number is measured, never estimated" (replaces a separate "Our principle" card).

## Image credits

All photographs and renders in `assets/img/` are **AI-generated concept visuals**, and each one is labelled that way in the PDF. They are not photos of the real prototype. You can swap in real prototype photos with the same filenames, then rebuild.
