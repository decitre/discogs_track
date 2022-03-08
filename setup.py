import setuptools
from discogs_track import __version__

setuptools.setup(
    name='discogs_track',
    version=__version__,
    license_files=('LICENSE',),
    packages=['discogs_track'],
    py_modules=['silly_collector'],
    entry_points={'console_scripts': ['discogs_track=discogs_track:cli']},
    python_requires='>=3.7',
)
