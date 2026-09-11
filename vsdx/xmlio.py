"""Zip-backed XML persistence helpers shared across modules."""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET


def file_to_xml(filename: str, zip_file_contents: dict[str, io.BytesIO]) -> ET.ElementTree[ET.Element] | None:
    """Import a file as an ElementTree."""
    if filename in zip_file_contents:
        content: io.BytesIO = zip_file_contents[filename]
        return ET.parse(io.BytesIO(content.getvalue()))
    return None


def xml_to_file(xml: ET.ElementTree[ET.Element], filename: str, zip_file_contents: dict[str, io.BytesIO]) -> None:
    """Save an ElementTree to zip_file_contents."""
    file: io.BytesIO = io.BytesIO()
    xml.write(file, xml_declaration=True, method="xml", encoding="UTF-8")
    zip_file_contents[filename] = io.BytesIO(file.getvalue())


def require_tree(tree: ET.ElementTree[ET.Element] | None, description: str) -> ET.ElementTree[ET.Element]:
    """A required in-memory ElementTree (already parsed from the package)."""
    if tree is None:
        raise ValueError(f"expected document part not found: {description}")
    return tree


def require_xml_tree(filename: str, zip_file_contents: dict[str, io.BytesIO], description: str) -> ET.ElementTree[ET.Element]:
    """Parse a required XML part from the zip and return its ElementTree."""
    tree = file_to_xml(filename, zip_file_contents)
    if tree is None:
        raise ValueError(f"expected XML part not found: {description} ({filename})")
    return tree


def require_root(filename: str, zip_file_contents: dict[str, io.BytesIO], description: str) -> ET.Element:
    """Parse a required XML part from the zip and return its root element."""
    return require_element(require_xml_tree(filename, zip_file_contents, description).getroot(), description)


def require_element(element: ET.Element | None, description: str) -> ET.Element:
    """Return a required XML element, or raise with a description of what was expected.

    Visio parts are schema-driven: a missing Pages/Page/PageSheet/Cell element
    means the document is malformed rather than that the caller should branch.
    Fail loudly with the path instead of raising AttributeError on None.
    """
    if element is None:
        raise ValueError(f"expected XML element not found: {description}")
    return element
