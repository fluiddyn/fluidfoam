"""
Time series of postProcessing probe
===================================

This example reads and plots one postProcessing probe and compute and plot the
fft of the y velocity component
"""

###############################################################################
# Read the postProcessing files
# -----------------------------
#
# .. note:: In this example it reads one postProcessing file for the
#           statistically steady state of the flow around a rectangular
#           cylinder. The probe is located downstream and at the edge of the
#           cylinder.

# import readprobes function from fluidfoam package
from fluidfoam.readpostpro import readprobes
import numpy as np

# ****************Selection of case, repository and parameters*************** #
rep = '../output_samples/'
case = 'ascii'

time = '1e+06'             # Simulation start time for fft
variable = 'U'             # Variable on which fft is applied
index = 1                  # Component of U on which fft is applied
numprob = 1                # Number of probes
n0 = 0                     # Start point for the fft
nfft = 500                 # Number of point for the fft
calculdeltat = 100         # Delta t used in the calculation
fftdeltat = 2000           # Sampling Delta t for the fft, note that Tfft = nfft * fftdeltat =< Ttot = endTime - time
timestart = 0              # Start time for sampling from time
display_temp = True

# *************************************************************************** #

# reading Data
timevec, var = readprobes(rep+case+'/', time_name = time, name = variable)

# var as shape Nt, nProbes, 3
nProbes = np.size(var,axis=1)

# Sampling
i = 0

vari = np.zeros((nfft,nProbes))
vart = np.zeros((nfft,nProbes))
while i < nfft:
    for k in range(nProbes):
    	vari[i,k] = var[int(i*fftdeltat/calculdeltat+timestart/calculdeltat), 
                        k, index]
    vart[i] = timevec[int(i*fftdeltat/calculdeltat+timestart/calculdeltat)]
    i += 1

# fft calculation
y1 = np.zeros((nfft,nProbes),dtype = np.complex128)
for k in range(nProbes):
    # Division by nfft to correct the spectral amplitude
    y1[:,k] = np.fft.fft(vari[n0:n0+nfft,k]-np.mean(vari[n0:n0+nfft,k]))/nfft 

###############################################################################
# Now plots the pressure and y velocity for the first probe
# ---------------------------------------------------------
#

import matplotlib.pyplot as plt

plt.rcParams.update({'font.size': 20})
# Temporal plot section
if display_temp:
    plt.plot(vart[n0:n0+nfft], vari[n0:n0+nfft,0],'r')
    plt.xlabel('time (s)')
    plt.ylabel('U (m/s)')
    plt.show()

# frequency plot section
f = np.arange(nfft)*1/(fftdeltat*nfft)
i = 1
plt.figure(figsize=(16, 8))
for k in range(nProbes):
    plt.plot(f[n0:n0+nfft], abs(y1[n0:n0+nfft,k]), label='probe n '+str(k))

plt.axis([0.0, 1/(2*fftdeltat), 0,  1.2*np.max(abs(y1[n0:n0+nfft,:]))])
plt.grid()
plt.legend(loc='upper right')
plt.xlabel(r'f (Hz)')
plt.ylabel(r'Amplitude ($m^2/s^2$)')
plt.show()
