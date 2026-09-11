import os

from vsdx import VisioFile

basedir = os.path.realpath(os.path.join(os.getcwd(), 'vsdx', 'media'))


def test_media_curved_connector_returns_curved():
    """Regression: Media.curved_connector returned the straight connector."""
    from vsdx import Media
    media = Media()
    curved = media.curved_connector
    straight = media.straight_connector
    assert curved is not None and straight is not None
    assert curved.ID != straight.ID
    with VisioFile(os.path.join(basedir, 'media.vsdx')) as vis:
        page = vis.pages[0]
        expected_curved = page.find_shape_by_text('CURVED_CONNECTOR')
        assert curved.ID == expected_curved.ID
