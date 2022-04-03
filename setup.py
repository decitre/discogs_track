import setuptools
from typing import Set, Any, List, Dict
from pathlib import Path


def get_property(prop, packages_path: str, packages: List[str]) -> Set[Any]:
    """
    Searches and returns a property from all packages __init__.py files
    :param prop: property searched
    :param packages_path: root path of packages to search into
    :param packages: array of packages paths
    :return: an set of values
    """
    results = set()
    namespace: Dict[str, Any] = {}
    for package in packages:
        init_file = open(Path(packages_path, package, "__init__.py")).read()
        exec(init_file, namespace)
        if prop in namespace:
            results.add(namespace[prop])
    return results


project_name = "discogs_track"

if __name__ == "__main__":
    _packages_path = "src"
    _packages = setuptools.find_packages(where=_packages_path)
    main_package_path = {
        Path(_packages_path, *package.split("."))
        for package in _packages
        if package.endswith(project_name)
    }.pop()
    version = get_property("__version__", _packages_path, _packages).pop()
    setuptools.setup(
        name=project_name,
        version=version,
        license_files=("LICENSE",),
        package_dir={"": _packages_path},
        packages=_packages,
        package_data={project_name: ["py.typed"]},
        entry_points={"console_scripts": [f"{project_name}={project_name}.cli:cli"]},
        python_requires=">=3.6",
        zip_safe=False,
    )
