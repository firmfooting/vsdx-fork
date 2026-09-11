"""save_vsdx destination handling (in-place, suffix, explicit path)."""

from vsdx import VisioFile

BASE = "test8_simple_connector.vsdx"


def test_save_vsdx_no_filename_saves_in_place(vsdx_copy, tmp_path):
    src = vsdx_copy(BASE)
    with VisioFile(src) as vis:
        vis.pages[0].find_shape_by_text("Shape A").text = "Renamed A"
        vis.save_vsdx()  # used to raise AttributeError on None
    with VisioFile(src) as vis:
        assert vis.pages[0].find_shape_by_text("Renamed A") is not None


def test_save_vsdx_appends_vsdx_suffix(vsdx_copy):
    src = vsdx_copy(BASE)
    out = str(src)[:-5] + "_out"  # no .vsdx suffix
    with VisioFile(src) as vis:
        vis.save_vsdx(out)
    import os

    assert os.path.exists(out + ".vsdx")
    with VisioFile(out + ".vsdx") as vis:
        assert len(vis.pages) == 1
