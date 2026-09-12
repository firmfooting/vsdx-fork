# Changelog

This changelog covers the `vsdxkit` fork. The upstream project history remains
available at <https://github.com/dave-howard/vsdx>.

## Unreleased

### Added

- Package expansion limits: `VisioFile` inspects archive metadata before reading
  members and enforces caps on member count, per-member and total uncompressed
  size and compression ratio, and rejects duplicate and path-unsafe member names,
  raising `vsdx.PackageLimitError` with a stable `reason`. Defaults suit
  untrusted documents; trusted callers relax them via `limits=` or `limits_path=`.
- Renovate keeps the digest-pinned GitHub Actions and Python dependencies
  current, with grouped weekly update PRs and a uv lock maintenance pass.
- The CI build job now smoke-tests the built wheel in a clean virtual
  environment (install, import, `pip show`, `py.typed` presence) before the
  distribution is uploaded as an artifact.
- CI cancels superseded runs on the same ref via a concurrency group.
- Pyrefly runs at the `strict` preset with zero diagnostics at warning severity
  and no in-source type suppression comments.
- Typed contracts for shapes, pages, connectors, geometry, containers,
  templating, media and XML/package persistence.
- Shared required-XML helpers that report the missing package part rather than
  failing later on a `None` value.
- Regression coverage for in-place and named save destinations.
- Current README and Sphinx guides for shape creation, connectors,
  re-anchoring, swimlanes, search and Jinja templates.
- Sphinx warning-as-error validation and a dedicated zizmor GitHub Actions audit
  in the CI gates.
- Malformed numeric ShapeSheet values raise `ValueError` naming the cell and raw
  value instead of silently reading as `0.0`; absent cells still read as `None`,
  keeping absent, malformed and genuine zero distinct.
- Package-wide import coverage now runs as a normal test across the supported
  Python and operating-system matrix.

### Fixed

- Connector record removal normalises integer IDs before matching XML attributes,
  preserving the existing public-call behaviour.
- Shape and connector coordinate setters reject `None` instead of writing
  invalid `V="None"` ShapeSheet values.
- `save_vsdx()` now writes through a same-directory temporary archive and
  atomically replaces the target; failed in-place writes retain the original.
- Repeated in-place or named saves preserve untouched ZIP members and keep
  archive member paths relative.
- Combined routes such as `point|curved` retain connection-point glue while
  applying the requested line style.
- `apply_text_context()` again coerces non-string values before replacement.
- The legacy debug-handler bridge imports and runs on Python 3.10.
- `Shape.copy()` retains a valid Page or Shape parent rather than assigning an
  internal shape list as the parent.
- XML master-part types now match the package representation used at runtime.
- Missing `IX` values and list/dictionary confusion in geometry handling no
  longer flow into unguarded operations.
- Page-template matching handles absent names and non-matching Jinja markers.
- Connector re-anchoring handles missing endpoint IDs explicitly and avoids
  parameter shadowing.
- Media documents can be closed and opened again through one lazy access path.
- Page relationship parts use OPC separators on every operating system and are
  copied into the in-memory package when a page is copied.
- Bundled media paths no longer depend on the process working directory.
- Closing an in-memory document no longer deletes an unrelated same-stem
  directory beside the source file.
- Saving rejects an empty package instead of writing a corrupt archive and
  recognises an uppercase `.VSDX` suffix without appending another extension.

### Changed

- The lint job checks and formats the whole `tests` tree rather than two
  selected test modules; the remaining test files have been brought into
  compliance (semantic fixes: `raise AssertionError` instead of `assert
  False`, `zip(..., strict=True)`, `enumerate()` accumulation, exception
  chaining).
- zizmor is pinned to the committed uv lock (`uv run zizmor`) instead of
  resolving ad hoc via `uvx` at run time.
- Package keywords no longer carry inherited upstream terms.
- CONTRIBUTING.md and SECURITY.md now describe this fork (uv workflow,
  gate list, private vulnerability reporting on this repository) rather than
  inheriting the upstream project's text.
- CI now uses a committed uv lock for normal test, lint and build jobs. The
  minimum-dependency job regenerates that lock with
  `--resolution lowest-direct` and runs the full test suite on the oldest and
  newest supported Python versions.
- Test and development tooling now use uv dependency groups instead of a
  published `dev` extra.
- The pyrefly preset is now `strict` rather than `basic`.
- Runtime dependency floors now match the supported API and security baseline:
  `Jinja2>=3.1.6`, `deprecation>=2.1.0`, and `typing-extensions>=4.4.0` on
  Python 3.10–3.11. Python 3.12 and later use `typing.override` directly.
- `insert_shape()` now validates that `page_path` identifies the supplied
  `Page` instead of silently allocating IDs against whichever page was visited
  last.
- GitHub's default branch is now `main`; CI and documentation references follow
  the renamed branch.
- Documentation now names the distribution `vsdxkit`, retains `import vsdx`,
  and requires Python 3.10 or later.

## 0.6.3

- Renamed the distribution to `vsdxkit` while preserving the `vsdx` import.
- Replaced legacy packaging with `pyproject.toml`.
- Added ruff, pyrefly and a Python 3.10–3.14 Linux/Windows CI matrix.
- Added connector creation, master import, connector re-anchoring, shape
  creation from the bundled palette and CFF swimlane operations.
- Split master import, templating and XML persistence out of `vsdxfile.py`.
- Replaced package `print()` diagnostics with standard-library logging.
