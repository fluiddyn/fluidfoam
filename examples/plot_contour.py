"""
Read and Plot a contour of OpenFoam output from a structured mesh
=================================================================

This example reads and plots a contour of the first component of an OpenFoam
vector field from a structured mesh
"""

###############################################################################
# First reads the mesh and print the shape/size of the mesh
# ---------------------------------------------------------
#
# .. note:: It reads the mesh coordinates for a structured mesh (argument True)
#           and stores them in variables x, y and z

# import readmesh function from fluidfoam package
from fluidfoam import readmesh


sol = '../output_samples/box/'

x, y, z = readmesh(sol, True)

nx, ny, nz = x.shape
print("Nx = ", nx, "Ny = ", ny, "Nz = ", nz)

###############################################################################
# Reads a vector field
# --------------------
#
# .. note:: It reads a vector field from a structured mesh
#           and stores it in vel variable

# import readvector function from fluidfoam package
from fluidfoam import readvector

sol = '../output_samples/box/'
timename = '0'
vel = readvector(sol, timename, 'U', True)

###############################################################################
# Now plots the contour of the first velocity component at a given z position
# ---------------------------------------------------------------------------
#
# .. note:: Here the position z is the middle (// is used to have an integer)

import matplotlib.pyplot as plt

plt.figure()
plt.contourf(x[:, :, nz//2], y[:, :, nz//2], vel[0, :, :, nz//2])

# Setting axis labels
plt.xlabel('x (m)')
plt.ylabel('y (m)')

###############################################################################
# Now add on the same plot the velocity vectors
# ---------------------------------------------
#

plt.figure()
plt.contourf(x[:, :, nz//2], y[:, :, nz//2], vel[0, :, :, nz//2])

# Setting axis labels
plt.xlabel('x (m)')
plt.ylabel('y (m)')

plt.quiver(x[:, :, nz//2], y[:, :, nz//2],
           vel[0, :, :, nz//2], vel[1, :, :, nz//2])
