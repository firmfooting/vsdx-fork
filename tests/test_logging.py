"""Logging behaviour: library-grade defaults per the Python logging HOWTO."""

import io
import logging

from vsdx import VisioFile

BASE = "test8_simple_connector.vsdx"


def test_no_output_on_default_configuration(vsdx_copy, capsys):
    """Default config: NullHandler only; nothing reaches stdout/stderr."""
    path = vsdx_copy(BASE)
    with VisioFile(path) as vis:
        vis.pages[0].delete_shape(vis.pages[0].all_shapes[0])
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_debug_true_bridges_to_logging(vsdx_copy, capsys):
    """debug=True reproduces the old print behaviour via a logging handler."""
    path = vsdx_copy(BASE)
    with VisioFile(path, debug=True) as vis:
        vis.pages[0]  # touch enough to trigger debug paths
    # handler writes to stderr; capsys captures it even though it is
    # bypassing print (StreamHandler holds the stream by default capture)
    err = capsys.readouterr().err
    assert "vsdx.vsdxfile" in err


def test_host_application_can_capture_module_logs(vsdx_copy):
    """A host app configures the 'vsdx' logger and receives module records."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    root = logging.getLogger("vsdx")
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    try:
        path = vsdx_copy(BASE)
        with VisioFile(path) as vis:
            vis.remove_page_by_index(0)
        assert "_remove_page_from_app_xml()" in stream.getvalue()
        assert "VisioFile(filename=" in stream.getvalue()
    finally:
        root.removeHandler(handler)
        root.setLevel(logging.NOTSET)


def test_lazy_formatting_at_disabled_levels():
    """Disabled levels must not interpolate arguments (HOWTO requirement)."""

    class Boom:
        def __str__(self):
            raise RuntimeError("eagerly formatted")

    logging.getLogger("vsdx").setLevel(logging.WARNING)
    try:
        logging.getLogger("vsdx.vsdxfile").debug("value=%s", Boom())
    except RuntimeError:
        raise AssertionError("arguments were formatted at a disabled level") from None
    finally:
        logging.getLogger("vsdx").setLevel(logging.NOTSET)


def test_package_root_has_null_handler_only():
    """Library contract: the 'vsdx' logger carries a NullHandler and no
    propagation-escaping handlers of other kinds by default."""
    root = logging.getLogger("vsdx")
    vsdx_handlers = [h for h in root.handlers if not getattr(h, "_vsdx_debug_handler", False)]
    assert len(vsdx_handlers) == 1
    assert isinstance(vsdx_handlers[0], logging.NullHandler)
