"""Shared pytest fixtures for the vsdx test suite."""
import os
import shutil

import pytest

# resolve relative to this file, independent of pytest's working directory
basedir = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture
def vsdx_copy(tmp_path):
    """Return a factory giving a fresh copy of a test file in tmp_path."""
    def _copy(filename: str) -> str:
        source = os.path.join(basedir, filename)
        destination = os.path.join(str(tmp_path), filename)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copy(source, destination)
        return destination
    return _copy
