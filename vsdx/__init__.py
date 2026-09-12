"""vsdxkit - create, edit and analyse Microsoft Visio .vsdx files.

The import namespace remains ``vsdx`` for continuity with the upstream
library; the distribution installs as ``vsdxkit``.
"""

import xml.dom.minidom as minidom  # minidom used for prettyprint
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element

namespace = "{http://schemas.microsoft.com/office/visio/2012/main}"  # visio file name space
ext_prop_namespace = "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}"
vt_namespace = "{http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes}"
r_namespace = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
document_rels_namespace = "{http://schemas.openxmlformats.org/package/2006/relationships}"
cont_types_namespace = "{http://schemas.openxmlformats.org/package/2006/content-types}"

# Ref: https://docs.microsoft.com/en-us/office/client-developer/visio/visio-file-format-reference


def pretty_print_element(xml: Element | ET.ElementTree) -> str:
    if isinstance(xml, ET.ElementTree):
        root = xml.getroot()
        return minidom.parseString(ET.tostring(root) if root is not None else b"").toprettyxml()
    return minidom.parseString(ET.tostring(xml)).toprettyxml()


__version__ = "0.6.3"

from .connectors import Connect  # noqa: E402
from .containers import Container  # noqa: E402
from .formulae import calc_value  # noqa: E402
from .geometry import Geometry, GeometryCell, GeometryRow  # noqa: E402
from .logging_support import attach_debug_stream_handler, get_logger  # noqa: E402
from .media import Media  # noqa: E402
from .pages import Page, PagePosition  # noqa: E402
from .shapes import Cell, DataProperty, Shape  # noqa: E402
from .vsdxfile import PackageLimitError, PackageLimits, VisioFile  # noqa: E402

__all__ = [
    "Cell",
    "Connect",
    "Container",
    "DataProperty",
    "Geometry",
    "GeometryCell",
    "GeometryRow",
    "Media",
    "PackageLimitError",
    "PackageLimits",
    "Page",
    "PagePosition",
    "Shape",
    "VisioFile",
    "attach_debug_stream_handler",
    "calc_value",
    "get_logger",
]
