"""Round-trip a saved package through LibreOffice Draw.

libvisio, which backs LibreOffice's Visio import filter, is stricter about
namespace prefixes than Visio itself: a package whose parts arrive under
ElementTree's generated `ns0:` prefixes imports as an empty document or fails
outright (upstream dave-howard/vsdx#90, #35). Converting to PDF headlessly is
the cheapest end-to-end check that the package is still readable by something
other than this library.

Skipped unless `soffice` is on PATH, so it is opt-in locally and gated by a
dedicated CI job.
"""

import os
import shutil
import subprocess

import pytest

import vsdx

basedir = os.path.dirname(os.path.realpath(__file__))

soffice = shutil.which("soffice") or shutil.which("libreoffice")

pytestmark = pytest.mark.skipif(soffice is None, reason="LibreOffice (soffice) is not on PATH")


@pytest.mark.parametrize("filename", ["test1.vsdx", "test4_connectors.vsdx", "test3_house.vsdx"])
def test_edited_package_converts_in_libreoffice(filename, tmp_path):
    out = os.path.join(str(tmp_path), filename)
    with vsdx.VisioFile(os.path.join(basedir, filename)) as vis:
        page = vis.pages[0]
        shape = page.child_shapes[0]
        shape.text = "converted by libreoffice"
        vis.save_vsdx(out)

    profile = os.path.join(str(tmp_path), "profile")
    result = subprocess.run(
        [
            str(soffice),
            f"-env:UserInstallation=file://{profile}",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(tmp_path),
            out,
        ],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    pdf = os.path.join(str(tmp_path), os.path.splitext(filename)[0] + ".pdf")
    assert result.returncode == 0, result.stderr
    assert os.path.exists(pdf), f"no PDF produced: {result.stdout}\n{result.stderr}"
    assert os.path.getsize(pdf) > 0
