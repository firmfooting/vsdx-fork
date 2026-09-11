from __future__ import annotations
import shutil
import os
import copy


import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element

import vsdx
from .shapes import Shape


class Connect:
    """Connect class to represent a connection between two `Shape` objects"""
    def __init__(self, xml: Element=None, page: vsdx.Page=None):
        if page is None:
            return
        if type(xml) is Element:  # create from xml
            self.xml = xml
            self.page = page  # type: vsdx.Page
            self.from_id = xml.attrib.get('FromSheet')  # ref to the connector shape
            self.to_id = xml.attrib.get('ToSheet')  # ref to the shape where the connector terminates
            self.from_rel = xml.attrib.get('FromCell')  # i.e. EndX / BeginX
            self.to_rel = xml.attrib.get('ToCell')  # i.e. PinX

    @staticmethod
    def create(page: vsdx.Page=None, from_shape: Shape = None, to_shape: Shape = None) -> Shape:
        """Create a new Connect object between from_shape and to_shape

        :returns: a new Connect object
        :rtype: Shape
        """
        if from_shape and to_shape:  # create new connector shape and connect items between this and the two shapes
            # create new connect shape and get id
            media = vsdx.Media()
            media_shape = media.straight_connector
            # guard on in-memory document state, not the filesystem: the
            # extracted folder only exists after save_vsdx(), so an
            # os.path.exists guard re-provisions on the second Connect.create()
            # and duplicates package metadata (#93)
            masters_rel_present = any(
                r.attrib.get('Type') == 'http://schemas.microsoft.com/visio/2010/relationships/masters'
                for r in page.vis.document_rels())
            new_master_id = None
            if not masters_rel_present:
                # document has no masters at all: copy the media masters folder
                for file_name, file in media._media_vsdx.zip_file_contents.items():
                    if file_name.startswith(media._media_vsdx._masters_folder):
                        new_file_name = file_name.replace(media._media_vsdx._masters_folder, page.vis._masters_folder)
                        page.vis.zip_file_contents[new_file_name] = file
                page.vis.load_master_pages()
                page.vis._add_document_rel(rel_type="http://schemas.microsoft.com/visio/2010/relationships/masters",
                                           target="masters/masters.xml")
                page.vis._add_content_types_override(content_type="application/vnd.ms-visio.masters+xml",
                                                     part_name_path="/visio/masters/masters.xml")
                page.vis._add_content_types_override(content_type="application/vnd.ms-visio.master+xml",
                                                     part_name_path="/visio/masters/master1.xml")
                # per-page master relationship (creates + registers the page
                # rels part so save_vsdx persists it)
                page._ensure_page_master_rel('rId1', 'master1.xml')
            else:
                # document has masters: import the connector master (by name)
                # BEFORE the copy, while media_shape still points at its source
                new_master_id = page.vis._ensure_masters_for_shape(media_shape) or None

            connector_shape = media_shape.copy(page)  # default to straight connector
            connector_shape.text = ''  # clear text used to find shape
            if new_master_id:
                # repoint the copied shape at this document's imported master
                connector_shape.xml.attrib['Master'] = new_master_id
                connector_shape.master_page_ID = new_master_id

            # per-page relationship for whichever master the connector uses
            effective_master_id = new_master_id or connector_shape.master_page_ID
            master_page = page.vis.get_master_page_by_id(effective_master_id) if effective_master_id else None
            if master_page is not None:
                master_part = master_page.filename.replace(page.vis._masters_folder + '/', '')
                page._ensure_page_master_rel(master_page.rel_id, master_part)

            # update HeadingPairs and TitlesOfParts in app.xml
            if page.vis._get_app_xml_value('Masters') is None:
                page.vis._set_app_xml_value('Masters', '1')

            if connector_shape.shape_name not in page.vis._titles_of_parts_list():  # todo: replace static string with name from shape
                page.vis._add_titles_of_parts_item(connector_shape.shape_name)

            # copy style used by new connector shape
            if not isinstance(page.vis._get_style_by_id(connector_shape.master_shape.line_style_id), Element):
                # assume same if is ok, todo: use names for match and increment IDs
                media_style = media._media_vsdx._get_style_by_id(connector_shape.master_shape.line_style_id)
                page.vis._style_sheets().append(media_style)
            media._media_vsdx.close_vsdx()

            # set Begin and End Trigger formulae for the new shape - linking to shapes in destination page
            beg_trigger = connector_shape.cells.get('BegTrigger')
            beg_trigger.formula = beg_trigger.formula.replace('Sheet.1!', f'Sheet{from_shape.ID}!')
            end_trigger = connector_shape.cells.get('EndTrigger')
            end_trigger.formula = end_trigger.formula.replace('Sheet.2!', f'Sheet{to_shape.ID}!')

            # create connect relationships
            # todo: FromPart="12" and ToPart="3" represent the part of a shape to connection is from/to
            end_connect_xml = f'<Connect xmlns="http://schemas.microsoft.com/office/visio/2012/main" FromSheet="{connector_shape.ID}" FromCell="EndX" FromPart="12" ToSheet="{to_shape.ID}" ToCell="PinX" ToPart="3"/>'
            beg_connect_xml = f'<Connect xmlns="http://schemas.microsoft.com/office/visio/2012/main" FromSheet="{connector_shape.ID}" FromCell="BeginX" FromPart="9" ToSheet="{from_shape.ID}" ToCell="PinX" ToPart="3"/>'

            # Add these new connection relationships to the page
            page.add_connect(Connect(xml=ET.fromstring(end_connect_xml), page=page))
            page.add_connect(Connect(xml=ET.fromstring(beg_connect_xml), page=page))
            #print(vsdx.pretty_print_element(connector_shape.xml))
            #print(connector_shape.geometry)

            connector_shape.set_start_and_finish(from_shape.center_x_y, to_shape.center_x_y)
            print([(m.rel_id, m.page_id) for m in page.vis.master_pages])
            return connector_shape

    @property
    def shape_id(self):
        # ref to the shape where the connector terminates - convenience property
        return self.to_id

    @property
    def shape(self) -> Shape:
        return self.page.find_shape_by_id(self.shape_id)

    @property
    def connector_shape_id(self):
        # ref to the connector shape - convenience property
        return self.from_id

    @property
    def connector_shape(self) -> Shape:
        return self.page.find_shape_by_id(self.connector_shape_id)

    def __repr__(self):
        return f"Connect: from={self.from_id} to={self.to_id} connector_id={self.connector_shape_id} shape_id={self.shape_id}"
