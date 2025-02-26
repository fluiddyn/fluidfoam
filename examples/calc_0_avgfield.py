"""
Postprocessing example : Spatial average
========================================

This example doesn't do much, it reads and makes a spatial average of OpenFoam
fields
"""

###############################################################################
# First read the fields
# ---------------------
#
# .. note:: It just reads a scalar and vector field and store it in variables
#
# import readfield function from fluidfoam package
from fluidfoam import readfield, getVolumes

sol = '../output_samples/bin/'
timename = '0'

alpha = readfield(sol, timename, 'alpha')
U = readfield(sol, timename, 'U')

###############################################################################
# Now read the dV from the mesh
# -----------------------------
#
centr,dV = getVolumes(sol)

###############################################################################
# Finally calculate the average of the fields
# -------------------------------------------
#
import numpy as np
avgfield = np.sum(alpha*dV)/np.sum(dV)
avgU = np.sum(U*dV, axis=1)/np.sum(dV)

print("Mean value of the alpha field = ", avgfield)
print("Mean value of the velocity vectorfield = ", avgU)
