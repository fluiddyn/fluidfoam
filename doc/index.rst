.. fluidfoam documentation master file, created by
   sphinx-quickstart on Thu Jan 11 12:22:00 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

FluidFoam documentation
=======================


The fluidfoam package provides Python classes useful to perform some plot with OpenFoam data.

What is this repository for?
----------------------------

* Openfoam Tools
* Version : 0.1.0
* Supported OpenFoam Versions : 2.4.0, 4.1, 5.0
* Supported Python Versions : 2.7.x, 3.5


Deployment instructions
-----------------------

The simplest way to install fluidfoam is by using pip::

  pip install fluidfoam

You can get the source code from `Bitbucket
<https://bitbucket.org/fluiddyn/fluidfoam>`_ or from `the Python Package Index
<https://pypi.python.org/pypi/fluidfoam/>`_.

The development mode is often useful. From the root directory, run::

  python setup.py develop --user


Committing instructions (in development mode)
---------------------------------------------

To get the status of the files::

  hg st

In case of new file(s)::

  hg add new_file

To commit a revision on the local repository::

  hg ci -m "comment on the revision"

To push the revision on the central repository::

  hg push


Update instructions (in development mode)
-----------------------------------------

Pull the last revision::

  hg pull

Deploy::

  hg up


Example Usage
-------------

* http://servforge.legi.grenoble-inp.fr/pub/soft-sedfoam/

Contacts
--------

* Cyrille.Bonamy@legi.cnrs.fr
* Julien.Chauchat@grenoble-inp.fr
* Pierre.Augier@legi.cnrs.fr
* Tim.Nagel@legi.cnrs.fr
* Thibaud.Revil-Baudard@legi.cnrs.fr

License
-------

fluidfoam is distributed under the CeCILL-B_ License, a BSD compatible
french license.

.. _CeCILL-B: http://www.cecill.info/index.en.html


User Guide
----------

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   overview
   install
   tutorial
   examples


Modules Reference
-----------------

Here is presented the general organization of the package
and the documentation of the modules, classes and
functions.

.. autosummary::
   :toctree: generated/

   fluidfoam.readof

More
----

.. |release| image:: https://img.shields.io/pypi/v/fluidfoam.svg
   :target: https://pypi.org/project/fluidfoam/
   :alt: Latest version

.. |coverage| image:: https://codecov.io/bb/sedfoam/fluidfoam/branch/default/graph/badge.svg
   :target: https://codecov.io/gh/fluiddyn/fluidfoam
   :alt: Code coverage


- `FluidFoam forge on Bitbucket <https://bitbucket.org/fluiddyn/fluidfoam>`_
- FluidFoam in PyPI |release|
- Unittest coverage |coverage|

.. toctree::
   :maxdepth: 1

   changes
   to_do

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
