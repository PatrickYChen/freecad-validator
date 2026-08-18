# Session Handoff — CAD Bench contributions (Area 3: leaderboard run analysis)
_2026-07-22_

## Project
Patrick is contributing to the Parametric CAD Bench (cadbench.ai, gNucleus-AI org). Three contribution areas from a 2026-07-14 meeting with Mei Chen (yicong2005@gmail.com): (1) freecad-validator improvements, (2) leaderboard agent+model entries, (3) analysis of published leaderboard runs. This session completed **Area 3** end-to-end.

## What We Did
- Mapped the ecosystem: scorer = `gNucleus-AI/freecad-validator` (this repo is Patrick's fork, PRs #9/#10 already merged), submissions = `gNucleus-AI/cad-bench-submission` (harbor run → HF dataset → manifest YAML PR), data = HF `gnucleus-ai/cad-gen-freecad` (100 task specs) + `gnucleus-ai/cad-gen-freecad-bench` (1,000-row results parquet + full per-trial artifacts under `runs/<agent>/<model>/<task>/`)
- Analyzed all 1,000 trials (10 combos × 100 tasks, bench run 2026-05-13); sampled generated `answer.py` artifacts for the spur-gear task `freecad-08d2da3057` across 4 combos
- Built an interactive HTML report (5 SVG charts, leaderboard table) and published as artifact: **https://claude.ai/code/artifact/957613b4-3cbf-4467-8501-c64a906d55f9**
- Rendered the report to PDF via headless Chrome → **`~/cad-bench-analysis.pdf`** (8 pages, verified visually, one scatter-label collision fixed)
- Tooling: Claude Code 2.1.218 + Opus 4.8 (1M) — Patrick wants this credited in his email to Mei

## Key Findings (the deliverable's content)
1. Outcomes are bimodal: 279/1000 trials at exactly 1.0, 166 at exactly 0
2. 36/100 tasks are "toothed" (gear/spline/bearing/brake) and decide the ranking; top-5 combos near-tied on the other 64
3. gemini-cli+gemini-pro alone has no gear penalty — it uses FreeCAD's built-in `InvoluteGearFeature`; others hand-roll involute math (verified on 1 task only — flagged as a caveat)
4. Sonnet's #7 rank is a harness artifact: plain-part score 0.7136 ≈ Opus's 0.7138; deficit = 22 exceptions/21 near-timeout runs, 16 on gears
5. 166 zeros decompose: 63 no-.FCStd-saved (gemini-cli signature), 99 structurally-gated (mini-swe signature), 4 exception-after-save; plus 102 trials spec=1.0 but geom<0.3 (47 hex nuts)
6. 16× spread in pts/$; mini-swe+opus-4-7 = value sweet spot (88% of top score, 18% of cost)
7. mini-swe uses 54–56k median input tokens vs 259–693k for vendor CLIs; codex shows adaptive effort (r=−0.49 runtime↔score)

## Important Decisions
- **Recommended Area 1 next**: `scripts/fetch_dataset.py` + Dockerfile PRs (glue code already exists from SETUP_NOTES.md work); Patrick hasn't picked a track for follow-up yet
- **Toothed definition**: task name contains gear/spline/bearing/brake → 36 tasks (documented in report footer)
- **Zero-cause categories** mutually exclusive, priority: missing artifact → exception → structural gate

## Files and Components
- `~/cad-bench-analysis.pdf` — final PDF deliverable (persists)
- Artifact URL above — same report, interactive; updating it from a new session requires passing `url:` to the Artifact tool
- **Scratchpad (EPHEMERAL — gone next session)**: `explore.py`, `explore2.py`, `chartdata.json`, `cad-bench-analysis.html`, venv, both parquets. To reproduce: re-download parquets from the two HF datasets (curl -L the `resolve/main/...` URLs), `python3 -m venv` + pandas/pyarrow (system Python 3.11, **no uv/conda/node on PATH**; Chrome at `/Applications/Google Chrome.app`)
- `SETUP_NOTES.md` (this repo) — Patrick's earlier fork→run friction notes; contains the Area 1 roadmap

## Current State
- **Working**: Area 3 complete — report published + PDF delivered; all numbers verified against the parquet
- **Partial**: Finding 3 (InvoluteGearFeature) verified on one task; a sweep of all 31 gear tasks' `answer.py` would harden it. Trajectory-level analysis (`trajectory.json` mining for save/verify rhythm, turn counts) proposed but not done
- **TODO / open**: Patrick to email Mei (PDF + credit line ready). Next tracks: Area 1 PRs (fetch_dataset.py, Dockerfile, spec-scorer recoverability) or trajectory deep-dive or a cadbench news-post writeup
- `gh` CLI is **not authenticated** — needed before opening PRs (`gh auth login`)
- One oddity: first artifact republish hit a 409 "newer version from another session"; diff showed identical content, resolved by re-read + republish
