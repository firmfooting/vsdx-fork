import os

from .shapes import Shape
from .vsdxfile import VisioFile


def _media_path(filename: str) -> str:
    """Path to a bundled media vsdx in the module-adjacent 'media' folder."""
    basedir = os.path.relpath(__file__)
    return os.path.join(os.sep.join(basedir.split(os.sep)[:-1]), "media", filename)


class Media:
    straight_connector_text = "STRAIGHT_CONNECTOR"
    curved_connector_text = "CURVED_CONNECTOR"
    rectangle_text = "RECTANGLE"
    circle_text = "CIRCLE"

    def __init__(self) -> None:
        self._media_vsdx: VisioFile | None = VisioFile(_media_path("media.vsdx"))
        self._palette_vsdx: VisioFile | None = None

    @property
    def media(self) -> VisioFile:
        """The sentinel media document, re-opened if close() has been called."""
        if self._media_vsdx is None:
            self._media_vsdx = VisioFile(_media_path("media.vsdx"))
        return self._media_vsdx

    @property
    def palette(self) -> VisioFile:
        """Lazy-loaded extended shape palette (sentinel-text shapes:
        PALETTE_PROCESS, PALETTE_DECISION, PALETTE_START_END,
        PALETTE_PARALLELOGRAM, PALETTE_DATABASE)."""
        if self._palette_vsdx is None:
            self._palette_vsdx = VisioFile(_media_path("palette_extended.vsdx"))
        return self._palette_vsdx

    def close(self) -> None:
        if self._media_vsdx is not None:
            self._media_vsdx.close_vsdx()
            self._media_vsdx = None
        if self._palette_vsdx is not None:
            self._palette_vsdx.close_vsdx()
            self._palette_vsdx = None

    def _sentinel(self, text: str) -> Shape:
        """The media shape carrying a given sentinel text.

        A missing sentinel means the bundled media.vsdx is wrong, so fail loudly
        rather than handing callers a None shape.
        """
        shape = self.media.pages[0].find_shape_by_text(text)
        if shape is None:
            raise ValueError(f"media document has no shape with sentinel text {text!r}")
        return shape

    @property
    def rels_xml(self):
        return self.media.pages[0].rels_xml

    @property
    def straight_connector(self) -> Shape:
        return self._sentinel(Media.straight_connector_text)

    @property
    def curved_connector(self) -> Shape:
        return self._sentinel(Media.curved_connector_text)

    @property
    def rectangle(self) -> Shape:
        return self._sentinel(Media.rectangle_text)

    @property
    def circle(self) -> Shape:
        return self._sentinel(Media.circle_text)
