.. fluidfoam documentation master file, created by
   sphinx-quickstart on Thu Jan 11 12:22:00 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

FluidFoam documentation
=======================


.. include:: ../README.rst
   :start-after: .. start-intro


.. User Guide
.. ----------

.. toctree::
   :maxdepth: 2
   :caption: Contents:

..   overview
..   install
..   tutorial
..   examples


Modules Reference
-----------------

Here is presented the general organization of the package
and the documentation of the modules, classes and
functions.

.. autosummary::
   :toctree: generated/
   :caption: General

   fluidfoam.readof
   fluidfoam.processing1d
   fluidfoam.readpostpro
   fluidfoam.meshdesign
   fluidfoam.meshvisu
   fluidfoam.openfoamsimu

.. toctree::
   :maxdepth: 2
   :caption: Example galleries:

   auto_examples/index


More
----

.. |release| image:: https://img.shields.io/pypi/v/fluidfoam.svg
   :target: https://pypi.python.org/pypi/fluidfoam/
   :alt: Latest version

.. |docs| image:: https://readthedocs.org/projects/fluidfoam/badge/?version=latest
   :target: http://fluidfoam.readthedocs.org
   :alt: Documentation status

.. |Travis| image:: https://app.travis-ci.com/fluiddyn/fluidfoam.svg?branch=master
   :target: https://app.travis-ci.com/github/fluiddyn/fluidfoam 
   :alt: Build status

.. |Github-action| image:: https://github.com/fluiddyn/fluidfoam/actions/workflows/build_and_test.yml/badge.svg
   :target: https://github.com/fluiddyn/fluidfoam/actions
   :alt: CI status

.. |coverage| image:: https://codecov.io/gh/fluiddyn/fluidfoam/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/fluiddyn/fluidfoam/branch/master/
   :alt: Code coverage




- `FluidFoam forge on github <https://github.com/fluiddyn/fluidfoam>`_
- FluidFoam in PyPI |release|
- Unittest coverage |coverage|

.. toctree::
   :maxdepth: 1

..   changes
..   to_do

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
