"""Shared pytest fixtures for the vsdx test suite."""
import os
import shutil

import pytest

basedir = os.path.realpath(os.path.join(os.getcwd(), 'tests'))


@pytest.fixture
def vsdx_copy(tmp_path):
    """Return a factory giving a fresh copy of a test file in tmp_path."""
    def _copy(filename: str) -> str:
        source = os.path.join(basedir, filename)
        destination = os.path.join(str(tmp_path), filename)
        shutil.copy(source, destination)
        return destination
    return _copy
