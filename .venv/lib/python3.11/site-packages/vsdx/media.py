import os
from .vsdxfile import VisioFile


class Media:
    straight_connector_text = 'STRAIGHT_CONNECTOR'
    curved_connector_text = 'CURVED_CONNECTOR'
    rectangle_text = "RECTANGLE"
    circle_text = "CIRCLE"

    def __init__(self):
        basedir = str(os.path.relpath(__file__))
        file_path = os.sep.join(basedir.split(os.sep)[:-1])
        file_path = os.path.join(file_path, 'media', 'media.vsdx')
        self._media_vsdx = VisioFile(file_path)
        self._palette_vsdx = None

    @property
    def palette(self) -> VisioFile:
        """Lazy-loaded extended shape palette (sentinel-text shapes:
        PALETTE_PROCESS, PALETTE_DECISION, PALETTE_START_END,
        PALETTE_PARALLELOGRAM, PALETTE_DATABASE)."""
        if self._palette_vsdx is None:
            file_path = os.path.join(
                os.sep.join(str(os.path.relpath(__file__)).split(os.sep)[:-1]),
                'media', 'palette_extended.vsdx')
            self._palette_vsdx = VisioFile(file_path)
        return self._palette_vsdx

    def close(self):
        if self._media_vsdx is not None:
            self._media_vsdx.close_vsdx()
            self._media_vsdx = None
        if self._palette_vsdx is not None:
            self._palette_vsdx.close_vsdx()
            self._palette_vsdx = None

    @property
    def rels_xml(self):
        return self._media_vsdx.pages[0].rels_xml

    @property
    def straight_connector(self):
        return self._media_vsdx.pages[0].find_shape_by_text(Media.straight_connector_text)

    @property
    def curved_connector(self):
        return self._media_vsdx.pages[0].find_shape_by_text(Media.curved_connector_text)

    @property
    def rectangle(self):
        return self._media_vsdx.pages[0].find_shape_by_text(Media.rectangle_text)

    @property
    def circle(self):
        return self._media_vsdx.pages[0].find_shape_by_text(Media.circle_text)
