fluidfoam
=========

[![release](https://img.shields.io/pypi/v/fluidfoam.svg)](https://pypi.python.org/pypi/fluidfoam/)
[![docs](https://readthedocs.org/projects/fluidfoam/badge/?version=latest)](http://fluidfoam.readthedocs.org)
[![Github-action](https://github.com/fluiddyn/fluidfoam/actions/workflows/build_and_test.yml/badge.svg)](https://github.com/fluiddyn/fluidfoam/actions)
[![coverage](https://codecov.io/gh/fluiddyn/fluidfoam/branch/master/graph/badge.svg)](https://codecov.io/gh/fluiddyn/fluidfoam/branch/master/)

The fluidfoam package provides Python classes useful to perform some plot with OpenFoam data.

What is this repository for?
----------------------------

* Openfoam Tools
* Version : 0.2.9
* Supported OpenFoam Versions : 2.4.0, 4.1 to 9, v1712plus to latest
* Supported Python Versions : >= 3.8

Documentation and Examples
--------------------------

[http://fluidfoam.readthedocs.org](http://fluidfoam.readthedocs.org>)

Deployment instructions
-----------------------

The simplest way to install fluidfoam is by using pip::

  `pip install fluidfoam --user`

You can get the source code from [github](https://github.com/fluiddyn/fluidfoam>)
or from [the Python Package Index](https://pypi.python.org/pypi/fluidfoam/).

The development mode is often useful. From the fluidfoam directory, run::

  `python3 -m pip install --editable . --user`
  
Or if you are using a virtual environment, run::

  `python3 -m pip install --editable .`

Committing instructions (in development mode)
---------------------------------------------

A good starting point is to follow this [forking tutorial](https://guides.github.com/activities/forking/).

To clone your fork of fluidfoam repository::

  `git clone https://github.com/your_username/fluidfoam`
  
To get the status of the repository::

  `git status`

In case of new/modified file(s)::

  `git add new_file`

To commit a revision on the local repository::

  `git commit -m "comment on the revision"`

To push the revision on your github fluidfoam repository::

  `git push`

To propose your changes into the main fluidfoam project, follow again the [forking tutorial](https://guides.github.com/activities/forking/).

Example Usage
-------------

* https://sedfoam.github.io

Core Developers
---------------

* Cyrille.Bonamy@univ-grenoble-alpes.fr

Other Contributors
------------------

* Julien.Chauchat@univ-grenoble-alpes.fr
* amathieu@udel.edu
* Remi.Chassagne@univ-grenoble-alpes.fr
* Quentin.Clemencot@univ-grenoble-alpes.fr
* Matthias.Renaud@univ-grenoble-alpes.fr
* Alban.Gilletta.De.Saint.Joseph@france-energies-marines.org
* Gabriel Goncalves

Emeritus Core Developers
------------------------

* Pierre.Augier@legi.cnrs.fr

Emeritus Developers
------------------------

* Guillaume.Maurice@univ-grenoble-alpes.fr
* Tim.Nagel@legi.cnrs.fr

License
-------

fluidfoam is distributed under the GNU General Public License v3 (GPLv3 or newer).

.. _GPLv3: https://www.gnu.org/licenses/gpl-3.0.en.html
