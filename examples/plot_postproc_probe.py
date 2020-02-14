"""
Read and Plot a time series of OpenFoam postProcessing probe
============================================================

This example reads and plots a series of postProcessing probe
"""

###############################################################################
# Read the postProcessing files
# -----------------------------
#
# .. note:: In this example it reads and merges two postProcessing files
#           automatically (with the 'mergeTime' option)

# import readprobes function from fluidfoam package
from fluidfoam.readpostpro import readprobes

sol = '../output_samples/ascii/'

# import readprobes function from fluidfoam package
timeU, u = readprobes(sol, time_name = 'mergeTime', name = 'U')
timeP, p = readprobes(sol, time_name = 'mergeTime', name = 'p')

###############################################################################
# Now plots the pressure and y velocity for the first probe
# ---------------------------------------------------------
#

import matplotlib.pyplot as plt

plt.figure()

plt.plot(timeU, u[:, 0, 1])
plt.plot(timeP, p[:, 0])

# Setting axis labels
plt.xlabel('t (s)')

# add grid and legend
plt.grid()
plt.legend(["Uy", "p"])

# show
plt.show()
