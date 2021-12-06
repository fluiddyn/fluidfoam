import fluidfoam
from usefulFunctions import choose_simulation, find_directory
import os, sys
import subprocess

class fluidFoamPP(object):

    def __init__(self, path, simu=None, timeStep=None, structured=False):
        """
        path : str, reference path where simulations are stored. You may want to
            provide path if all your simulations are located inside path and
            subfolders of path. You can do it by modifying in the __init__
            path='/path/to/the/simulations/'
        simu : str, name of the simu that has to be loaded. If None, it will
            lists all existing simulation names in path and ask you to choose
        timeStep : str, timeStep to load. If None, load the last time step
        structured : bool, true if the mesh is structured
        """
        if simu == None:
            self.directory = choose_simulation(path)
            self.simu = self.directory.split("/")[-2]
        else:
            self.simu = simu
            self.directory = find_directory(path, simu)

        self.readOpenFoam(timeStep=timeStep, structured=structured)

    def readOpenFoam(self, timeStep=None, structured=True):
        """
        Reading SedFoam results
        Load the last time step saved of the simulation
        """
        if timeStep is None:
            # Use batch function foamListTimes to find the last time step
            # As it is a batch function, and not a python, we use a subprocess
            try:
                proc = subprocess.Popen(
                    ["foamListTimes", "-latestTime", "-case", self.directory],
                    stdout=subprocess.PIPE,
                )
            except:
                print("foamListTimes : command not found")
                print("Do you have load OpenFoam environement?")
                sys.exit(0)
            output = proc.stdout.read() #to obtain the output of function foamListTimes from the subprocess
            timeStep = output.decode().rstrip().split('\n')[0] #Some management on the output to obtain a number

        self.timeStep = timeStep

        #Read Mesh
        X, Y, Z = fluidfoam.readmesh(self.directory, structured=structured)
        self.x = X
        self.y = Y
        self.z = Z

        #List all variables saved at the required time step removing potential
        #directory that cannot be loaded
        self.variables = []
        basepath = self.directory+self.timeStep+'/'
        for fname in os.listdir(basepath):
            path = os.path.join(basepath, fname)
            if os.path.isdir(path):
                # skip directories
                continue
            else:
                self.variables.append(fname)


        for var in self.variables:
            #Load all variables and assign them as a variable of the object
            self.__setattr__(var, fluidfoam.readfield(self.directory,
                self.timeStep, var, structured=structured))

    def keys(self):
        """
        Print the name all variables loaded from simulation results
        """
        print("Loaded available variables are :")
        print(self.variables)

