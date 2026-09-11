from __future__ import annotations
from enum import IntEnum

from typing import List
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .vsdxfile import VisioFile
import vsdx

import io
import xml.etree.ElementTree as ET

import deprecation

from .connectors import Connect
from .shapes import Shape
# from .vsdxfile import file_to_xml  # todo: refactor this away - defined in set_name() to break circular imports

from vsdx import namespace, pretty_print_element


class PagePosition(IntEnum):
    FIRST =  0
    LAST  = -1
    END   = -1
    AFTER = -2
    BEFORE= -3


class Page:
    """Represents a page or a master page in a vsdx file

    :param vis: the VisioFile object the page belongs to
    :type vis: :class:`VisioFile`
    :param name: the name of the page
    :type name: str
    :param connects: a list of Connect objects in the page
    :type connects: List of :class:`Connect`

    """
    def __init__(self, xml: ET.ElementTree, filename: str, page_name: str, page_id: str, rel_id: str, vis: VisioFile):
        self._xml = xml
        self.filename = filename
        self._name = page_name
        self._background = None
        self.page_id = page_id
        self.rel_id = rel_id
        self.master_unique_id = None
        self.master_base_id = None
        self.rels_xml_filename = None
        self.rels_xml = None  # type: ET.ElementTree
        self.vis = vis
        self.max_id = 0
        # todo: add page id - from pages_xml - PageSheet[ID]

    def __repr__(self):
        return f"<Page name={self.name} file={self.filename} >"

    @property
    def connects(self):
        return self.get_connects()

    @deprecation.deprecated(deprecated_in="v0.5.0", removed_in="1.0.0", current_version=vsdx.__version__,
                            details="Use Page.name property instead")
    def set_name(self, value: str):
        from .vsdxfile import file_to_xml  # to break circular imports - is this really needed?
        pages_filename = self.vis._pages_filename()  # pages contains Page name, width, height, mapped to Id
        pages = file_to_xml(pages_filename, self.vis.zip_file_contents)  # this contains a list of pages with rel_id and filename
        page = pages.getroot().find(f"{namespace}Page[{self.index_num + 1}]")
        if page:
            page.attrib['Name'] = value
            self.name = value
            self.vis.pages_xml = pages

    @property
    def name(self):
        if self._name:
            return self._name
        name = self.vis.pages_xml.find(f'{namespace}Page[{self.index_num + 1}]').attrib['Name']
        name_u = self.vis.pages_xml.find(f'{namespace}Page[{self.index_num + 1}]').attrib['NameU']
        return name_u or name or self._name  # return unicode name, or name if NameU not set

    @name.setter
    def name(self, value):
        self.vis.pages_xml.find(f'{namespace}Page[{self.index_num + 1}]').attrib['Name'] = str(value)
        self.vis.pages_xml.find(f'{namespace}Page[{self.index_num + 1}]').attrib['NameU'] = str(value)
        self._name = str(value)

    @property
    def background(self):
        if self._background is not None:
            return self._background
        bg = self.vis.pages_xml.find(f'{namespace}Page[{self.index_num + 1}]').attrib.get('Background', "0") != "0"
        self._background = bg
        return self._background

    @background.setter
    def background(self, value):
        value = bool(value)
        if value:
            self.vis.pages_xml.find(f'{namespace}Page[{self.index_num + 1}]').attrib['Background'] = "1"
        else:
            self.vis.pages_xml.find(f'{namespace}Page[{self.index_num + 1}]').attrib['Background'] = "0"
        self._background = value

    @property
    @deprecation.deprecated(deprecated_in="v0.5.0", removed_in="1.0.0", current_version=vsdx.__version__,
                            details="Use Page.name property instead")
    def page_name(self):
        return self.name

    @page_name.setter
    @deprecation.deprecated(deprecated_in="v0.5.0", removed_in="1.0.0", current_version=vsdx.__version__,
                            details="Use Page.name property instead")
    def page_name(self, value):
        self.name = value

    @property
    def is_master_page(self) -> bool:
        """Return True if this page has a master unique id and there is a match in masters xml """
        if isinstance(self.vis.masters_xml, ET.Element) and self.master_unique_id:
            master_match = f'{namespace}Master[@UniqueID="{self.master_unique_id}"]'
            master_element = self.vis.masters_xml.find(master_match)
            return master_element is not None
        return False

    @property
    def _pagesheet_xml(self):
        # get PageSheet element from pages_xml based on page_id
        ps = self.vis.pages_xml.find(f'{namespace}Page[@ID="{self.page_id}"]/{namespace}PageSheet')
        if not isinstance(ps, ET.Element):
            ps = self.vis.masters_xml.find(f'{namespace}Master[@ID="{self.page_id}"]/{namespace}PageSheet')
        return ps

    @property
    def width(self):
        return float(self._pagesheet_xml.find(f'{namespace}Cell[@N="PageWidth"]').attrib.get('V'))

    @width.setter
    def width(self, value):
        value = float(value)
        self._pagesheet_xml.find(f'{namespace}Cell[@N="PageWidth"]').attrib['V'] = str(value)

    @property
    def height(self):
        return float(self._pagesheet_xml.find(f'{namespace}Cell[@N="PageHeight"]').attrib.get('V'))

    @height.setter
    def height(self, value):
        value = float(value)
        self._pagesheet_xml.find(f'{namespace}Cell[@N="PageHeight"]').attrib['V'] = str(value)

    @property
    def xml(self):
        return self._xml

    @xml.setter
    def xml(self, value):
        self._xml = value

    @property
    def _shapes(self):
        """Return a list of :class:`Shape` objects - for each 'Shapes'

        Note: typically returns one :class:`Shape` object which itself contains :class:`Shape` objects

        """
        return [Shape(xml=shapes, parent=self, page=self) for shapes in self.xml.findall(f"{namespace}Shapes")] or []

    @property
    @deprecation.deprecated(deprecated_in="0.5.0", removed_in="1.0.0", current_version=vsdx.__version__,
                            details="Use Page.child_shapes property to access top level shapes of a Page")
    def shapes(self):
        """Return a list of :class:`Shape` objects

        Note: typically returns one :class:`Shape` object which itself contains :class:`Shape` objects

        """
        return [Shape(xml=shapes, parent=self, page=self) for shapes in self.xml.findall(f"{namespace}Shapes")]

    @deprecation.deprecated(deprecated_in="0.5.0", removed_in="1.0.0", current_version=vsdx.__version__,
                            details="Use Page.child_shapes property to access top level shapes of a Page")
    def sub_shapes(self) -> List[Shape]:
        return self.child_shapes

    @property
    def child_shapes(self):
        """Return list of Shape objects at top level of VisioFile.Page

            :returns: list of `Shape` objects
            :rtype: List[Shape]
            """
        # note that self.shapes should always return a single shape
        if self._shapes:
            return self._shapes[0].child_shapes
        return []  # empty list if no top shapes object

    def set_max_ids(self):
        # get maximum shape id from xml in page
        for shapes in self._shapes:
            for shape in shapes.child_shapes:
                id = shape.get_max_id()
                if id > self.max_id:
                    self.max_id = id

        return self.max_id

    @property
    def index_num(self):
        # return zero-based index of this page in parent VisioFile.pages list
        return self.vis.pages.index(self) if self in self.vis.pages else None

    def add_connect(self, connect: Connect):
        connects = self.xml.find(f".//{namespace}Connects")
        if connects is None:
            connects = ET.fromstring(f"<Connects xmlns='{namespace[1:-1]}' xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'/>")
            self.xml.getroot().append(connects)
            connects = self.xml.find(f".//{namespace}Connects")

        connects.append(connect.xml)

    def _ensure_page_master_rel(self, master_rel_id: str, master_part_name: str):
        """Ensure this page's rels reference the given master part.

        Visio writes a per-page relationship to each master used by shapes on
        that page (Target '../masters/masterN.xml'). The rels part is created
        on demand; the filename is registered so save_vsdx persists it.
        """
        if self.rels_xml is None:
            rels_filename = self.filename.replace('visio/pages/', 'visio/pages/_rels/') + '.rels'
            self.rels_xml_filename = rels_filename
            self.rels_xml = ET.ElementTree(ET.fromstring(
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'))
        rels_root = self.rels_xml.getroot()
        assert rels_root is not None
        existing = {r.attrib.get('Target') for r in rels_root}
        target = f'../masters/{master_part_name}'
        if target in existing:
            return
        rel_element = ET.fromstring(
            f'<Relationship xmlns="http://schemas.openxmlformats.org/package/2006/relationships" '
            f'Type="http://schemas.microsoft.com/visio/2010/relationships/master" '
            f'Id="{master_rel_id}" Target="{target}"/>')
        rels_root.append(rel_element)
        # persist into the zip contents so save picks it up even for pages
        # that never had a rels part before
        if self.rels_xml_filename:
            self.vis.zip_file_contents[self.rels_xml_filename] = io.BytesIO(
                ET.tostring(rels_root, xml_declaration=True, encoding='UTF-8'))

    def get_connects(self):
        elements = self.xml.findall(f".//{namespace}Connect")  # search recursively
        connects = [Connect(xml=e, page=self) for e in elements]
        return connects

    def get_connectors_between(self, shape_a_id: str='', shape_a_text: str='',
                              shape_b_id: str='', shape_b_text: str=''):
        shape_a = self.find_shape_by_id(shape_a_id) if shape_a_id else self.find_shape_by_text(shape_a_text)
        shape_b = self.find_shape_by_id(shape_b_id) if shape_b_id else self.find_shape_by_text(shape_b_text)
        connector_ids = set(a.ID for a in shape_a.connected_shapes).intersection(
            set(b.ID for b in shape_b.connected_shapes))

        connectors = set()
        for id in connector_ids:
            connectors.add(self.find_shape_by_id(id))
        return connectors

    def apply_text_context(self, context: dict):
        for s in self._shapes:
            s.apply_text_filter(context)

    def find_replace(self, old: str, new: str):
        for s in self._shapes:
            s.find_replace(old, new)

    def find_shape_by_id(self, shape_id) -> Shape:
        for s in self._shapes:
            found = s.find_shape_by_id(shape_id)
            if found:
                return found

    def _find_shapes_by_id(self, shape_id) -> List[Shape]:
        # return all shapes by ID - should only be used internally where ID is not unique (i.e. copying shapes)
        found = list()
        for s in self._shapes:
            found = s.find_shapes_by_id(shape_id)
            if found:
                return found
        return found

    def find_shape_by_attr(self, attr, attr_value) -> Shape:
        for s in self._shapes:
            found = s.find_shape_by_attr(attr, attr_value)
            if found:
                return found

    def find_shapes_with_same_master(self, shape: Shape) -> List[Shape]:
        # return all shapes with master
        return [s for s in self.all_shapes if
                s.master_shape_ID == shape.master_shape_ID and s.master_page_ID == shape.master_page_ID]

    def find_shape_by_text(self, text: str) -> Shape:
        for s in self._shapes:
            found = s.find_shape_by_text(text)
            if found:
                return found

    def find_shapes_by_text(self, text: str) -> List[Shape]:
        shapes = list()
        for s in self._shapes:
            found = s.find_shapes_by_text(text)
            if found:
                shapes.extend(found)
        return shapes

    def find_shapes_by_regex(self, regex: str) -> List[Shape]:
        """Search for shapes in this page's top shape by regex"""
        return self._shapes[0].find_shapes_by_regex(regex) if len(self._shapes) else []

    @property
    def all_shapes(self):
        # return all shapes in page
        return self._shapes[0].all_shapes if len(self._shapes) else []

    def find_shape_by_property_label(self, property_label: str) -> Shape:
        """Search for shapes in this page's top shape by property label"""
        # note: use label rather than name as label is more easily visible in diagram
        return self._shapes[0].find_shape_by_property_label(property_label) if len(self._shapes) else None

    def find_shapes_by_property_label(self, property_label: str) -> List[Shape]:
        # return all matching shapes with property label
        shapes = list()
        for s in self._shapes:
            found = s.find_shapes_by_property_label(property_label)
            if found:
                shapes.extend(found)
        return shapes

    def find_shape_by_property_label_value(self, property_label: str, property_value: str) -> Shape:
        # return first matching shape with label
        # note: use label rather than name as label is more easily visible in diagram
        for s in self._shapes:
            found = s.find_shape_by_property_label_value(property_label, property_value)
            if found:
                return found

    def find_shapes_by_property_label_value(self, property_label: str, property_value: str) -> List[Shape]:
        # return all matching shapes with property label and value
        shapes = list()
        for s in self._shapes:
            found = s.find_shapes_by_property_label_value(property_label, property_value)
            if found:
                shapes.extend(found)
        return shapes

    def connect_shapes(self, from_shape: Shape, to_shape: Shape, route: str = 'dynamic',
                       from_cp: int = 0, to_cp: int = 0) -> Shape:
        """Create a Visio-faithful dynamic connector between two shapes on this page.

        route: 'dynamic' (shape glue, default), 'point' (connection-point glue
        using from_cp/to_cp 0-based connection point indexes), optionally with
        routing behaviour 'straight', 'rightangle' or 'curved' - e.g.
        route='straight' or route='point|curved'.

        :returns: the new connector Shape
        :rtype: Shape
        """
        parts = route.split('|') if route else []
        glue = 'point' if 'point' in parts else 'dynamic'
        behaviour = next((p for p in parts if p in ('straight', 'rightangle', 'curved')), None)
        return vsdx.Connect.create(page=self, from_shape=from_shape, to_shape=to_shape,
                                   route=behaviour or glue, from_cp=from_cp, to_cp=to_cp)

    def delete_shape(self, shape: Shape):
        """Delete a shape from this page, removing any incident connectors.

        Connectors whose Begin or End glue references the shape are deleted
        first (including their Connect records), then the shape itself.
        """
        shape_id = str(shape.ID)
        # connectors are the FromSheet of Connect records whose ToSheet is the
        # doomed shape, on a begin/end relationship
        connector_ids = {c.from_id for c in self.connects
                         if c.to_id == shape_id and c.from_rel in ('BeginX', 'EndX')}
        doomed = set()
        for s in self.all_shapes:
            sid = str(s.ID)
            if sid == shape_id:
                doomed.add(s)
            elif sid in connector_ids and 'BeginX' in s.cells:
                doomed.add(s)
        for s in doomed:
            self._remove_shape_xml(s)

    def _remove_shape_xml(self, shape: Shape):
        """Remove a shape's xml, its Connect records, and (if 1-D) its connectors' records."""
        sid = str(shape.ID)
        connects_el = self.xml.find(f'.//{namespace}Connects')
        if connects_el is not None:
            for connect in list(connects_el):
                if connect.attrib.get('FromSheet') == sid or connect.attrib.get('ToSheet') == sid:
                    connects_el.remove(connect)
        for shapes_el in self.xml.iter(f'{namespace}Shapes'):
            if shape.xml in list(shapes_el):
                shapes_el.remove(shape.xml)
                break
