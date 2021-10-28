"""
Read and Plot OpenFoam output field
===================================

This example doesn't do much, it just reads and makes a simple plot of OpenFoam
field
"""

###############################################################################
# First read a scalar field
# -------------------------
#
# .. note:: It just reads a scalar field and store it in alpha variable

# import readscalar function from fluidfoam package
from fluidfoam import readscalar

sol = '../output_samples/bin/'
timename = '0'

alpha = readscalar(sol, timename, 'alpha')

###############################################################################
# Now plot this scalar field
# --------------------------
#
# In this example, we haven't read the mesh, and can be structured or
# unstructured

import matplotlib.pyplot as plt
plt.figure()
plt.plot(alpha)

