"""Class to load all data saved at timeStep of an openFoam simulation
=====================================================================

.. autoclass:: OpenFoamSimu

.. automethod:: OpenFoamSimu.keys

.. automethod:: OpenFoamSimu.readopenfoam

"""

import os, sys
import subprocess
from fluidfoam import readmesh, readfield

class Error(Exception):
    pass

class DirectorySimuError(Error):
    def __init__(self, simu):
        super(DirectorySimuError,self).__init__(
                "No directory found for simulation named {}".format(simu))

class OpenFoamSimu(object):
    """
    Class to load all data saved at timeStep of an openFoam simulation

    Args:
        path: str, reference path where simulations are stored.\n
            You may want to provide path if all your simulations are located
            inside path and subfolders of path. You can do it by modifying
            in the __init__ path='/path/to/the/simulations/'\n
        simu: str, name of the simu that has to be loaded.\n
            If simu=None, it will lists all existing simulation names in path
            and ask you to choose.\n
        timeStep: str, timeStep to load. If None, load the last time step\n
        structured: bool, true if the mesh is structured
    """

    def __init__(self, path, simu=None, timeStep=None, structured=False):

        if simu == None:
            self.directory = self._choose_simulation(path)
            self.simu = self.directory.split("/")[-2]
        else:
            self.simu = simu
            self.directory = self._find_directory(path, simu)

        self.readopenfoam(timeStep=timeStep, structured=structured)

    def readopenfoam(self, timeStep=None, structured=True):
        """
        Reading SedFoam results
        Load the last time step saved of the simulation

        Args:
            timeStep : str or int, timeStep to load. If None, load the last time step\n
            structured : bool, true if the mesh is structured
        """
        if timeStep is None:
            dir_list = os.listdir(self.directory)
            time_list = []

            for directory in dir_list:
                try:
                    float(directory)
                    time_list.append(directory)
                except:
                    pass
            time_list.sort(key=float)
            timeStep = time_list[-1]

        elif type(timeStep) is int:
            #timeStep should be in a str format
            timeStep = str(timeStep)

        self.timeStep = timeStep

        #Read Mesh
        X, Y, Z = readmesh(self.directory, structured=structured)
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
            self.__setattr__(var, readfield(path=self.directory,
                time_name=self.timeStep, name=var, structured=structured))

    def keys(self):
        """
        Print the name of all variables loaded from simulation results
        """
        print("Loaded available variables are :")
        print(self.variables)

    def _choose_simulation(self, path):
        """
        Make a list of all directories located in path containing a simulation.
        Ask the user which simulation to load

        Args:
            path : str, reference path where simulations are stored.
        """
        directories = []
        subDirectories = [x[0] for x in os.walk(path)]

        for f in subDirectories:
            #A directory is detected to be a simulation if it contains a 0_org/ folder
            if f + "/constant" in subDirectories:
                directories.append(f)

        # If no directories found
        if len(directories) == 0:
            raise DirectorySimuError(path)

        for i in range(len(directories)):
            print("{} : {}".format(i, directories[i]))
        chosenSimulation = -1
        while type(chosenSimulation) is not int or (
                chosenSimulation < 0 or chosenSimulation > len(directories) - 1):
            chosenSimulation = int( input(
                "Please, choose one simulation ! (integer between {} and {})".format(
                    0, len(directories) - 1))
            )
        directory = directories[chosenSimulation]

        return directory + "/"

    def _find_directory(self, path, simu):
        """
        Look for the directory of simu in all the sub directories of path. If several
        directories are found, the program asks which directory is the good one.

        Args:
            path : str, reference path where simulations are stored.
            simu : str, name of the simu that has to be loaded. If None, it will
                lists all existing simulation names in path and ask you to choose
        """
        directories = []
        subDirectories = [x[0] for x in os.walk(path)]

        for f in subDirectories:
            if f.endswith(simu):
                directories.append(f)

        # If no directories found
        if len(directories) == 0:
            raise DirectorySimuError(simu)

        # If several directories found, ask for the one wanted
        elif len(directories) > 1:
            print("The following simulations has been found :")
            for i in range(len(directories)):
                print("{} : {}".format(i, directories[i]))
            chosenSimulation = -1
            while type(chosenSimulation) is not int or (
                    chosenSimulation < 0 or chosenSimulation > len(directories) - 1):
                chosenSimulation = int(input(
                    "Please, choose one simulation ! (integer between {} and {})".format(
                        0, len(directories) - 1)
                    )
                )
            directory = directories[chosenSimulation]

        else:
            directory = directories[0]

        return directory + "/"


if __name__ == "__main__":

    simu = "box"
    timeStep = "4"

    for d in dirs:
        rep = os.path.join(os.path.dirname(__file__), "../output_samples")

        mySimu = OpenFoamSimu(path=rep, simu=simu, timeStep=timeStep, structured=True)

        mySimu.keys()

        mySimu.U

