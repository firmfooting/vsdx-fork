"""Master-part import for vsdx documents.

Methods defined here are bound onto VisioFile at import time
(see vsdxfile._bind_extracted_support) so the public API is unchanged
while vsdxfile.py stays reviewable.
"""

from __future__ import annotations

import copy as copy_module
import io
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element

from vsdx import document_rels_namespace, namespace, r_namespace

from .logging_support import get_logger
from .pages import Page
from .shapes import Shape
from .xmlio import file_to_xml, xml_to_file

logger = get_logger(__name__)


class MastersImportMixin:
    def _ensure_masters_for_shape(self, source_shape: Shape) -> str:
        """Ensure this document contains the master that source_shape uses.

        Call with the SOURCE shape (still attached to its original document)
        BEFORE copying it into this document. Master identity is by NAME
        (NameU), matching Visio's MatchByName semantics: numeric master IDs
        are per-document and coincide across documents by chance.

        :param source_shape: the shape in its source document
        :return: the logical master ID the copied shape should reference in
                 this document ('' when the shape references no master or the
                 source reference is dangling)
        """
        src_vis = source_shape.page.vis
        master_ref = source_shape.xml.attrib.get("Master")
        if not master_ref:
            return ""  # shape has no master - nothing to import
        src_masters = src_vis.masters_xml
        if src_masters is None or isinstance(src_masters, list):
            return ""  # source document has no masters part

        # locate the source Master element by numeric ID within the source doc
        source_element = None
        for m in src_masters:
            if m.attrib.get("ID") == master_ref:
                source_element = m
                break
        if source_element is None:
            return ""  # dangling reference - drop rather than corrupt

        master_name = source_element.attrib.get("NameU") or source_element.attrib.get("Name") or ""

        # already present in this document, by name?
        existing = self.master_index.get(master_name)
        if existing is not None:
            return str(existing.page_id)

        source_master_page = src_vis.get_master_page_by_id(master_ref)
        if source_master_page is None or source_master_page.filename not in src_vis.zip_file_contents:
            return ""

        # 1. copy the master part bytes under the next free filename
        prefix = f"{self._masters_folder}/master"
        existing_numbers = [
            int(f[len(prefix) : -4])
            for f in self.zip_file_contents
            if f.startswith(prefix) and f.endswith(".xml") and f[len(prefix) : -4].isdigit()
        ]
        next_num = max(existing_numbers, default=0) + 1
        part_name = f"master{next_num}.xml"
        part_path = f"{self._masters_folder}/{part_name}"
        self.zip_file_contents[part_path] = src_vis.zip_file_contents[source_master_page.filename]

        # 2. ensure this document has a masters.xml to append to
        if self.masters_xml is None or isinstance(self.masters_xml, list):
            self._bootstrap_masters()

        # 3. append the Master element with a fresh logical ID
        numeric_ids = [int(m.attrib["ID"]) for m in self.masters_xml if str(m.attrib.get("ID", "")).isdigit()]
        new_id = max(numeric_ids, default=1) + 1
        if new_id < 2:
            new_id = 2
        new_master_element = copy_module.deepcopy(source_element)
        new_master_element.attrib["ID"] = str(new_id)
        new_rel_id = f"rId{next_num}"
        rel_el = new_master_element.find(f"{namespace}Rel")
        if rel_el is not None:
            rel_el.attrib[f"{r_namespace}id"] = new_rel_id
        self.masters_xml.append(new_master_element)
        # persist masters.xml (save_vsdx does not write it)
        xml_to_file(ET.ElementTree(self.masters_xml), f"{self._masters_folder}/masters.xml", self.zip_file_contents)

        # 4. masters.xml.rels: map the new rel id -> part filename
        master_rels_path = f"{self._masters_folder}/_rels/masters.xml.rels"
        rels_tree = file_to_xml(master_rels_path, self.zip_file_contents)
        rels_root = rels_tree.getroot() if rels_tree is not None else None
        if rels_root is not None:
            existing_targets = {r.attrib.get("Target") for r in rels_root}
            while part_name in existing_targets:  # never clobber an existing mapping
                next_num += 1
                part_name = f"master{next_num}.xml"
                new_rel_id = f"rId{next_num}"
            rel_el = new_master_element.find(f"{namespace}Rel")
            if rel_el is not None:
                rel_el.attrib[f"{r_namespace}id"] = new_rel_id
        else:
            rels_root = ET.fromstring('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
        rels_root.append(
            Element(
                f"{document_rels_namespace}Relationship",
                {
                    "Id": new_rel_id,
                    "Type": "http://schemas.microsoft.com/visio/2010/relationships/master",
                    "Target": part_name,
                },
            )
        )
        xml_to_file(ET.ElementTree(rels_root), master_rels_path, self.zip_file_contents)

        # keep the copied part path in sync with any collision rename
        final_part_path = f"{self._masters_folder}/{part_name}"
        if final_part_path != part_path:
            self.zip_file_contents[final_part_path] = self.zip_file_contents.pop(part_path)

        # 5. package wiring (helpers are idempotent); PartName paths are
        # archive-relative, never absolute
        self._add_content_types_override(
            part_name_path="/visio/masters/masters.xml", content_type="application/vnd.ms-visio.masters+xml"
        )
        self._add_content_types_override(
            part_name_path=f"/visio/masters/{part_name}", content_type="application/vnd.ms-visio.master+xml"
        )
        self._add_document_rel(
            rel_type="http://schemas.microsoft.com/visio/2010/relationships/masters", target="masters/masters.xml"
        )

        # 6. register the new master directly - a full load_master_pages()
        # reload would re-append every existing master to master_pages
        new_master_page = Page(
            file_to_xml(final_part_path, self.zip_file_contents), final_part_path, master_name, str(new_id), new_rel_id, self
        )
        new_master_page.master_unique_id = new_master_element.attrib.get("UniqueID")
        new_master_page.master_base_id = new_master_element.attrib.get("BaseID")
        self.master_pages.append(new_master_page)
        self.master_index[master_name] = new_master_page
        return str(new_id)

    def _bootstrap_masters(self):
        """Create an empty masters part + wiring for documents without masters."""
        masters_root = ET.fromstring(
            '<Masters xmlns="http://schemas.microsoft.com/office/visio/2012/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>'
        )
        self.masters_xml = masters_root
        self.zip_file_contents[f"{self._masters_folder}/masters.xml"] = io.BytesIO(
            ET.tostring(masters_root, xml_declaration=True, encoding="UTF-8")
        )
        self.zip_file_contents[f"{self._masters_folder}/_rels/masters.xml.rels"] = io.BytesIO(
            b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
            b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
        )
        self._add_content_types_override(
            part_name_path="/visio/masters/masters.xml", content_type="application/vnd.ms-visio.masters+xml"
        )
        self._add_document_rel(
            rel_type="http://schemas.microsoft.com/visio/2010/relationships/masters", target="masters/masters.xml"
        )
