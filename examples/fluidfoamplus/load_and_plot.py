"""
Organize simulations results data
=================================

This example shows how to organize the results of a simulation into an object
that contains all the results of one simulations.
"""

###############################################################################
# First create a simulation object with fluidFoamPP
# -------------------------------------------------
#
# .. note:: This class allows you to create an object associated to a
#           simulation
#

# import the class fluidFoamPP
from fluidFoamPP import fluidFoamPP

#path were all simulations are located
path = '../../output_samples'
#Name of simulation to load, if not given, the program lists all simulations
#located in path and ask you to choose which one to load
simu = 'box'
#time step to load, if not given, load last time step
timeStep = '4'

#Load simulation and create an object called mySimu that contain the results of
#the simulation
mySimu = fluidFoamPP(path=path, simu=simu, timeStep=timeStep, structured=True)
# .. note:: All data saved at timeStep of the desired simulations are
#           automatically loaded as a variable of object mySimu.
#           You can now what variables have been loaded using function keys() of
#           the class

mySimu.keys()

# .. note:: function keys() indicates that variables named U, nut and p have
#           been loaded. You can access them simply by typing for example mySimu.U
#           for the velocity field

mySimu.U

###############################################################################
# Averaging along x and z axis (1 and 3)
# --------------------------------------
#
import numpy as np

mySimu.vel_averaged = np.mean(np.mean(mySimu.U, 3), 1)

###############################################################################
# Now plots the profile of the averaged first velocity component
# --------------------------------------------------------------
#

import matplotlib.pyplot as plt

plt.figure()
plt.plot(mySimu.vel_averaged[0], mySimu.y[0, :, 0])

#Setting axis labels
plt.xlabel('U (m/s)')
plt.ylabel('y (m)')

# add grid
plt.grid()

# show figure
plt.show()
