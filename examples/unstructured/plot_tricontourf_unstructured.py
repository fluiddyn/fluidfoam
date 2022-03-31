"""
Contour from an unstructured mesh
=================================

This example reads and plots a contour of an OpenFoam vector field from an
unstructured mesh by triangulation WITHOUT interpolation on a structured grid
"""

###############################################################################
# Reads the mesh
# --------------
#
# .. note:: It reads the mesh coordinates and stores them in variables x, y
#           and z

# import readmesh function from fluidfoam package
import numpy as np
import matplotlib.pyplot as plt
from fluidfoam import readvector, readscalar
from fluidfoam import readmesh


sol = '../../output_samples/pipeline/'

x, y, z = readmesh(sol)

###############################################################################
# Reads vector and scalar field
# -----------------------------
#
# .. note:: It reads volume scalar field from an unstructured mesh
#           and stores it

# import readvector and readscalar functions from fluidfoam package


timename = '25'
vel = readvector(sol, timename, 'Ub')
alpha = readscalar(sol, timename, 'alpha')


###############################################################################
# Plots the contour of the scalarfield alpha and a patch
# -----------------------------------------------------------------------------
#
# .. note:: The scalar field alpha reprensents the concentration of sediment in
#           in a 2D two-phase flow simulation of erosion below a pipeline

# Define plot parameters
fig, ax = plt.subplots(figsize=(8.5, 3), dpi=100)
plt.rcParams.update({'font.size': 10})
plt.xlabel('x/D')
plt.ylabel('y/D')
d = 0.05
# Add a cuircular patch representing the pipeline
circle = plt.Circle((0, 0), radius=0.5, fc='silver', zorder=10,
                    edgecolor='k')
plt.gca().add_patch(circle)

# Plots the contour of sediment concentration
levels = np.arange(0.0, 0.63, 0.001)

plt.tricontourf(x/d, y/d, alpha, cmap=plt.cm.Reds, levels=levels)

ax.set(xlim=(-2, 7), ylim=(-1.5, 1.5))
plt.show()
