"""Serialised parts must carry the prefixes Visio itself writes.

Consumers stricter than Visio — libvisio (LibreOffice Draw) and draw.io's
importer — reject parts whose elements arrive under a generated ``ns0:``
prefix instead of the expected default namespace. See upstream
dave-howard/vsdx#90 and #35.
"""

import os
import re
import zipfile
from xml.etree import ElementTree

import pytest

import vsdx
from vsdx import namespace

basedir = os.path.dirname(os.path.realpath(__file__))

# ElementTree invents ns0:, ns1:, … for any namespace it has no prefix for.
GENERATED_PREFIX_RE = re.compile(rb"[<\s]/?ns\d+:")

ALL_PACKAGES = sorted(name for name in os.listdir(basedir) if name.endswith((".vsdx", ".vsdm")))


def _saved_copy(filename: str, tmp_path) -> str:
    out = os.path.join(str(tmp_path), "out" + os.path.splitext(filename)[1])
    with vsdx.VisioFile(os.path.join(basedir, filename)) as vis:
        page = vis.pages[0]
        _ = page.child_shapes  # force the page part to be parsed and re-serialised
        vis.save_vsdx(out)
    # save_vsdx may adjust the suffix it was handed; take whatever it wrote
    written = os.listdir(str(tmp_path))
    assert len(written) == 1, written
    return os.path.join(str(tmp_path), written[0])


@pytest.mark.parametrize("filename", ALL_PACKAGES)
def test_saved_parts_have_no_generated_namespace_prefixes(filename, tmp_path):
    with zipfile.ZipFile(_saved_copy(filename, tmp_path)) as archive:
        offenders = {
            name
            for name in archive.namelist()
            if name.endswith((".xml", ".rels")) and GENERATED_PREFIX_RE.search(archive.read(name))
        }
    assert offenders == set()


@pytest.mark.parametrize("filename", ALL_PACKAGES)
def test_saved_parts_are_well_formed(filename, tmp_path):
    """Re-prefixing must not rebind a reserved prefix such as `xml:`."""
    with zipfile.ZipFile(_saved_copy(filename, tmp_path)) as archive:
        for name in archive.namelist():
            if not name.endswith((".xml", ".rels")):
                continue
            ElementTree.fromstring(archive.read(name))  # raises ParseError if not


@pytest.mark.parametrize("filename", ALL_PACKAGES)
def test_visio_parts_declare_the_visio_default_namespace(filename, tmp_path):
    """Parts rooted in the Visio vocabulary must carry it as the default namespace.

    Theme parts are rooted in DrawingML and keep their `a:` prefix, so the rule
    follows each part's own root element rather than its path.
    """
    visio_uri = namespace[1:-1]
    checked = 0
    with zipfile.ZipFile(_saved_copy(filename, tmp_path)) as archive:
        for name in archive.namelist():
            if not name.endswith(".xml"):
                continue
            body = archive.read(name)
            root_tag = ElementTree.fromstring(body).tag
            if not root_tag.startswith(f"{{{visio_uri}}}"):
                continue
            checked += 1
            head = body[:1024].decode("utf-8", "replace")
            # parts the library did not rewrite keep Visio's own single quotes
            declared = f'xmlns="{visio_uri}"' in head or f"xmlns='{visio_uri}'" in head
            assert declared, f"{name} does not declare the Visio default namespace"
    assert checked, "expected the package to contain parts in the Visio namespace"


def test_setting_text_preserves_the_formatting_runs_as_elements(tmp_path):
    """The cp/pp runs bracketing a shape's text survive an edit as real elements.

    The runs used to be spliced back as serialised text matched by an `ns0:`
    regex, which broke the moment the Visio namespace stopped being prefixed.
    """
    with vsdx.VisioFile(os.path.join(basedir, "test2.vsdx")) as vis:
        shape = vis.pages[0].find_shape_by_id("9")
        text_element = shape.xml.find(f"{namespace}Text")
        before = [(child.tag, dict(child.attrib)) for child in text_element]
        assert before, "fixture shape is expected to carry formatting runs"

        shape.text = "replaced"

        text_element = shape.xml.find(f"{namespace}Text")
        assert shape.text == "replaced"
        assert [(child.tag, dict(child.attrib)) for child in text_element] == before
