import os

class Error(Exception):
    pass

class DirectorySimuError(Error):
    def __init__(self, simu):
        super(DirectorySimuError,self).__init__(
                "No directory found for simulation named {}".format(simu))

def find_directory(path, simu):
    """
    Look for the directory of simu in all the sub directories of path. If several
    directories are found, the program asks which directory is the good one.
    path : string, reference path where all the simulations are located.
    directory : string, look for this directory in path and sub directories of path
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


def choose_simulation(path):
    """
    Make a list of all the directories containing a simulation located in path.
    Ask the user which simulation to load
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
