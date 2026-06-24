# Setup Notes — gnucleus-freecad-validator

Notes from a clean fork → clone → run pass on macOS, plus running sample
validation jobs against the published [`cad-gen-freecad`](https://huggingface.co/datasets/gnucleus-ai/cad-gen-freecad)
dataset. Captures the friction points worth smoothing for the next person.

- **Environment:** macOS (Darwin 25.5.0, arm64), Python 3.11
- **FreeCAD:** 1.1 (conda-forge build, module directly importable)
- **Repo:** fork of `gNucleus-AI/freecad-validator` @ `main` (commit `74f2f47`)

---

## What worked smoothly

- `from freecad_validator._freecad_loader import import_freecad` auto-detected
  FreeCAD with no `FREECAD_LIB` wrangling — the conda-forge build is directly
  importable, exactly as the README promises.
- The CLI (`validate`, `batch`, `join`, `render`) installed cleanly via the
  package entry-point and all subcommands resolved.
- End-to-end scoring is fast and deterministic. Re-runs produced identical
  scores.

---

## Friction points

### 1. No Docker environment is provided
The task brief assumes a "Build Docker environment" step, but the repo ships
**no `Dockerfile`, `docker-compose.yml`, or `.devcontainer`**. FreeCAD is a
heavy, platform-specific native dependency (LGPL, not pip-installable as a
wheel), so a reference container would remove the single biggest setup
variable. Today every user has to install FreeCAD by hand per-platform.

> **Impact:** medium. Native FreeCAD install is the hardest part of setup; a
> published image (e.g. `FROM continuumio/miniconda3` + `conda install -c
> conda-forge freecad`) would make "clone and run" reproducible.

### 2. No documented path from the published dataset → a runnable job
This is the biggest gap. The README's "Inputs" section describes three inputs
(`candidate.FCStd`, `reference.FCStd`, `spec.json` with `name` / `description`
/ `key_parameters`), and the HuggingFace dataset publishes *exactly* those
fields — but there is **no documented recipe or helper** to go from the
dataset to the batch `sample-data/data/<case>/` layout the validator expects.

I had to write glue myself:
- read `data/dataset.parquet` (columns: `id`, `name`, `description`,
  `key_parameters`, `image`, `fcstd_path`, `viewer_url`),
- download each `fcstd/<id>.FCStd` asset,
- emit `spec.json = {name, description, key_parameters}` per row,
- lay them out as `sample-data/data/<id>/{candidate,reference}.FCStd + spec.json`.

The `key_parameters` column is a markdown-bullet string (e.g.
`- outer_diameter = 107.156mm`), which the rule-based spec parser *does*
accept — but a one-paragraph "running against cad-gen-freecad" section (or a
tiny `scripts/fetch_dataset.py`) would save every evaluator from
rediscovering this.

> **Impact:** high for anyone trying to reproduce benchmark numbers.

### 3. README undercounts the CLI subcommands
The Usage section states `--help` shows `validate`, `batch`, and `join` — but
the CLI actually exposes **four**: `validate`, `batch`, `join`, **`render`**.
The `render` subcommand was added (it rasterizes a `.FCStd` to PNG via the
`[render]` extra) but the prose wasn't updated. Small, but it's the kind of
drift that erodes trust in the docs.

> **Fixed in the accompanying PR.**

### 4. (Environmental) Python `urllib` SSL failure on macOS
Downloading dataset assets with Python's `urllib.request` failed with
`CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`. This is
the well-known macOS python.org-installer cert issue, not a repo bug —
`curl`/`huggingface_hub` work fine. Noted only so the next person reaches for
`curl` or `huggingface_hub` instead of burning time on it.

---

## Sample validation jobs (evidence)

Built a 6-case `sample-data` dir from diverse dataset families (round mounting
flange, spur gear, hex nut, smooth shaft, lego brick, cone frustum). Each case
uses the dataset's ground-truth FCStd as **both** candidate and reference (a
self-consistency sanity run) with its spec derived from the row.

```
$ freecad-validator batch --sample-data-dir ~/cad-data/sample
validating 6 case(s) under ~/cad-data/sample/data
[  1/6] 0603c53148  geom=1.000  spec=1.000  combined=1.000   # round mounting flange
[  2/6] 08d2da3057  geom=1.000  spec=0.529  combined=0.692   # spur gear
[  3/6] 5c60c7a001  geom=1.000  spec=1.000  combined=1.000   # hex nut
[  4/6] 893b9137ff  geom=1.000  spec=1.000  combined=1.000   # smooth shaft
[  5/6] aad4a0fbad  geom=1.000  spec=0.600  combined=0.750   # lego brick
[  6/6] f3e10795e7  geom=1.000  spec=1.000  combined=1.000   # cone frustum

validated: 6/6  errors: 0
geometry_similarity : mean=1.000  median=1.000  min=1.000  max=1.000
cad_spec_consistency: mean=0.855  median=1.000  min=0.529  max=1.000
combined            : mean=0.907  median=1.000  min=0.692  max=1.000
```

Observations:
- **Geometry self-match = 1.000 across all 6** — expected, validates the
  geometry pass end-to-end.
- **Spec consistency surfaces real signal** even on ground-truth models: the
  spur gear scored 0.529 (9/17 consistent, 4 inconsistent, 4 not_found),
  meaning several published `key_parameters` aren't recoverable from the
  FCStd geometry by the current heuristics — a useful finding in itself.

**Discrimination check** — cross-pairing a gear *candidate* against a flange
*reference* correctly collapses geometry to 0:

```
$ freecad-validator validate gear/candidate.FCStd flange/reference.FCStd gear/spec.json
geometry_similarity  : 0.000000
geometry_similarity_reason : face count differs by 96% (candidate=185, reference=8;
                             threshold 50%) — candidate likely represents a
                             structurally different part; gated geometry to 0.0
```

So the scorer isn't trivially returning 1.0 — it gates structurally different
parts to zero.

---

## Suggested follow-ups (beyond this PR)

1. Add a `Dockerfile` (conda-forge FreeCAD base) for reproducible setup.
2. Add a `scripts/fetch_dataset.py` + a README "Running against cad-gen-freecad"
   section documenting the parquet → `sample-data` mapping.
3. The accompanying PR fixes the subcommand miscount (#3 above).
