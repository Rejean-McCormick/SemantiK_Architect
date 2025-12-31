# Everything Matrix Orchestration

This document describes the **single-orchestrator** architecture for the Everything Matrix suite.

## Goal

`tools/everything_matrix/build_index.py` is the **only normal entrypoint** that refreshes the full matrix:

- **Zone A**: RGL inventory + grammar completion signals (from `rgl_inventory.json`)
- **Zone B**: Lexicon health
- **Zone C**: App readiness
- **Zone D**: QA readiness

All other scripts in `tools/everything_matrix/` remain available as **debug tools**, and must be:

- **side-effect free by default**
- **not duplicate work** during a normal matrix refresh

---

## Outputs

### Primary output

- `data/indices/everything_matrix.json`

### Prerequisite artifacts

- `data/indices/rgl_inventory.json` (Zone A source-of-truth input)

---

## Normalization rules

### Canonical language key

- The matrix is keyed by **ISO-639-1 `iso2`**, **lowercase** (example: `en`, `fr`, `sw`).

### No mixing of key types in orchestrator

- The orchestrator stores matrix entries under **iso2 only**
- Any wiki/iso3 keys are normalized at scanner boundaries (preferred) or by `norm.py`

### Source of truth for normalization

`tools/everything_matrix/norm.py` is the single shared module for:

- loading `config/iso_to_wiki.json`
- mapping `wiki` codes to canonical iso2
- mapping language display names

---

## Scanner contracts

Build Index uses scanners as libraries. The orchestrator calls each scanner **once per zone** (one-shot scan), then performs **dict lookups** per language.

### Zone A — RGL

**Library contract**
- `rgl_scanner.scan_rgl(...) -> inventory_dict`

**Normal behavior**
- `build_index.py` reads `data/indices/rgl_inventory.json`
- It does **not** rescan `gf-rgl/src` unless `--regen-rgl` or inventory missing

**Side effects**
- `rgl_scanner.scan_rgl(write_output=False)` must be side-effect free
- CLI can write with `--write` (debug only)

### Zone B — Lexicon

**Library contract**
- `lexicon_scanner.scan_all_lexicons(lex_root: Path) -> dict[iso2, zone_b_stats]`

**Expected keys**
- `{"SEED": float, "CONC": float, "WIDE": float, "SEM": float}`

**Scale**
- all values are `0..10` floats

### Zone C — App readiness

**Library contract**
- `app_scanner.scan_all_apps(repo_root: Path) -> dict[iso2, zone_c_stats]`

**Expected keys**
- `{"PROF": float, "ASST": float, "ROUT": float}`

**Scale**
- all values are `0..10` floats

### Zone D — QA readiness

**Library contract**
- `qa_scanner.scan_all_artifacts(gf_root: Path) -> dict[iso2, zone_d_stats]`

**Expected keys**
- `{"BIN": float, "TEST": float}`

**Scale**
- all values are `0..10` floats

---

## Orchestrator behavior

`tools/everything_matrix/build_index.py` performs:

1. **fingerprint/cache check**
2. ensures prerequisite inventories exist (optionally regenerates)
3. runs **one-shot scans** for each zone
4. synthesizes per-language verdict + maturity
5. writes `data/indices/everything_matrix.json`

### One-shot scan rule

During a normal refresh, build_index calls:

- `lexicon_scanner.scan_all_lexicons(...)` **once**
- `app_scanner.scan_all_apps(...)` **once**
- `qa_scanner.scan_all_artifacts(...)` **once**

Inside the per-language loop it does **only dict lookups**.

### No duplicate RGL scans

During a normal refresh, build_index:

- does **not** call `rgl_scanner.scan_rgl()` unless explicitly requested (`--regen-rgl`) or the inventory file is missing

---

## Scoring rules

### Scale

All zone values must be `0..10` floats.

### Back-compat shim

`build_index.py` may keep a helper to rescale legacy `0..1` values into `0..10`, but scanners should emit `0..10`.

### Zone averages

Per-language averages are computed as mean of each zone's sub-blocks:

- `A_RGL` average of `CAT, NOUN, PARA, GRAM, SYN`
- `B_LEX` average of `SEED, CONC, WIDE, SEM`
- `C_APP` average of `PROF, ASST, ROUT`
- `D_QA` average of `BIN, TEST`

### Maturity

Maturity is a weighted sum of the zone averages:

- weights are configurable (in `everything_matrix_config.json` under `matrix.zone_weights` or equivalent)
- output is clamped to `0..10`

### Strategy ladder

The orchestrator produces one of:

- `HIGH_ROAD`
- `SAFE_MODE`
- `SKIP`

(Exact thresholds are configured in the matrix config.)

---

## CLI usage

### Normal run

```bash
python tools/everything_matrix/build_index.py
