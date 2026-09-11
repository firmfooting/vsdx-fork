"""Zip-backed XML persistence helpers shared across modules."""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET


def file_to_xml(filename: str, zip_file_contents: dict | None = None) -> ET.ElementTree | None:
    """Import a file as an ElementTree."""
    if filename in zip_file_contents:
        content: io.BytesIO = zip_file_contents[filename]
        return ET.parse(io.BytesIO(content.getvalue()))
    return None


def xml_to_file(xml: ET.ElementTree, filename: str, zip_file_contents: dict | None = None):
    """Save an ElementTree to zip_file_contents."""
    file: io.BytesIO = io.BytesIO()
    xml.write(file, xml_declaration=True, method="xml", encoding="UTF-8")
    zip_file_contents[filename] = io.BytesIO(file.getvalue())
