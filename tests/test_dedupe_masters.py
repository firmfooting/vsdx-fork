import os
import shutil

import vsdx
from vsdx import VisioFile

basedir = os.path.realpath(os.path.join(os.getcwd(), 'tests'))


def test_two_connectors_on_one_page_no_duplicate_masters_rels(tmp_path):
    """Regression for duplicated masters rels/content-type overrides.

    The second Connect.create() call against a still-open document must not
    re-provision master parts. The saved package carries exactly one
    masters relationship and one masters.xml / master1.xml override.
    """
    import zipfile

    dst = str(tmp_path / 'two_connectors.vsdx')
    shutil.copy(os.path.join(basedir, 'test8_simple_connector.vsdx'), dst)
    with VisioFile(dst) as vis:
        page = vis.pages[0]
        a = page.find_shape_by_text('Shape A')
        b = page.find_shape_by_text('Shape B')
        assert a is not None and b is not None
        page.add_connect(vsdx.Connect.create(page=page, from_shape=a, to_shape=b))
        # a second connector between the same pair: exercises the
        # already-provisioned path that used to duplicate package metadata
        page.add_connect(vsdx.Connect.create(page=page, from_shape=a, to_shape=b))
        vis.save_vsdx(dst)

    with zipfile.ZipFile(dst) as z:
        rels = z.read('visio/_rels/document.xml.rels').decode()
        content_types = z.read('[Content_Types].xml').decode()
    assert rels.count('relationships/masters') == 1
    assert content_types.count('visio/masters/masters.xml') == 1
    assert content_types.count('visio/masters/master1.xml') == 1
