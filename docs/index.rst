vsdxkit documentation
=====================

``vsdxkit`` creates, edits and analyses Microsoft Visio ``.vsdx`` files with
Python. The distribution is called ``vsdxkit``; code imports it as ``vsdx``.
Microsoft Visio is not required at runtime.

The library works on the XML parts inside an existing Visio package. It can
query and edit shapes, create common flowchart shapes, create and re-anchor
connectors, extend existing cross-functional flowcharts, copy pages and render
Jinja-backed templates.

.. note::

   ``vsdxkit`` is not yet published on PyPI. Install it from the GitHub
   repository as described in :doc:`quickstart`.

.. toctree::
   :maxdepth: 2
   :caption: Guides

   quickstart
   create_connect
   swimlanes
   templating
   find_shape
   classes

Format support
--------------

* Python 3.10–3.14 on Linux and Windows
* read, edit and save ``.vsdx``
* read-only support for ``.vsdm``
* no Microsoft Visio dependency at runtime
* generated connectors and swimlanes checked against real Visio through COM

The library starts from an existing package. It does not construct a complete
Visio document from an empty file, and it does not create or save macro-enabled
``.vsdm`` documents.

Project
-------

Source and issues: https://github.com/shauneccles/vsdx

Upstream project: https://github.com/dave-howard/vsdx

* :ref:`genindex`
