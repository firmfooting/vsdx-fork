# Plan: vsdx connector + swimlane feature build

**Repo:** fork `shauneccles/vsdx` of `dave-howard/vsdx` (upstream master `6703e6c`, v0.6.1)
**Date:** 2026-09-11
**Status:** in progress
**Ground truth:** `tests/fixtures/com_reference/` — 6 scenario .vsdx files + `manifest.json`, generated from live Visio 16.0 via `tools/com_reference.ps1`

## Objective

Take the connector and container story from "copy a template shape and hope" to a
fully featured, Visio-faithful implementation: dynamic connectors with real glue
semantics, route-style control, and swimlane/container support. Everything is
written against the COM ground-truth corpus, not guesswork.

## Ground-truth facts (from manifest.json, Visio 16.0)

A real dynamic connector between two shapes carries:

- `BeginX/BeginY = _WALKGLUE(BegTrigger,EndTrigger,WalkPreference)` and the EndX/EndY mirror
- `BegTrigger = _XFTRIGGER(<from-sheet-id>!EventXFMod)`, `EndTrigger = _XFTRIGGER(<to-sheet-id>!EventXFMod)`
- `GlueType = 2` (dynamic/static mix), `ObjType = 2`
- Route styles: `ShapeRouteStyle = 1` right-angle, `16` straight, `17` + `ConLineRouteExt = 2` curved
- `ConFixedCode = 6` default; point-glue scenarios show literal mm coordinates in Begin/End instead of _WALKGLUE
- Connection-point glue cells are named `Connections.X1` (not `ConnectionXY1`)
- Swimlanes: `msvSDContainerStyle`, `msvSDListDirection`, `msvSDListItemMaster`,
  `msvSDContainerLocked` user cells; masters `CFF Container`, `Swimlane List`,
  `Swimlane`, `Phase List`, `Separator` from `XFUNC_M.vssx`

## Work items

### WI-1 — Connector engine rewrite (P0) ✅ done (commit 1a564ee, Visio-verified)

Replace the string-replace trigger construction in `Connect.create()` with
formula-exact connector construction:

- [x] `_WALKGLUE` on BeginX/BeginY/EndX/EndY
- [x] `_XFTRIGGER(Sheet.N!EventXFMod)` triggers referencing real from/to shape IDs
- [x] `GlueType=2`, `ObjType=2` + explicit dynamic route cells (ShapeRouteStyle=0)
- [x] route_style parameter: 0 default, 1 right-angle, 16 straight, 17+ext=2 curved (`route='straight'|'rightangle'|'curved'`)
- [x] connection-point glue via `Connections.Xn` cell references (`route='point'`, ToPart=100+n, ValueError when CPs missing)
- [x] remove debug print() from production paths (library-wide logging tracked in #2)
- [ ] connector re-anchor helper: retarget an existing connector's from/to

Accept: generated file opens in Visio and shows a routed dynamic connector. **Met:**
`tools/visio_check.ps1` on engine output reports `PASS connectors=5 walkglue=3`.

### WI-2 — shape deletion cascade (P0) ✅ done (commit 1a564ee)

- [x] deleting a shape removes its incident connectors and their Connect records (`Page.delete_shape`)

Accept: delete_shape on a connected shape leaves a valid, openable file. **Met**
(test_delete_shape_cascades_connectors + zip validity check).

### WI-0 — bugs discovered during the build (raised as issues)

- [x] #1 master-import gap: create() on documents with own masters but no
  connector master → FileNotFoundError (test3_house param strict-xfail)
- [x] #2 debug print() pollution library-wide
- [x] Media.curved_connector returned straight connector — fixed with
  regression test (commit 5ad1b48)

### WI-3 — shape creation from a richer template palette (P1)

- [ ] media template gains decision/start-end/database shapes (drawn once via COM, then shipped as fixture)
- [ ] `VisioFile.create_shape(page, master_text, x, y, w, h, text)` public API
- [ ] `Page.add_shape` remains as alias for compat

Accept: `create_shape('Decision', ...)` produces a real decision diamond.

### WI-4 — swimlanes / containers (P1, in progress)

Ground truth source: `tests/fixtures/com_reference/s05_swimlanes_cfflow.vsdx`
(real Visio CFF capture). No cell name may be written from plausibility.

- [ ] 4a inspect s05: dump User cells + geometry for CFF Container, Swimlane
  List, Swimlane lanes, Phase List, Separator, and Processes inside vs outside
  lanes; identify the exact membership representation
- [ ] 4b DRY prerequisites (separate commit): lift `Connect._get_or_create_cell`
  to `Shape.get_or_create_cell` (single cell-write primitive); shared
  `tests/conftest.py` fixture-copy helper (stop per-module `get_copy` copies)
- [ ] 4c `vsdx/containers.py`: `Container` wrapper (discovery, members,
  add_member); `Page.add_swimlane(label)` (clone last lane, shift geometry per
  `msvSDListDirection`); `Page.add_shape_to_lane(shape, lane)`. Page methods
  are thin facades, matching the connect_shapes→Connect.create pattern
- [ ] 4d tests: membership cells present, lane clone geometry, label set,
  package validity; cross-document lane creation reuses master-import
- [ ] 4e Visio validation: extend `tools/visio_check.ps1` with container
  membership reporting (no second harness)

DRY rules for this work item:
1. one cell-write primitive (`Shape.get_or_create_cell`) — no second
   cell-creation path
2. one membership-semantics implementation (`containers.py`); Page methods
   delegate
3. any cross-document shape/master movement flows through
   `_ensure_masters_for_shape` — zero new package-wiring code
4. shared test fixture helper in `conftest.py`
5. extend the existing Visio harness; never a parallel one

Accept: open s05 fixture, add a shape to lane 2, add a lane; Visio opens the
result and shows the membership (manual COM check script provided).

### WI-5 — round-trip safety (P0)

- [ ] every WI above adds pytest cases using the com_reference fixtures
- [ ] Visio open-check harness (`tools/visio_check.ps1`) for local ground-truth validation

### WI-6 — master-import (P0) ✅ done (branch feat/master-import, upstream PR #96)

Goal: `Connect.create()` (and any master-carrying shape copy) works on
documents that carry their own masters. Sub-steps:

- [x] 6a ground truth: COM paste capture — masters.xml carries logical Master
  IDs (NameU + BaseID preserved), masters.xml.rels maps rel→part, content
  types declare both, PAGE rels carry a per-page master relationship, app.xml
  carries nothing
- [x] 6b `VisioFile._ensure_masters_for_shape(source_shape)` — imports by
  NAME (MatchByName; numeric IDs are per-document — the numeric-ID match bug
  was caught by tests mid-build), `_bootstrap_masters()` for masters-less docs
- [x] 6c `Connect.create()` rewired: bootstrap or source-then-copy import;
  dedupe guards on document rels + content types; app.xml Masters count
  dropped (Visio omits it); page rels now registered so save persists them
- [x] 6d tests: strict-xfail lifted (test3_house param passes); idempotency
  and single-master-import regression tests; 352 passed / 342 on upstream base
- [x] 6e Visio ground-truth validation: test3_house + test8 both PASS with
  the imported connector carrying _WALKGLUE
- [x] 6f upstream PR #96 opened (master-import + dedupe + state guard,
  scoped without the formula engine); curved-connector one-liner is PR #95

Accept: all xfails lifted, Visio opens every generated file, upstream PRs
cut from the tested state. **Met.**

## Upstream posture (decided 2026-09-11)

Fork-forward for capability; staged small PRs for universal bugs.
- Issues filed upstream: #93 (corruption/duplicate masters), #94 (curved_connector).
- PR #95 open upstream: curved-connector one-liner (probe for maintainer responsiveness).
- Corruption fix PR waits on WI-6 (see above).
- Full recon: `.hermes/recon/upstream-connector-notes.md`.

## Conventions

- Branch per work item off `main` (named `feat/<wi>-<slug>`), single-concern commits
- Tests must pass with NO Visio installed (pure python); COM checks are local-only extras
- Commit only coherent state; push to origin (shauneccles/vsdx) when a WI is green
- Do not modify upstream tags; keep fork master == upstream master + release wiring

## Delegation

- COM corpus work is DONE (this plan's ground truth section)
- Implementation proceeds WI-1 → WI-2 → WI-3 → WI-4 with a review pass per WI
