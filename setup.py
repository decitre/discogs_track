import discogs_track  # __init__.py does not import anything
import setuptools


project_name = "discogs_track"


if __name__ == "__main__":
    setuptools.setup(
        name=project_name,
        version=discogs_track.__version__,
        license_files=("LICENSE",),
        packages=setuptools.find_packages(),
        package_data={project_name: ["py.typed"]},
        entry_points={"console_scripts": [f"{project_name}={project_name}:cli"]},
        python_requires=">=3.6",
        zip_safe=False,
    )
