import os
import shutil
import tempfile
import zipfile

import pytest

from vsdx import VisioFile

test_directory = os.path.realpath(os.path.join(os.getcwd(), 'tests'))


def get_copy(filename: str, target_dir: str) -> str:
    src = os.path.join(test_directory, filename)
    dst = os.path.join(target_dir, filename)
    shutil.copy(src, dst)
    return dst


def test_connect_shapes_dynamic_glue_formulas():
    with VisioFile(os.path.join(test_directory, 'test8_simple_connector.vsdx')) as vis:
        page = vis.pages[0]
        a = page.find_shape_by_text('Shape A')
        b = page.find_shape_by_text('Shape B')
        assert a is not None and b is not None
        connector = page.connect_shapes(a, b)
        assert connector is not None

        beg_trigger = connector.cells.get('BegTrigger')
        end_trigger = connector.cells.get('EndTrigger')
        assert beg_trigger is not None and end_trigger is not None
        assert beg_trigger.formula == '_XFTRIGGER(Sheet{}!EventXFMod)'.format(a.ID)
        assert end_trigger.formula == '_XFTRIGGER(Sheet{}!EventXFMod)'.format(b.ID)

        walkglue_begin = '_WALKGLUE(BegTrigger,EndTrigger,WalkPreference)'
        walkglue_end = '_WALKGLUE(EndTrigger,BegTrigger,WalkPreference)'
        assert connector.cells['BeginX'].formula == walkglue_begin
        assert connector.cells['BeginY'].formula == walkglue_begin
        assert connector.cells['EndX'].formula == walkglue_end
        assert connector.cells['EndY'].formula == walkglue_end
        assert connector.cells['GlueType'].value == '2'
        assert connector.cells['ShapeRouteStyle'].value == '0'


def test_connect_shapes_glue_records():
    with VisioFile(os.path.join(test_directory, 'test8_simple_connector.vsdx')) as vis:
        page = vis.pages[0]
        a = page.find_shape_by_text('Shape A')
        b = page.find_shape_by_text('Shape B')
        connector = page.connect_shapes(a, b)
        connects = {c.from_rel: c for c in page.connects
                    if c.from_id == str(connector.ID)}
        assert 'BeginX' in connects and 'EndX' in connects
        begin = connects['BeginX']
        assert begin.to_id == str(a.ID)
        assert begin.to_rel == 'PinX'
        end = connects['EndX']
        assert end.to_id == str(b.ID)
        assert end.to_rel == 'PinX'


def test_connect_shapes_route_variants():
    with VisioFile(os.path.join(test_directory, 'test8_simple_connector.vsdx')) as vis:
        page = vis.pages[0]
        a = page.find_shape_by_text('Shape A')
        b = page.find_shape_by_text('Shape B')
        straight = page.connect_shapes(a, b, route='straight')
        assert straight.cells['ShapeRouteStyle'].value == '16'
        right = page.connect_shapes(a, b, route='rightangle')
        assert right.cells['ShapeRouteStyle'].value == '1'
        curved = page.connect_shapes(a, b, route='curved')
        assert curved.cells['ShapeRouteStyle'].value == '17'
        assert curved.cells['ConLineRouteExt'].value == '2'
        plain = page.connect_shapes(a, b)
        assert plain.cells['ShapeRouteStyle'].value == '0'


def test_connect_point_glue_requires_connection_points():
    with VisioFile(os.path.join(test_directory, 'test8_simple_connector.vsdx')) as vis:
        page = vis.pages[0]
        a = page.find_shape_by_text('Shape A')
        b = page.find_shape_by_text('Shape B')
        with pytest.raises(ValueError):
            page.connect_shapes(a, b, route='point')


def test_connector_round_trip_and_zip_validity():
    with tempfile.TemporaryDirectory() as tmp:
        src = get_copy('test8_simple_connector.vsdx', tmp)
        with VisioFile(src) as vis:
            page = vis.pages[0]
            a = page.find_shape_by_text('Shape A')
            b = page.find_shape_by_text('Shape B')
            connector = page.connect_shapes(a, b, route='curved')
            conn_id = connector.ID
            vis.save_vsdx(src)
        with zipfile.ZipFile(src) as z:
            assert z.testzip() is None
        with VisioFile(src) as vis2:
            page = vis2.pages[0]
            reopened = page.find_shape_by_id(str(conn_id))
            assert reopened is not None
            assert reopened.cells['BegTrigger'].formula == '_XFTRIGGER(Sheet{}!EventXFMod)'.format(a.ID)
            assert reopened.cells['EndTrigger'].formula == '_XFTRIGGER(Sheet{}!EventXFMod)'.format(b.ID)
            assert reopened.cells['ShapeRouteStyle'].value == '17'


def test_delete_shape_cascades_connectors():
    with tempfile.TemporaryDirectory() as tmp:
        src = get_copy('test4_connectors.vsdx', tmp)
        with VisioFile(src) as vis:
            page = vis.pages[0]
            before_connects = len(list(page.connects))
            assert before_connects > 0
            doomed = page.find_shape_by_id('2')
            assert doomed is not None
            page.delete_shape(doomed)
            vis.save_vsdx(src)
        with zipfile.ZipFile(src) as z:
            assert z.testzip() is None
        with VisioFile(src) as vis2:
            page = vis2.pages[0]
            # shape 2 and both connectors attached to it (6 and 7) are gone
            assert page.find_shape_by_id('2') is None
            remaining_ids = {str(s.ID) for s in page.all_shapes}
            assert '6' not in remaining_ids
            assert '7' not in remaining_ids
            # no Connect records may reference removed shapes
            for c in page.connects:
                assert c.from_id not in ('2', '6', '7')
                assert c.to_id not in ('2', '6', '7')
