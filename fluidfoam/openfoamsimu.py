"""Class to load all data saved at timeStep of an openFoam simulation
=====================================================================

.. autoclass:: OpenFoamSimu

.. automethod:: OpenFoamSimu.keys

.. automethod:: OpenFoamSimu.readopenfoam

"""

import os
import logging
import numpy as np
from fluidfoam import readmesh, OpenFoamFile


logger = logging.getLogger("fluidfoam.openfoamsimu")


class Error(Exception):
    pass


class DirectorySimuError(Error):
    def __init__(self, simu):
        super(DirectorySimuError, self).__init__(
            "No directory found for simulation named {}".format(simu)
        )


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
        structured: bool, true if the mesh is structured\n
        dataToLoad: list of str, list containing the name of the variables
            to read and load. If None, read and load all saved variables.
    """

    def __init__(
        self,
        path: str | None = None,
        simu: str | None = None,
        timeStep: str | int | None = None,
        structured: bool = False,
        dataToLoad: list[str] | None = None,
        precision: int = 15,
        order: str = "F",
    ) -> None:

        if path == None and simu == None:
            # If nothing if given, consider the current directory as the
            # simulation to load
            self.directory = os.getcwd() + "/"
            self.simu = os.getcwd().split("/")[-1]
        elif simu == None:
            # If only path is provided, consider all subfolders as possible
            # simulations to load
            self.directory = self._choose_simulation(path)
            self.simu = self.directory.split("/")[-2]
        else:
            # If path and simu are provided, consider the given directory
            # as the simulation to load
            self.simu = simu
            if path.endswith("/") is False:
                path += "/"
            self.directory = path + simu
            if self.directory.endswith("/") is False:
                self.directory += "/"

        self.readmesh(
            timeStep=timeStep,
            structured=structured,
            precision=precision,
            order=order,
        )

        self.readopenfoam(
            timeStep=timeStep,
            structured=structured,
            dataToLoad=dataToLoad,
            precision=precision,
            order=order,
        )

    def readmesh(
        self,
        timeStep: str | int | None = None,
        structured: bool = False,
        precision: int = 15,
        order: str = "F",
    ) -> None:

        if timeStep is None:
            dir_list = os.listdir(self.directory)
            time_list = []

            for directory in dir_list:
                try:
                    float(directory)
                    time_list.append(directory)
                except ValueError:
                    pass
            time_list.sort(key=float)
            timeStep = time_list[-1]

        elif type(timeStep) is int:
            # timeStep should be in a str format
            timeStep = str(timeStep)

        self.timeStep = timeStep

        # Check if cell center position is written in the output directory
        field = None
        try:
            field = OpenFoamFile(
                path=self.directory,
                time_name=self.timeStep,
                name="C",
                structured=False,
                precision=precision,
                order=order,
            )
            # a uniform C field carries no cell position, fall back to readmesh
            if field.uniform:
                field = None
        except FileNotFoundError:
            pass
        if field is not None:
            values = field.values
            shape = (3, values.size // 3)
            values = np.reshape(values, shape, order=order)
            X, Y, Z = values[0], values[1], values[2]
        else:
            X, Y, Z = readmesh(
                self.directory,
                structured=structured,
                precision=precision,
                order=order,
            )
        self.x = X
        self.y = Y
        self.z = Z
        if structured:
            nx = np.unique(X).size
            ny = np.unique(Y).size
            nz = np.unique(Z).size
            self.ind = np.array(range(nx * ny * nz))
            self.shape = (nx, ny, nz)
            # reshape the coordinates consistently with the fields loaded
            # by readopenfoam
            self.x = np.reshape(self.x, self.shape, order=order)
            self.y = np.reshape(self.y, self.shape, order=order)
            self.z = np.reshape(self.z, self.shape, order=order)

    def readopenfoam(
        self,
        timeStep: str | int | None = None,
        structured: bool = False,
        dataToLoad: list[str] | None = None,
        precision: int = 15,
        order: str = "F",
    ) -> None:
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
                except ValueError:
                    pass
            time_list.sort(key=float)
            timeStep = time_list[-1]

        elif type(timeStep) is int:
            # timeStep should be in a str format
            timeStep = str(timeStep)

        self.timeStep = timeStep

        # List all variables saved at the required time step removing potential
        # directory that cannot be loaded
        if dataToLoad is None:
            self.variables = []
            basepath = self.directory + self.timeStep + "/"
            for fname in os.listdir(basepath):
                path = os.path.join(basepath, fname)
                if os.path.isdir(path):
                    # skip directories
                    continue
                else:
                    self.variables.append(fname)

            # Remove C, Cx, Cy and Cz if present
            var_to_remove = ["C", "Cx", "Cy", "Cz"]
            for var in var_to_remove:
                if var in self.variables:
                    self.variables.remove(var)
        else:
            self.variables = dataToLoad

        for var in self.variables:
            # Load all variables and assign them as a variable of the object
            field = OpenFoamFile(
                path=self.directory,
                time_name=self.timeStep,
                name=var,
                structured=False,
                precision=precision,
                order=order,
            )
            values = field.values

            if field.type_data == "scalar":
                if structured and not field.uniform:
                    try:
                        values = np.reshape(
                            values[self.ind], self.shape, order=order
                        )
                    except (IndexError, ValueError) as error:
                        logger.warning(
                            "Variable %s could not be loaded: %s", var, error
                        )
                        self.variables.remove(var)
                        continue
            elif field.type_data == "vector":
                shape = (3, values.size // 3)
                values = np.reshape(values, shape, order=order)
                if structured and not field.uniform:
                    try:
                        values[0:3, :] = values[0:3, self.ind]
                        shape = (3,) + tuple(self.shape)
                        values = np.reshape(values, shape, order=order)
                    except (IndexError, ValueError) as error:
                        logger.warning(
                            "Variable %s could not be loaded: %s", var, error
                        )
                        self.variables.remove(var)
                        continue
            elif field.type_data == "symmtensor":
                shape = (6, values.size // 6)
                values = np.reshape(values, shape, order=order)
                if structured and not field.uniform:
                    try:
                        values[0:6, :] = values[0:6, self.ind]
                        shape = (6,) + tuple(self.shape)
                        values = np.reshape(values, shape, order=order)
                    except (IndexError, ValueError) as error:
                        logger.warning(
                            "Variable %s could not be loaded: %s", var, error
                        )
                        self.variables.remove(var)
                        continue
            elif field.type_data == "tensor":
                shape = (9, values.size // 9)
                values = np.reshape(values, shape, order=order)
                if structured and not field.uniform:
                    try:
                        values[0:9, :] = values[0:9, self.ind]
                        shape = (9,) + tuple(self.shape)
                        values = np.reshape(values, shape, order=order)
                    except (IndexError, ValueError) as error:
                        logger.warning(
                            "Variable %s could not be loaded: %s", var, error
                        )
                        self.variables.remove(var)
                        continue
            self.__setattr__(var.replace(".", "_"), values)

    def keys(self) -> None:
        """
        Print the name of all variables loaded from simulation results
        """
        print("Loaded available variables are :")
        print(self.variables)

    def _choose_simulation(self, path: str) -> str:
        """
        Make a list of all directories located in path containing a simulation.
        Ask the user which simulation to load

        Args:
            path : str, reference path where simulations are stored.
        """
        directories = []
        subDirectories = [x[0] for x in os.walk(path)]

        for f in subDirectories:
            # A directory is detected to be a simulation if it contains a 0_org/ folder
            if f + "/constant" in subDirectories:
                directories.append(f)

        # If no directories found
        if len(directories) == 0:
            raise DirectorySimuError(path)

        for i in range(len(directories)):
            print("{} : {}".format(i, directories[i]))
        chosenSimulation = -1
        while type(chosenSimulation) is not int or (
            chosenSimulation < 0 or chosenSimulation > len(directories) - 1
        ):
            chosenSimulation = int(
                input(
                    "Please, choose one simulation ! (integer between {} and {})".format(
                        0, len(directories) - 1
                    )
                )
            )
        directory = directories[chosenSimulation]

        return directory + "/"

    def _find_directory(self, path: str, simu: str) -> str:
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
                chosenSimulation < 0 or chosenSimulation > len(directories) - 1
            ):
                chosenSimulation = int(
                    input(
                        "Please, choose one simulation ! (integer between {} and {})".format(
                            0, len(directories) - 1
                        )
                    )
                )
            directory = directories[chosenSimulation]

        else:
            directory = directories[0]

        return directory + "/"


if __name__ == "__main__":

    rep = os.path.join(os.path.dirname(__file__), "../output_samples")
    simu = "box"
    timeStep = "4"

    mySimu = OpenFoamSimu(
        path=rep, simu=simu, timeStep=timeStep, structured=True
    )

    mySimu.keys()

    mySimu.U
