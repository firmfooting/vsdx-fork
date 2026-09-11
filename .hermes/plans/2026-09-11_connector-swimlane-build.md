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

### WI-4 — swimlanes / containers (P1)

- [ ] container membership cells (`msvSD*`) written correctly for member shapes
- [ ] `Page.add_swimlane(...)` — insert lane into a CFF document
- [ ] `Page.add_shape_to_lane(shape, lane)` — set membership cells
- [ ] fixture: s05_swimlanes_cfflow.vsdx used as base template for tests

Accept: open s05 fixture, add a shape to lane 2, add a lane; Visio opens the
result and shows the membership (manual COM check script provided).

### WI-5 — round-trip safety (P0)

- [ ] every WI above adds pytest cases using the com_reference fixtures
- [ ] Visio open-check harness (`tools/visio_check.ps1`) for local ground-truth validation

### WI-6 — master-import (P0, next)

Goal: `Connect.create()` (and any master-carrying shape copy) works on
documents that carry their own masters. Sub-steps:

- [ ] 6a ground truth: COM capture — take a doc with own masters
  (test3_house), paste a Dynamic-connector-master shape from a corpus file,
  save, and diff the zip (masters.xml, masters rels, content types, pasted
  shape's Master attribute, app.xml counts)
- [ ] 6b implement `VisioFile._ensure_master(shape) -> target_master_id`:
  no-op when the master name exists; else copy master part under the next
  free filename, append Master element with fresh unique ID, add masters.xml
  rels entry, content-type override, rewrite the copied shape's Master
  attribute, update app.xml
- [ ] 6c rewire `Connect.create()`: replace the three-branch provisioning
  mess with no-masters provisioning (existing path) + `_ensure_master`
- [ ] 6d tests: lift the strict-xfails (test3_house/test4 params must pass
  AND open in Visio); `_ensure_master` idempotency (import twice → one
  master); multi-connector regression still green
- [ ] 6e Visio ground-truth validation via tools/visio_check.ps1
- [ ] 6f upstream PR: master-import + dedupe helpers + state guard, anchored
  to upstream #93 (also closes the #77/#63 symptom class)

Accept: all xfails lifted, Visio opens every generated file, upstream PR cut
from the tested state.

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
