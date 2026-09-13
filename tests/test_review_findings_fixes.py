"""Tests for findings from reviews of merged PRs (fix pass, September 2026)."""

import os
import struct
import zipfile

import pytest

import vsdx
from vsdx import PackageLimitError, VisioFile
from vsdx.vsdxdiff import VisioFileDiff

basedir = os.path.dirname(os.path.realpath(__file__))


def _copy(name: str, tmp_path) -> str:
    source = os.path.join(basedir, name)
    destination = os.path.join(str(tmp_path), name)
    with open(source, "rb") as reader, open(destination, "wb") as writer:
        writer.write(reader.read())
    return destination


def test_eocd_preflight_rejects_declared_entry_overflow(tmp_path):
    """An EOCD declaring more entries than max_members is rejected before ZipFile runs."""
    path = _copy("test1.vsdx", tmp_path)
    limits = vsdx.PackageLimits(max_members=20)
    VisioFile._preflight_eocd(path, limits)  # real fixture declares 14 < 20: passes

    with open(path, "rb") as handle:
        payload = bytearray(handle.read())
    eocd = payload.rfind(b"PK\x05\x06")
    assert eocd != -1
    payload[eocd + 10 : eocd + 12] = struct.pack("<H", 50_000)
    lying = os.path.join(str(tmp_path), "lying.vsdx")
    with open(lying, "wb") as handle:
        handle.write(payload)

    with pytest.raises(PackageLimitError) as excinfo:
        VisioFile(lying, limits=limits)
    assert excinfo.value.reason == "member_count"


def test_diff_rejects_member_above_cap(tmp_path):
    """A member declaring more than the diff cap is refused, not inflated."""
    document = str(tmp_path / "big.vsdx")
    with zipfile.ZipFile(document, "w") as archive:
        archive.writestr("visio/pages/pages.xml", b"<xml/>")

    # lie about the member's declared uncompressed size in the central directory
    with open(document, "rb") as reader:
        payload = bytearray(reader.read())
    cd = payload.find(b"PK\x01\x02")
    struct.pack_into("<I", payload, cd + 24, VisioFileDiff.MAX_MEMBER_BYTES + 1)
    over = os.path.join(str(tmp_path), "over.vsdx")
    with open(over, "wb") as handle:
        handle.write(payload)

    with pytest.raises(PackageLimitError) as excinfo:
        VisioFileDiff.extract_file_data(over)
    assert excinfo.value.reason == "member_size"
