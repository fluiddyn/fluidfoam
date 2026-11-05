"""
Designing a wall-refined mesh for a boundary-layer computation
==============================================================

This example shows how to use :func:`fluidfoam.meshdesign.getgz` and
:func:`fluidfoam.meshdesign.getdzs` to design the graded mesh typically
used to resolve near-wall gradients in a boundary-layer or sheet-flow
computation.

The mesh is refined towards the wall with a constant expansion ratio, and
blockMesh is parametrised with the grading factor, i.e. the ratio of the
last cell size to the first cell size.

"""

import matplotlib.pyplot as plt
import numpy as np

import fluidfoam

###############################################################################
# Design the mesh
# ---------------
#
# A water column of height h = 1 m is resolved with N = 60 cells; the first
# cell (at the wall) must be dz1 = 1 mm to capture the viscous sublayer.

h = 1.0
dz1 = 0.001
N = 60

z, dz, gz = fluidfoam.getgz(h, dz1, N)
print(f"grading factor gz = {gz:.2f}")

###############################################################################
# The grading factor to enter in blockMesh is simply ``gz`` (or ``1/gz``
# for the opposite direction):
#
# .. code-block:: c++
#
#     // blockMeshDict
#     simpleGrading (1 (60 1 <gz>) 1)
#
# where the expansion is directed from the small wall cells towards the
# free surface.

###############################################################################
# Inverse problem
# ---------------
# Conversely, if the grading factor is imposed (e.g. gz = 10, a common rule
# of thumb), the resulting first and last cell sizes are:

dz1_b, dzN_b = fluidfoam.getdzs(h, 10.0, N)
print(f"gz = 10: first cell = {dz1_b:.2e} m, last cell = {dzN_b:.2e} m")

###############################################################################
# Plot the mesh
# -------------

fig, ax = plt.subplots(figsize=(5, 3), dpi=100)

# cell edges and centres
edges = z
centres = 0.5 * (edges[:-1] + edges[1:])

# visualise the cells as horizontal lines
ax.hlines(centres, 0, 1, color="C0", lw=0.8)
for e in edges[::5]:
    ax.axhline(e, color="k", lw=0.3)

ax.invert_yaxis()  # wall at the top, as in a channel flow
ax.set_xlabel("x")
ax.set_ylabel("z [m]")
ax.set_title(f"graded mesh: N = {N}, gz = {gz:.1f}")

plt.tight_layout()
plt.show()
