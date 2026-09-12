"""Regression tests for save_vsdx destination and repeat-save handling."""

import os
import zipfile
from pathlib import Path

import pytest

from vsdx import VisioFile

BASE = "test8_simple_connector.vsdx"


def test_save_vsdx_no_filename_saves_in_place(vsdx_copy):
    src = vsdx_copy(BASE)
    with VisioFile(src) as vis:
        shape = vis.pages[0].find_shape_by_text("Shape A")
        assert shape is not None
        shape.text = "Renamed A"
        vis.save_vsdx()
    with VisioFile(src) as vis:
        assert vis.pages[0].find_shape_by_text("Renamed A") is not None


def test_save_vsdx_appends_vsdx_suffix(vsdx_copy):
    src = vsdx_copy(BASE)
    out = str(src)[:-5] + "_out"
    with VisioFile(src) as vis:
        vis.save_vsdx(out)

    assert os.path.exists(out + ".vsdx")
    with VisioFile(out + ".vsdx") as vis:
        assert len(vis.pages) == 1


def test_save_vsdx_accepts_uppercase_suffix(vsdx_copy):
    src = vsdx_copy(BASE)
    destination = Path(src).with_name("UPPER.VSDX")

    with VisioFile(src) as vis:
        vis.save_vsdx(str(destination))

    assert destination.exists()
    assert not Path(f"{destination}.vsdx").exists()


def test_save_vsdx_creates_nested_parent_directories(vsdx_copy, tmp_path):
    src = vsdx_copy(BASE)
    destination = tmp_path / "nested" / "deeper" / "saved.vsdx"

    with VisioFile(src) as vis:
        vis.save_vsdx(str(destination))

    with VisioFile(str(destination)) as vis:
        assert len(vis.pages) == 1


def test_save_vsdx_refuses_an_empty_package(vsdx_copy, tmp_path):
    src = vsdx_copy(BASE)
    destination = tmp_path / "empty.vsdx"

    with VisioFile(src) as vis:
        vis.zip_file_contents.clear()
        with pytest.raises(ValueError, match="empty package"):
            vis.save_vsdx(str(destination))

    assert not destination.exists()


def test_save_vsdx_twice_preserves_unmodified_parts(vsdx_copy):
    src = vsdx_copy(BASE)
    with zipfile.ZipFile(src) as archive:
        root_rels = archive.read("_rels/.rels")

    with VisioFile(src) as vis:
        vis.save_vsdx()
        vis.save_vsdx()

    with zipfile.ZipFile(src) as archive:
        assert archive.read("_rels/.rels") == root_rels
    with VisioFile(src) as vis:
        assert len(vis.pages) == 1


def test_failed_in_place_save_keeps_original_bytes(vsdx_copy, monkeypatch):
    src = vsdx_copy(BASE)
    original = Path(src).read_bytes()

    def fail_write(*_args, **_kwargs):
        raise RuntimeError("injected ZIP write failure")

    with VisioFile(src) as vis:
        monkeypatch.setattr(zipfile.ZipFile, "writestr", fail_write)
        with pytest.raises(RuntimeError, match="injected ZIP write failure"):
            vis.save_vsdx()

    assert Path(src).read_bytes() == original


def test_two_named_saves_keep_archive_paths_relative(vsdx_copy):
    src = vsdx_copy(BASE)
    first = str(Path(src).with_name("first.vsdx"))
    second = str(Path(src).with_name("second.vsdx"))
    with zipfile.ZipFile(src) as archive:
        source_names = set(archive.namelist())

    with VisioFile(src) as vis:
        vis.save_vsdx(first)
        vis.save_vsdx(second)

    with zipfile.ZipFile(second) as archive:
        assert set(archive.namelist()) == source_names
    with VisioFile(second) as vis:
        assert len(vis.pages) == 1


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits are not meaningful on Windows")
def test_new_named_save_preserves_source_mode(vsdx_copy):
    src = Path(vsdx_copy(BASE))
    src.chmod(0o640)
    destination = src.with_name("mode-copy.vsdx")

    with VisioFile(str(src)) as vis:
        vis.save_vsdx(str(destination))

    assert destination.stat().st_mode & 0o777 == 0o640
