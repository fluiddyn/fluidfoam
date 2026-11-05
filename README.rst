fluidfoam
=========

.. image:: https://img.shields.io/pypi/v/fluidfoam.svg
   :target: https://pypi.python.org/pypi/fluidfoam/
   :alt: Latest version

.. image:: https://readthedocs.org/projects/fluidfoam/badge/?version=latest
   :target: http://fluidfoam.readthedocs.org
   :alt: Documentation status

.. image:: https://github.com/fluiddyn/fluidfoam/actions/workflows/build_and_test.yml/badge.svg
   :target: https://github.com/fluiddyn/fluidfoam/actions
   :alt: CI status

.. image:: https://codecov.io/gh/fluiddyn/fluidfoam/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/fluiddyn/fluidfoam/branch/master/
   :alt: Code coverage

.. start-intro

Efficient Python library to read, analyze, and visualize OpenFOAM simulation data (ASCII/binary, decomposed cases) — fast, flexible, and publication-ready.

What is this repository for?
----------------------------

* Openfoam Tools
* Version : 0.4.0
* Supported OpenFoam Versions : 2.4.0, 4.1 to 9, v1712plus to latest
* Supported Python Versions : >= 3.10

Documentation and Examples
--------------------------

http://fluidfoam.readthedocs.org

Installation
------------

We recommend installing fluidfoam in a Python virtual environment.

Create the virtual environment (only once)::

  python3 -m venv ~/pyenv

Activate it (each time you open a new terminal)::

  source ~/pyenv/bin/activate

Then install fluidfoam with pip::

  pip install fluidfoam

You can get the source code from `github
<https://github.com/fluiddyn/fluidfoam>`_ or from `the Python Package Index
<https://pypi.python.org/pypi/fluidfoam/>`_.

Development installation
------------------------

The development mode is often useful. First create and activate a virtual
environment as described above, then install `uv <https://docs.astral.sh/uv/>`_
in it::

  pip3 install uv

From the root directory of the repository, run::

  make develop

This runs ``uv sync --active`` and installs fluidfoam in the *currently
activated* virtual environment, so make sure it is activated before.

Other useful commands::

  make tests    # run the test suite (pytest)
  make black    # format the code (black, line length 82)
  make build    # build the package (in dist/)
  make clean    # remove dist/

Committing instructions (in development mode)
---------------------------------------------

A good starting point is to follow this `forking tutorial
<https://guides.github.com/activities/forking/>`_.

1. Fork the repository on GitHub, then clone your fork::

     git clone https://github.com/your_username/fluidfoam
     cd fluidfoam

2. Declare the main repository as the ``upstream`` remote (only once)::

     git remote add upstream https://github.com/fluiddyn/fluidfoam

3. Create a branch for your changes instead of working on ``master``::

     git switch -c my-new-feature

4. Get the status of the repository::

     git status

5. In case of new/modified file(s)::

     git add new_file

6. Format the code and check that the tests pass::

     make black
     make tests

7. Commit a revision on the local repository::

     git commit -m "comment on the revision"

8. Push the branch on your GitHub fluidfoam repository::

     git push -u origin my-new-feature

9. To propose your changes into the main fluidfoam project, open a pull
   request from your branch (see the forking tutorial above).

To update your fork with the latest changes of the main project::

  git fetch upstream
  git rebase upstream/master

Example Usage
-------------

* https://sedfoam.github.io

Core Developers
---------------

* Cyrille.Bonamy@cnrs.fr

Other Contributors
------------------

* Julien.Chauchat@univ-grenoble-alpes.fr
* antoine.mathieu@edf.fr
* eduard.puig@ieo.csic.es
* Remi.Chassagne@univ-grenoble-alpes.fr
* Quentin.Clemencot@univ-grenoble-alpes.fr
* Matthias.Renaud@univ-grenoble-alpes.fr
* Alban.Gilletta-de-saint-joseph@univ-grenoble-alpes.fr
* Gabriel Goncalves

Emeritus Core Developers
------------------------

* Pierre.Augier@cnrs.fr

Emeritus Developers
-------------------

* Guillaume.Maurice@univ-grenoble-alpes.fr
* Tim.Nagel@legi.cnrs.fr

License
-------

fluidfoam is distributed under the GNU General Public License v3 (GPLv3 or newer).

.. _GPLv3: https://www.gnu.org/licenses/gpl-3.0.en.html
