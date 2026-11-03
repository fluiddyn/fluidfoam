---
title: 'fluidfoam: from OpenFOAM cases to NumPy arrays in one call'
tags:
  - fluid dynamics
  - CFD
  - post-processing
  - OpenFOAM
  - Python
authors:
  - name: 'Cyrille Bonamy'
    affiliation: 1
    orcid: '0000-0003-3868-7090'
  - name: 'Pierre Augier'
    affiliation: 1
    orcid: '0000-0001-9481-4459'
  - name: 'Quentin Clemencot'
    affiliation: 3
  - name: 'Eduard Puig Montellà'
    affiliation: 4
    orcid: '0000-0001-7184-0945'
  - name: 'Rémi Chassagne'
    affiliation: 1
    orcid: '0000-0002-6448-7909'
  - name: 'Julien Chauchat'
    affiliation: 2
    orcid: '0000-0002-5979-0620'
affiliations:
  - index: 1
    name: Université Grenoble Alpes, CNRS, LEGI, Grenoble, France
    ror: '02rx3b187'
  - index: 2
    name: Université Grenoble Alpes, INRAE, IRD, CNRS, IGE, Grenoble, France
    ror: '02rx3b187'
  - index: 3
    name: Alstom, France
    ror: '00t4db855'
  - index: 4
    name: Centro Oceanográfico de Canarias, Instituto Español de Oceanografía, Consejo Superior de Investigaciones Científicas (IEO-CSIC), Santa Cruz de Tenerife, Spain
    ror: '0580ctc67'
date: '1 November 2026'
bibliography: paper.bib
---

# Summary

Computational fluid dynamics (CFD) researchers, engineers, and students
often use OpenFOAM [@openfoam; @opencfd], an open-source toolbox used
across a very wide range of applications - aerodynamics, heat transfer,
combustion, chemical engineering, and environmental flows alike.
Each simulation produces large output files in OpenFOAM's own
file format, which must then be analysed to compute statistics, plot
profiles, or compare with experiments.

fluidfoam is a Python package that
reads these output files directly, converting meshes and flow fields into
NumPy arrays [@harris2020], the standard array format of the scientific
Python ecosystem, in a single function call. It requires neither an OpenFOAM
installation nor conversion to intermediate formats, and runs on a laptop
analysing data copied from a supercomputer. Results from parallel
simulations, which are split across multiple directories, are reassembled
transparently. Beyond reading, fluidfoam processes the outputs of OpenFOAM
function objects (forces, probes) and writes and reads 1D profiles for
boundary-condition imposition via swak4Foam [@swak4foam]. The package is
pure Python, depends only on NumPy and SciPy [@virtanen2020], and is
released under GPL-3.0.

# Statement of need

Post-processing is a significant fraction of the working time of CFD
researchers. The native OpenFOAM toolchain is oriented towards interactive
visualisation in ParaView [@paraview] or requires converting data to
intermediate formats (VTK, HDF5) before analysis. Many practitioners instead
analyse results in Python, where the scientific ecosystem makes it easy to
compute statistics and spectra, to apply modal decompositions to snapshot
matrices, and to couple simulation output with data-driven workflows.

fluidfoam is designed for researchers and students who need scriptable,
reproducible post-processing of OpenFOAM results: research groups running
parametric studies, teachers preparing course material, and analysts on
machines where OpenFOAM itself is not installed. Studies of canonical flows
typically read tens to hundreds of time steps of several fields, often from
decomposed parallel runs stored on network file systems, so reading files
is a large share of the analysis time; the package aims to keep this cost
modest and to hide the bookkeeping of parallel layouts from the user.

# State of the field

Several Python tools address OpenFOAM data, with different emphases. PyFoam
[@gschaider2023] focuses on case configuration and running rather than
analytical post-processing. Ofpp [@xianghua2023] is a minimal reader that
appears to be no longer actively maintained (no commit since August 2023).
fluidsimfoam [@augier2025] sets up and runs simulations within the fluidsim
framework, relying on HDF5 output rather than native OpenFOAM files. foamlib
[@gerlero2025] is a comprehensive, fully type-hinted library for interacting
with OpenFOAM files and running cases, including asynchronous and Slurm-based
execution. Turbulucid [@mukha2019] provides scripted post-processing and
plotting of plane 2D simulations based on VTK. Generic readers such as the
OpenFOAM reader of ParaView, accessible from Python through PyVista
[@sullivan2019], give access to cases through the VTK data model. A different
approach is taken by PythonFOAM [@maulik2021] and by embedded-interpreter
approaches [@rodriguez2022], which call Python from within the solver for
in-situ analysis;
these require compiling against OpenFOAM and are complementary to the offline
post-processing addressed here.

To our knowledge, fluidfoam offers a specific combination of features that
is not found together in these tools: (i) reconstruction of decomposed
parallel cases directly into global, ordered fields; (ii) automatic reshaping of
structured meshes into multi-dimensional arrays; and (iii) a minimal
dependency footprint (NumPy and SciPy only), which matters for shared
analysis scripts, teaching, and continuous integration.
These tools are largely complementary: a workflow may use foamlib or
fluidsimfoam to launch simulations and fluidfoam to analyse their output.

# Software design

The package is organised in layers. The reading functions (fields, meshes,
patches) form the low-level core; on top of them, an OpenFoamSimu class
loads, in one step, all fields saved at a given time step of a simulation
(or of any simulation found in a directory tree), which is the typical entry
point for exploratory analysis; and specialised modules handle
postProcessing function-object output, mesh design and visualisation for
simple configurations - including the generation of vector figures (SVG,
PDF) of 2D meshes via Matplotlib [@hunter2007] line collections, for
publication-quality mesh illustrations. A dedicated module also closes the
loop between one-dimensional and multi-dimensional simulations: it extracts
vertical profiles of the flow fields from a 1D preliminary run and writes
them in a format that swak4Foam [@swak4foam] can interpolate to impose
boundary or initial conditions on a 2D/3D case. This 1D-to-3D workflow,
classically used to initialise SedFoam studies (see the SedFoam tutorials
[@sedfoamdoc]), turns a costly 3D spin-up into a cheap 1D computation.

Three further design choices structure the core.

First, it is a standalone
reader: it does not wrap OpenFOAM commands and does not link to the
OpenFOAM C++ API. It reads the file format shared by the two OpenFOAM
distributions (the OpenFOAM Foundation and OpenCFD), which removes any
dependence on a particular version or distribution, at the cost of
maintaining a parser for the OpenFOAM file format - a cost kept low because
the format is stable and because the parser handles ASCII, binary (either byte
order, taken from the FoamFile header), and gzip-compressed files uniformly.

A related, deliberate goal was to keep the code small and readable. The
reading core is a single module of about 1,800 lines of plain Python, and
the whole package fits in roughly 3,000 lines without metaprogramming,
type machinery, or asynchronous constructs. Graduate students - a large
share of the user base - can read the parser in an afternoon, adapt it to
their particular output layout, or extend it; we consider this hackability
a feature for research code, at the cost of the ergonomics that larger
frameworks provide.

Second, decomposed parallel cases (uncollated and collated layouts) are
reconstructed transparently using the cell, face, and boundary addressing
files that OpenFOAM writes at decomposition time, so the same call returns
identical arrays for reconstructed and decomposed data, and this
reconstruction is shared by all functionalities. Reading of decomposed
cases can optionally be multi-threaded, with bit-exact results. Since a silent
reconstruction error would be invisible in downstream results, the
transparent reconstruction is validated in the test suite against
reconstructed references.

Third, a benchmark released with the package compares reading times with
foamlib and with OpenFOAM's reconstructPar on fields of $10^6$ and
$8\times10^6$ cells (cold client cache, medians of 10 runs on dedicated
compute nodes with an NFS file system, using fluidfoam 0.4.0, foamlib 1.10.0
and OpenFOAM v2606; scripts and raw outputs are archived with the release;
timings vary by tens of percent between invocations, so ranges are given).
fluidfoam is not the fastest reader of a single file: 26 ms against 14 ms
for foamlib. For $10^6$ cells decomposed into 64 non-contiguous subdomains,
fluidfoam returns the global array in a single call in 0.15 to 0.21 s (0.06
s with 20 threads, an optional setting), against 0.29 to 0.48 s for foamlib,
which does not reconstruct decomposed cases and needs about 30 lines of user
code to reorder the cells with the addressing files. For $8\times10^6$
cells, single-threaded fluidfoam (0.73 s) and foamlib (0.54 to 0.83 s) are
comparable, and eight threads bring fluidfoam to 0.38 s. Alternatively,
reconstructPar can be run once for the field (2.5 s and 9.6 s for the two
cases), after which the reconstructed field is read in 0.04 s and 0.32 s:
this pays off only if the same field is read more than 14 to 24 times, and
requires an OpenFOAM installation and a second copy of the data on disk. All
reported results match a ground-truth array. The benchmark also yields
practical guidance: write results in binary format and load each time series
once.

# Research impact statement

fluidfoam has been developed since 2017, initially as the post-processing
layer of SedFoam [@chauchat2017], a two-phase sediment-transport model used
in morphodynamics research. It has since been used to analyse simulations in
studies of unsteady effects in oscillatory sheet flows [@mathieu2022],
finite-size effects in two-fluid large-eddy simulation of particle-laden
boundary layers [@mathieu2021] and a frictional–collisional model for
bedload transport [@chassagne2023]. It is also the post-processing layer of
the group's other solvers and methods: sedInterFoam, a three-phase model for
free-surface sediment transport [@mathieu2025]; sedExnerFoam, an Exner-based
morphodynamics model [@renaud2026]; and an Exner diagnosis method for
two-fluid morphodynamics simulations [@gilletta2026]. In the SedFoam
tutorials, it is the interface for reading OpenFOAM output [@sedfoamdoc].

Beyond the group, the package is distributed on PyPI and conda-forge. As of
22 October 2026, it has been downloaded over 125,000 times from PyPI since
its first release (about 800 times per month, excluding mirrors) and 376
times from conda-forge over the last six months. Its GitHub repository has
201 stars and 54 forks, and a Google Scholar full-text search finds it
mentioned in 36 publications, after removing homonyms.

fluidfoam is also used beyond the SedFoam solvers, in tidal energy, machine
learning and teaching. In a monopile scour study under tidal flow, it reads
the velocity and pressure fields at the end of each half tidal cycle to
initialise the next one [@liu2024], and a machine-learning study of
transient flow prediction around airfoils uses it to extract the grid and
the flow-field data from the simulations [@xie2024]. The independent package
openfoam-postprocessing builds on fluidfoam for field access [@martins2025].
A series of tutorials by another author presents proper orthogonal
decomposition of OpenFOAM snapshots [@goswami2024; @goswami2025],
function-object post-processing [@goswami2024fo] and the extraction and
analysis of OpenFOAM data [@goswami2024dive]. fluidfoam is also listed in a
survey of open-source CFD tools [@kodman2024]. In a different application
domain, it post-processes the simulations of 120 randomised blade shapes in
an automated design methodology for cross-flow tidal turbines, developed in
a PhD thesis supervised by one of the authors [@ruiz2025]. The
Sphinx-Gallery example gallery and the benchmark datasets provide
reproducible materials for new users.

# AI usage disclosure

In accordance with the JOSS AI usage policy, we disclose the following use
of generative AI. Two assistants were used: the Mistral AI "Vibe Code" agent
(model zai-glm-5-3) and Anthropic's
Claude (model Claude Sonnet 5.5).

- *Paper text:* drafting and copy-editing of sections of this manuscript
  from source material provided by the authors.
- *Benchmark code:* generation of the comparative benchmark scripts and of
  synthetic OpenFOAM-format test datasets, with iterative debugging against
  real OpenFOAM output files.
- *Software:* the most recent changes to the fluidfoam codebase -
  essentially the transparent support of decomposed cases, the optional
  multi-threaded reading and a faster parsing of binary files - were made
  with AI assistance.
- *Documentation:* restructuring of the benchmark documentation.

AI was not used for interactions with editors or reviewers. The human
authors reviewed and validated all AI-assisted outputs, ran the benchmarks
on their own hardware, verified the reported numbers, and made all design
decisions. All modified code is covered by the package's test suite and
continuous integration. The authors remain fully responsible for the
accuracy, originality, licensing, and ethical and legal compliance of all
submitted materials.

# Acknowledgements

The OpenFOAM simulations whose post-processing motivated and shaped
fluidfoam were performed using HPC resources provided by GENCI (Grand
Équipement National de Calcul Intensif) under projects A0160107567,
A0172A14636, A0180107567, A0192A14636 and A0212A14636.
We are thankful to the developers involved in OpenFOAM, and to all the
students and colleagues at LEGI who used fluidfoam and contributed feedback
and bug reports.

# References
