from setuptools import setup, find_packages
setup(
    name="fluidfoam",
    version="0.0.1",
    packages=find_packages(exclude=['tutorials']),
    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
    install_requires=['numpy>=1.11', 'scipy>=0.17',
                      'matplotlib>=1.5'],
    # metadata for upload to PyPI
    author="Cyrille Bonamy",
    author_email="cyrille.bonamy@legi.cnrs.fr",
    description="Openfoam PostProcessing Python Tools",
    license='GPLv2',
    keywords="Openfoam PostProcessing Tools",
    url="http://legi.grenoble-inp.fr",   # project home page, if any
    classifiers=[
        # How mature is this project? Common values are
        # 3 - Alpha
        # 4 - Beta
        # 5 - Production/Stable
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Education',
        'Topic :: Scientific/Engineering',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        # actually CeCILL License (GPL compatible license for French laws)
        #
        # Specify the Python versions you support here. In particular,
        # ensure that you indicate whether you support Python 2,
        # Python 3 or both.
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        ])
