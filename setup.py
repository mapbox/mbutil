from distutils.core import setup

setup(
    name='mbutil',
    version='0.0.2',
    author='Tom MacWright',
    author_email='macwright@gmail.com',
    packages=['mbutil'],
    scripts=['mb-util'],
    url='https://github.com/mapbox/mbutil',
    license='LICENSE.md',
    description='An importer and exporter for MBTiles',
    long_description=open('README.md').read(),
)
