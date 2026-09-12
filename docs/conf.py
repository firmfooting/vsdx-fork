# Configuration for the Sphinx documentation builder.

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

import vsdx

project = "vsdxkit"
copyright = "2021–2026, Dave Howard and Shaun Eccles"  # update when preparing each release
author = "Dave Howard and Shaun Eccles"
release = vsdx.__version__
version = vsdx.__version__

extensions = [
    "sphinx.ext.autodoc",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_title = f"vsdxkit {release}"
