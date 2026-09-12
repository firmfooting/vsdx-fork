# vsdxkit

[![CI](https://github.com/shauneccles/vsdx/actions/workflows/ci.yml/badge.svg)](https://github.com/shauneccles/vsdx/actions/workflows/ci.yml)
[![Python 3.10–3.14](https://img.shields.io/badge/python-3.10%E2%80%933.14-blue.svg)](https://www.python.org/)
[![BSD-3-Clause](https://img.shields.io/badge/license-BSD--3--Clause-green.svg)](LICENSE)

Create, edit and analyse Microsoft Visio `.vsdx` files with Python. Visio is not required at runtime.

The distribution is named **`vsdxkit`**. The import remains **`vsdx`** for compatibility with the upstream library.

This fork extends [`dave-howard/vsdx`](https://github.com/dave-howard/vsdx) with shape creation, Visio-faithful connectors, connector re-anchoring, cross-functional flowchart swimlanes, stricter package handling, current Python tooling and typed public APIs.

## What it does

- Opens, queries and edits existing `.vsdx` files without Microsoft Visio.
- Finds shapes by ID, text, regular expression or Shape Data.
- Creates common flowchart shapes from a bundled palette.
- Creates dynamic or connection-point glue with straight, right-angle or curved routing.
- Re-anchors either end of an existing connector.
- Reads and extends Visio cross-functional flowchart swimlanes.
- Copies shapes and pages while rewriting package-local IDs and importing masters.
- Renders data into Visio templates with Jinja.
- Saves to a new file or safely replaces the source file in place.

The implementation edits the XML parts inside the Open Packaging Convention archive. It does not drive the Visio user interface. Generated connector and swimlane files are nevertheless checked against Microsoft Visio through COM as a release gate.

## Installation

`vsdxkit` is not yet published on PyPI. Install it from GitHub:

```bash
python -m pip install "vsdxkit @ git+https://github.com/shauneccles/vsdx.git"
```

For development:

```bash
git clone https://github.com/shauneccles/vsdx.git
cd vsdx
python -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev,docs]"
```

Python 3.10–3.14 is supported on Linux and Windows.

## Open, edit and save

Use the context manager to close the package cleanly. Saving is explicit.

```python
from vsdx import VisioFile

with VisioFile("diagram.vsdx") as vis:
    page = vis.pages[0]
    shape = page.find_shape_by_text("Shape to remove")

    if shape is not None:
        shape.text = "Renamed shape"

    vis.save_vsdx("edited.vsdx")
```

Call `save_vsdx()` without a filename to replace the source file in place:

```python
with VisioFile("diagram.vsdx") as vis:
    vis.pages[0].name = "Current state"
    vis.save_vsdx()
```

## Create shapes and connectors

Shape coordinates are in Visio page units, normally inches. `x` and `y` identify the shape centre.

```python
from vsdx import VisioFile

with VisioFile("diagram.vsdx") as vis:
    page = vis.pages[0]

    start = vis.create_shape(
        page, "PALETTE_START_END", 2.0, 6.0, text="Start"
    )
    work = vis.create_shape(
        page, "PALETTE_PROCESS", 6.0, 6.0, text="Do the thing"
    )
    decision = vis.create_shape(
        page, "PALETTE_DECISION", 10.0, 6.0, text="OK?"
    )

    page.connect_shapes(start, work)
    page.connect_shapes(work, decision, route="rightangle")
    vis.save_vsdx("flow.vsdx")
```

Bundled palette names are:

- `PALETTE_PROCESS`
- `PALETTE_DECISION`
- `PALETTE_START_END`
- `PALETTE_PARALLELOGRAM`
- `PALETTE_DATABASE`

Connector `route` combines glue and routing behaviour:

| Value | Meaning |
|---|---|
| `dynamic` | Dynamic shape glue. This is the default. |
| `point` | Glue to zero-based connection points selected with `from_cp` and `to_cp`. |
| `straight` | Dynamic glue with straight routing. |
| `rightangle` | Dynamic glue with right-angle routing. |
| `curved` | Dynamic glue with curved routing. |
| `point|curved` | Connection-point glue with curved routing. |

## Re-anchor a connector

Pass only the end that should move. A `None` endpoint keeps the current shape.

```python
connector = page.find_shape_by_id("9")
new_target = page.find_shape_by_text("Store")

if connector is not None and new_target is not None:
    page.reanchor_connector(connector, to_shape=new_target)
```

Deleting a shape through `page.delete_shape(shape)` also removes incident connectors and their `Connect` records.

## Work with swimlanes

Swimlane operations require an existing Visio cross-functional flowchart (CFF) page. `add_swimlane()` clones the current top lane and updates the CFF container geometry.

```python
with VisioFile("cross-functional-flow.vsdx") as vis:
    page = vis.pages[0]
    container = page.get_container()

    if container is None:
        raise ValueError("The page is not a Visio CFF diagram")

    review_lane = page.add_swimlane("Review")
    check = vis.create_shape(
        page, "PALETTE_PROCESS", 6.0, 2.0, text="Check"
    )
    page.add_shape_to_lane(check, review_lane)

    assert container.lane_of(check) is not None
    vis.save_vsdx("with-review-lane.vsdx")
```

Visio CFF membership is geometric. Shapes are associated with the lane whose vertical band contains their centre; there is no separate membership field to write.

## Render a Jinja template

Jinja expressions can be stored in shape text and rendered into a new file:

```python
with VisioFile("template.vsdx") as vis:
    vis.jinja_render_vsdx(
        context={"project": "Ward refurbishment", "owner": "Facilities"}
    )
    vis.save_vsdx("rendered.vsdx")
```

The package also supports its existing group-shape loop and `showif` conventions. See `docs/templating.rst` and the `tests/test_jinja*.py` cases for the exact template structure.

## Limits

- The library starts from an existing `.vsdx`; it does not create a complete Visio document package from nothing.
- `.vsdm` files can be read, but creating or saving macro-enabled documents is not supported.
- Swimlane creation works on existing Visio CFF diagrams. It does not convert an ordinary page into a CFF diagram.
- Visio may recalculate layout when a generated file opens. The library writes the glue and route cells but does not reproduce Visio's entire layout engine.

## Development and verification

```bash
python -m pytest tests -q
ruff check vsdx
ruff format --check vsdx
pyrefly check vsdx --min-severity warn
sphinx-build -W --keep-going -b html docs docs/_build/html
python -m build
```

The package is held at pyrefly's `strict` preset. CI tests Python 3.10–3.14 on Ubuntu and Windows. Connector and swimlane changes also run through `tools/visio_check.ps1`, which opens generated files in an invisible Microsoft Visio instance and fails on package repair or automation errors.

## Documentation

The Sphinx source is in [`docs/`](docs/). Build it locally with:

```bash
python -m pip install sphinx sphinx-rtd-theme
python -m sphinx -W --keep-going -b html docs docs/_build/html
```

## Provenance and licence

`vsdxkit` is a fork of [`dave-howard/vsdx`](https://github.com/dave-howard/vsdx), originally written by Dave Howard. The fork keeps the `vsdx` import namespace and BSD-3-Clause licence. See [`LICENSE`](LICENSE).
