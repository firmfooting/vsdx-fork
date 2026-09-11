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
    def create(page: vsdx.Page=None, from_shape: Shape = None, to_shape: Shape = None,
               route: str = 'dynamic', from_cp: int = 0, to_cp: int = 0) -> Shape:
        """Create a new Connect object between from_shape and to_shape

        route: 'dynamic' (shape glue, default), 'point' (connection-point glue),
        optionally combined routing behaviour via 'straight', 'rightangle' or
        'curved'. When route='point', from_cp/to_cp give the 0-based connection
        point row index on the from/to shapes respectively.

        :returns: a new Connect object
        :rtype: Shape
        """
        if from_shape and to_shape:  # create new connector shape and connect items between this and the two shapes
            # create new connect shape and get id
            media = vsdx.Media()
            connector_shape = media.straight_connector.copy(page)  # default to straight connector
            connector_shape.text = ''  # clear text used to find shape
            # state-based guard: masters provisioned if the document already
            # carries the masters relationship (the on-disk folder only exists
            # after save, so os.path.exists double-provisioned on 2nd+ calls)
            masters_rel_present = any(
                r.attrib.get('Type') == 'http://schemas.microsoft.com/visio/2010/relationships/masters'
                for r in page.vis.document_rels())
            if not masters_rel_present:
                # Add masters folder to directory if not already present
                for file_name, file in media._media_vsdx.zip_file_contents.items():
                    if file_name.startswith(media._media_vsdx._masters_folder):
                        new_file_name = file_name.replace(media._media_vsdx._masters_folder, page.vis._masters_folder)
                        page.vis.zip_file_contents[new_file_name] = file
                page.vis.load_master_pages()  # load copied master page files into VisioFile object
                # add new master to document relationship
                page.vis._add_document_rel(rel_type="http://schemas.microsoft.com/visio/2010/relationships/masters",
                                           target="masters/masters.xml")
                # create masters/master1 elements in [Content_Types].xml
                page.vis._add_content_types_override(content_type="application/vnd.ms-visio.masters+xml",
                                                     part_name_path="/visio/masters/masters.xml")
                page.vis._add_content_types_override(content_type="application/vnd.ms-visio.master+xml",
                                                     part_name_path="/visio/masters/master1.xml")
                # create an initial copy of page_rels from media and attach to this page
                page_rels_xml = copy.deepcopy(media.rels_xml)
                page.rels_xml = page_rels_xml
            elif connector_shape.shape_name not in page.vis._titles_of_parts_list():
                print(f"Warning: Updating existing Page/Master relationships not yet fully implemented. "
                      f"This may cause unexpected outputs.")
                # vsdx has masters - but not this shape
                # todo: Complete this scenario
                #print("conn master page", connector_shape.master_shape.page.filename)
                #print("max page file num", [p.filename[-5:-4] for p in page.vis.master_pages])
                #print("max page id", [p.page_id for p in page.vis.master_pages])
                rel_num = max([int(p.filename[-5:-4]) for p in page.vis.master_pages]) +1
                master_file_path = os.path.join(page.vis.directory, 'visio', 'masters', f'master{rel_num}.xml')
                #print(f"m_num={rel_num} master_file_path={master_file_path}")
                shutil.copy(connector_shape.master_shape.page.filename, master_file_path)
                # todo: ensure master page ID and RId is unique, update shape master_id to refer to new master
                # todo: update mast file name, and add content type override
                # todo: update masters.xml file contents?
                # todo: update visio/pages/_rels/page3.xml.rels - add: <Relationship Id="rId3" Type="http://schemas.microsoft.com/visio/2010/relationships/master" Target="../masters/master1.xml"/>
                rels = page.rels_xml.getroot()
                new_rel = ET.fromstring(f'<Relationship  xmlns="{vsdx.document_rels_namespace[1:-1]}" '
                                        f'Type="http://schemas.microsoft.com/visio/2010/relationships/master" />')
                new_rel.attrib['Id'] = f"rID{rel_num}"
                new_rel.attrib['Target'] = f"../masters/master{rel_num}.xml"
                rels.append(new_rel)
                page.vis._add_content_types_override(content_type="application/vnd.ms-visio.master+xml",
                                                     part_name_path=f"/visio/masters/master{rel_num}.xml")
            else:
                # vsdx has this master shape, but not related to this page
                master_page = page.vis.master_index.get(connector_shape.shape_name)  # type: vsdx.Page
                rel_num = int(master_page.rel_id[-1])
                rels = page.rels_xml.getroot()
                new_rel = ET.fromstring(f'<Relationship  xmlns="{vsdx.document_rels_namespace[1:-1]}" '
                                        f'Type="http://schemas.microsoft.com/visio/2010/relationships/master" />')
                new_rel.attrib['Id'] = master_page.rel_id
                new_rel.attrib['Target'] = "../masters/master1.xml"
                rels.append(new_rel)

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

            # wire glue to the from/to shapes (Visio-faithful formulas, see
            # tests/fixtures/com_reference/manifest.json for ground truth)
            Connect._apply_glue(connector_shape, from_shape, to_shape, route=route,
                                from_cp=from_cp, to_cp=to_cp)

            # initial endpoints so the file renders sensibly even before Visio recalculates
            connector_shape.set_start_and_finish(from_shape.center_x_y, to_shape.center_x_y)
            return connector_shape

    @staticmethod
    def _get_or_create_cell(shape: Shape, name: str, v: str = None, f: str = None):
        """Set or create a cell on a shape, preserving schema cell ordering."""
        cell = shape.cells.get(name)
        if cell is not None:
            if f is not None:
                cell.formula = f
            if v is not None:
                cell.value = v
            return cell
        attribs = f'N="{name}"'
        if v is not None:
            attribs += f' V="{v}"'
        if f is not None:
            attribs += f' F="{f}"'
        cell_el = ET.fromstring(f'<Cell xmlns="{vsdx.namespace[1:-1]}" {attribs}/>')
        # insert after the last direct Cell child so cells stay ahead of Text/Sections
        insert_at = 0
        for i, child in enumerate(list(shape.xml)):
            if child.tag == f'{vsdx.namespace}Cell':
                insert_at = i + 1
        shape.xml.insert(insert_at, cell_el)
        cell = vsdx.Cell(xml=cell_el, shape=shape)
        shape.cells[name] = cell
        return cell

    @staticmethod
    def _connection_point_count(shape: Shape) -> int:
        sections = shape.xml.findall(f'{vsdx.namespace}Section')
        for section in sections:
            if section.attrib.get('N') == 'Connection':
                return len(section.findall(f'{vsdx.namespace}Row'))
        return 0

    @staticmethod
    def _apply_glue(connector_shape: Shape, from_shape: Shape, to_shape: Shape,
                    route: str = 'dynamic', from_cp: int = 0, to_cp: int = 0):
        """Apply Visio-faithful glue between connector and from/to shapes.

        Shape glue (default): _WALKGLUE formulas + GlueType=2, matching what
        Visio writes for a dynamic connector glued to shape PinX.
        Point glue (route='point'): PAR(PNT(...)) formulas referencing
        Connections.Xn/Yn rows; raises ValueError if the shape has too few
        connection points.
        route may also set routing behaviour: 'straight' (ShapeRouteStyle=16),
        'rightangle' (ShapeRouteStyle=1), 'curved' (ShapeRouteStyle=17 +
        ConLineRouteExt=2).
        """
        conn_id = connector_shape.ID

        if route == 'point':
            ends = (('Begin', 'EndX', from_shape, from_cp), ('End', 'BeginX', to_shape, to_cp))
            for prefix, opposite_cell, shape, cp in ends:
                cp_count = Connect._connection_point_count(shape)
                if cp >= cp_count:
                    raise ValueError(
                        f'Shape ID {shape.ID} has {cp_count} connection point(s); '
                        f'cannot glue to connection point index {cp}')
                k = cp + 1
                Connect._get_or_create_cell(
                    connector_shape, f'{prefix}Trigger',
                    f=f'_XFTRIGGER(Sheet{shape.ID}!EventXFMod)')
                pnt = f'PAR(PNT(Sheet{shape.ID}!Connections.X{k},Sheet{shape.ID}!Connections.Y{k}))'
                Connect._get_or_create_cell(connector_shape, f'{prefix}X', f=pnt)
                Connect._get_or_create_cell(connector_shape, f'{prefix}Y', f=pnt)
            beg_connect = (f'<Connect xmlns="http://schemas.microsoft.com/office/visio/2012/main" '
                           f'FromSheet="{conn_id}" FromCell="BeginX" FromPart="9" '
                           f'ToSheet="{from_shape.ID}" ToCell="Connections.X{from_cp + 1}" '
                           f'ToPart="{99 + from_cp + 1}"/>')
            end_connect = (f'<Connect xmlns="http://schemas.microsoft.com/office/visio/2012/main" '
                           f'FromSheet="{conn_id}" FromCell="EndX" FromPart="12" '
                           f'ToSheet="{to_shape.ID}" ToCell="Connections.X{to_cp + 1}" '
                           f'ToPart="{99 + to_cp + 1}"/>')
        else:
            # shape glue - dynamic connector behaviour, formulas as written by Visio 16
            Connect._get_or_create_cell(connector_shape, 'BegTrigger',
                                        f=f'_XFTRIGGER(Sheet{from_shape.ID}!EventXFMod)')
            Connect._get_or_create_cell(connector_shape, 'EndTrigger',
                                        f=f'_XFTRIGGER(Sheet{to_shape.ID}!EventXFMod)')
            walkglue_begin = '_WALKGLUE(BegTrigger,EndTrigger,WalkPreference)'
            walkglue_end = '_WALKGLUE(EndTrigger,BegTrigger,WalkPreference)'
            Connect._get_or_create_cell(connector_shape, 'BeginX', f=walkglue_begin)
            Connect._get_or_create_cell(connector_shape, 'BeginY', f=walkglue_begin)
            Connect._get_or_create_cell(connector_shape, 'EndX', f=walkglue_end)
            Connect._get_or_create_cell(connector_shape, 'EndY', f=walkglue_end)
            Connect._get_or_create_cell(connector_shape, 'GlueType', v='2')
            Connect._get_or_create_cell(connector_shape, 'ObjType', v='2')
            # explicit dynamic routing, as written by Visio 16; overrides the
            # template connector's inherited ShapeRouteStyle=16 (straight)
            Connect._get_or_create_cell(connector_shape, 'ShapeRouteStyle', v='0')
            Connect._get_or_create_cell(connector_shape, 'ConLineRouteExt', v='0')
            Connect._get_or_create_cell(connector_shape, 'ConFixedCode', v='6')
            beg_connect = (f'<Connect xmlns="http://schemas.microsoft.com/office/visio/2012/main" '
                           f'FromSheet="{conn_id}" FromCell="BeginX" FromPart="9" '
                           f'ToSheet="{from_shape.ID}" ToCell="PinX" ToPart="3"/>')
            end_connect = (f'<Connect xmlns="http://schemas.microsoft.com/office/visio/2012/main" '
                           f'FromSheet="{conn_id}" FromCell="EndX" FromPart="12" '
                           f'ToSheet="{to_shape.ID}" ToCell="PinX" ToPart="3"/>')

        if route == 'straight':
            Connect._get_or_create_cell(connector_shape, 'ShapeRouteStyle', v='16')
        elif route == 'rightangle':
            Connect._get_or_create_cell(connector_shape, 'ShapeRouteStyle', v='1')
        elif route == 'curved':
            Connect._get_or_create_cell(connector_shape, 'ShapeRouteStyle', v='17')
            Connect._get_or_create_cell(connector_shape, 'ConLineRouteExt', v='2')

        # Add these new connection relationships to the page
        page = connector_shape.page
        page.add_connect(Connect(xml=ET.fromstring(end_connect), page=page))
        page.add_connect(Connect(xml=ET.fromstring(beg_connect), page=page))

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
