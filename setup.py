from setuptools import setup, find_packages

from runpy import run_path

# Get the version from the relevant file
d = run_path('fluidfoam/_version.py')
__version__ = d['__version__']

# Get the development status from the version string
if 'a' in __version__:
    devstatus = 'Development Status :: 3 - Alpha'
elif 'b' in __version__:
    devstatus = 'Development Status :: 4 - Beta'
else:
    devstatus = 'Development Status :: 5 - Production/Stable'

def readme():
    with open('README.rst') as f:
        return f.read()

setup(
    name="fluidfoam",
    version=__version__,
    packages=find_packages(exclude=['tutorials']),
    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
    install_requires=['numpy>=1.11', 'scipy>=1.7.4',
                      'matplotlib>=1.5', 'netCDF4'],
    # metadata for upload to PyPI
    author = "Cyrille Bonamy",
    author_email = "cyrille.bonamy@univ-grenoble-alpes.fr",
    description = "Openfoam PostProcessing Python Tools",
    long_description_content_type="text/markdown",
    long_description = readme(),
    license = 'GPLv2',
    keywords = ["Openfoam", "postprocessing", "python", "CFD"],
    url = "http://legi.grenoble-inp.fr",   # project home page, if any
    classifiers=[
        # How mature is this project? Common values are
        # 3 - Alpha
        # 4 - Beta
        # 5 - Production/Stable
        devstatus,
        'Intended Audience :: Science/Research',
        'Intended Audience :: Education',
        'Topic :: Scientific/Engineering',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        #
        # Specify the Python versions you support here. In particular,
        # ensure that you indicate whether you support Python 2,
        # Python 3 or both.
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10'
        ])
