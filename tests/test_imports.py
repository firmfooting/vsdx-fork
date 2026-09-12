import pkgutil
from importlib import import_module

import vsdx


def test_all_package_modules_import():
    discovery_errors: list[str] = []
    modules = list(
        pkgutil.walk_packages(
            vsdx.__path__,
            f"{vsdx.__name__}.",
            onerror=discovery_errors.append,
        )
    )

    assert discovery_errors == []
    for module in modules:
        import_module(module.name)
