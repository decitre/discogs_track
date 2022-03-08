import setuptools
from discogs_track import __version__

setuptools.setup(
    name='discogs_track',
    version=__version__,
    license_files=('LICENSE',),
    packages=['discogs_track'],
    modules=['silly_collector'],
    python_requires='>=3.7',
)
