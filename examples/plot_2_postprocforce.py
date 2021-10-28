"""
Read and Plot a time series of OpenFoam postProcessing force
============================================================

This example reads and plots a series of postProcessing force
"""

###############################################################################
# Read the postProcessing files
# -----------------------------
#
# .. note:: In this example it reads and merges two postProcessing files
#           automatically (with the 'mergeTime' option)

# import readforce function from fluidfoam package
from fluidfoam.readpostpro import readforce

sol = '../output_samples/ascii/'

force = readforce(sol, time_name = 'mergeTime')

###############################################################################
# Now plots the pressure force
# ----------------------------
#

import matplotlib.pyplot as plt

plt.figure()

plt.plot(force[:, 0], force[:, 1])

# Setting axis labels
plt.xlabel('t (s)')
plt.ylabel('p (Pa)')

# add grid
plt.grid()
