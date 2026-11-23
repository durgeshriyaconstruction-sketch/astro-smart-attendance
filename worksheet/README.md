# ABG STEM Quest 2026–27 · Part 1 — Creative Ideation Worksheet

**AttendSure · Privacy-First Attendance**
Team Sun Rises India · Grade 9 · The Aditya Birla Public School, Renukoot

📄 **Deliverable:** [`AttendSure_Creative_Ideation_Worksheet.pdf`](./AttendSure_Creative_Ideation_Worksheet.pdf) — 10 A4 pages, print-ready.

> **Edition:** this is the *completed example* edition. Sections 1, 2, 4, 6, 8 and 9 are
> pre-filled with the team's suggested answers and targets, clearly badged on §1.
> Anything that must come from real measurements or interviews is left as a target or
> a blank cell — replace it with your own values before the pilot.

| Page | Content |
|---|---|
| 01 | Cover — event, team, theme (SDG 9), selected direction |
| 02 | **Section 1** Problem focus — statement, discovery question, who/when/current/evidence write-in |
| 03 | **Section 2** Brainstormed possibilities — 10 idea cards + “the pattern we noticed” |
| 04 | **Section 3** Concept map — six-stage chain → proposed direction |
| 05 | **Section 4** Shortlisting matrix — heat-map + scoring note + blank team-score row |
| 06 | **Section 5** Selected concept & reason — description, six feature cards, rationale |
| 07 | **Section 6** Initial system sketch — labelled block-diagram template + filled write-in table (all five blocks, power and offline store) |
| 08 | **Section 7** What the team must validate next — five checks + interview log (five stakeholders pre-listed; “what we heard” and consent left blank to fill in) |
| 09 | **Section 8** Prototype success indicators + **Section 9** Risks & design safeguards |
| 10 | Team reflection — three write-in prompts + declaration |

## Rebuild

```bash
cd worksheet
npm install
node build.mjs            # → PDF
node build.mjs --preview  # → also PNG previews in .preview/
```

The source is `src/index.html` + `src/styles.css`. Icons are Lucide (inlined at build);
fonts are Space Grotesk, Inter, Instrument Serif and JetBrains Mono (via Fontsource).
The build script lays the sheet out in headless Chromium and checks every A4 page for
overflowing or clipped content before writing the PDF.

## Where the content comes from

The worksheet follows the team’s Part 1 creative-ideation brief section by section,
keeping its wording:

- §1 problem statement and the four-part discovery question
- §2 the ten brainstormed possibilities
- §3 the six-stage concept map (user/setting → trigger → sensor/input → process/decision → output/action → measurable benefit)
- §4 the shortlisting matrix (four candidates, same five criteria) and its scoring note
- §5 the selected concept and its rationale
- §6 the system-sketch brief (user, input/sensor, controller/process, output/alert, power source, human confirmation step)
- §7 the five validation tasks
- §8 the five prototype success indicators
- §9 the risks, the safeguards, and the three team-reflection questions

### Design additions (not in the original text; remove freely)

- §1 write-in grid for *who / when / what they do now / evidence*, taken straight from the discovery question.
- §2 a “pattern we noticed” band and per-idea icons.
- §3 stage answers filled in from the selected concept, labelled as the team’s proposal.
- §4 a blank “Team score (1–5)” row so the meeting scores can be written in.
- §5 six feature cards (rotating QR, short window, pseudonymous ID, teacher confirms, offline mode, no face recognition).
- §6 a labelled block-diagram template plus a write-in table.
- §7 a five-row interview log (role, what we heard, consent).
- §9 risk → safeguard rows derived from the brief’s own sentence.

There are no photographs in this edition — the visuals are vector/CSS only, so there are
no image credits to track and nothing to swap out later.

## Files

| Path | What it is |
|---|---|
| `AttendSure_Creative_Ideation_Worksheet.pdf` | generated deliverable |
| `src/index.html` | the worksheet source |
| `src/styles.css` | design system (shared with the earlier Astro worksheet) |
| `build.mjs` | HTML → inline icons → headless Chromium → PDF, with a layout guard |
| `package.json` / `package-lock.json` | build dependencies |
