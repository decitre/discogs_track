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


def get_requirements(file_path: str, no_precise_version: bool = False) -> List[str]:
    requirements = []
    with open(file_path, "rt") as r:
        for line in r.readlines():
            package = line.strip()
            if not package or package.startswith("#"):
                continue
            if no_precise_version:
                package = package.split("==")[0]
            requirements.append(package)
    return requirements


project_name = "discogs_track"

if __name__ == "__main__":

    _packages_path = "src"
    _packages = setuptools.find_packages(where=_packages_path)

    with open("README.md", "rt") as r:
        long_description = r.read()

    main_package_path = {
        Path(_packages_path, *package.split("."))
        for package in _packages
        if package.endswith(project_name)
    }.pop()

    version = get_property("__version__", _packages_path, _packages).pop()

    requirements = get_requirements("requirements.txt", no_precise_version=True)
    requirements_test = get_requirements("requirements_test.txt")

    setuptools.setup(
        name=project_name,
        version=version,
        license_files=("LICENSE.txt",),
        package_dir={"": _packages_path},
        packages=_packages,
        long_description=long_description,
        long_description_content_type="text/markdown",
        package_data={project_name: ["py.typed"]},
        entry_points={"console_scripts": [f"{project_name}={project_name}.cli:cli"]},
        python_requires=">=3.6",
        install_requires=requirements,
        extras_require={"dev": requirements_test},
        zip_safe=False,
        url="https://github.com/decitre/discogs_track",
        author="Emmanuel Decitre",
        classifiers=[
            "Programming Language :: Python :: 3 :: Only",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
            "Operating System :: OS Independent",
        ],
    )
