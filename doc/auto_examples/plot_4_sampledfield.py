"""
output field of files without header (sampling)
===============================================

This example doesn't do much, it just reads and makes a simple plot of OpenFoam
field in case of files without header (as for example the output of sampling
library)
"""

###############################################################################
# Read a scalar sampled field and the associated mesh
# ---------------------------------------------------
#
# .. note:: It reads a scalar sampled field and the associated mesh 

# import readscalar, readvector function from fluidfoam package
from fluidfoam import readscalar, readvector

sol = '../output_samples/ascii/wohead'

X, Y, Z = readvector(sol, 'faceCentres')
pressure = readscalar(sol, 'p')
###############################################################################
# Now plot this scalar field
# --------------------------
# In this example it is the pressure coefficient around an airfoil.
# It can be useful to sort the data in order to plot a line and not stars

import matplotlib.pyplot as plt
plt.figure()
plt.plot(X, pressure, '*')
plt.grid()
plt.show()
