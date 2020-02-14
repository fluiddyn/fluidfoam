"""Read OpenFoam PostProcessing Files for Python
=======================================================================
This module provides functions to list and read OpenFoam PostProcessing Files:

.. autofunction:: readforce
.. autofunction:: readprobes
"""
import os
import numpy as np


def _find_latesttime(path):
    dir_list = os.listdir(path)
    time_list = []

    for directory in dir_list:
        try:
            float(directory)
            time_list.append(directory)
        except:
            pass
    time_list.sort(key=float)
    return time_list[-1]


def varinforce():
    """ return the var included in postProcessing force files."""

    return [
        "T",
        "Fpx",
        "Fpy",
        "Fpz",
        "Fvx",
        "Fvy",
        "Fvz",
        "Fpox",
        "Fpoy",
        "Fpoz",
        "Mpx",
        "Mpy",
        "Mpz",
        "Mvx",
        "Mvy",
        "Mvz",
        "Mpox",
        "Mpoy",
        "Mpoz",
    ]


def readforce(path, namepatch="forces", time_name="0", name="forces"):
    """ read the data contained in the force file .
    create the forces variables in the Forcesfile object

    Args:
        path: str\n
        time_name: str ('latestTime' and 'mergeTime' are supported)\n
        name: str

    Returns:
        array: array of force field; size of the array is the size of the
        time

    A way you might use me is:\n
        force = readforce('path_of_OpenFoam_case', '0', 'forces')

    It will create and fill the force variables:\n
        ['T','Fpx','Fpy','Fpz','Fvx','Fvy','Fvz'
        ,'Fpox','Fpoy','Fpoz','Mpx','Mpy','Mpz'
        ,'Mvx','Mvy','Mvz','Mpox','Mpoy','Mpoz']
    """

    path_namepatch = os.path.join(path, "postProcessing", namepatch)
    if time_name is "latestTime":
        time_name = _find_latesttime(path_namepatch)
    elif time_name is "mergeTime":
        time_list = []
        dir_list = os.listdir(path + "/postProcessing/" + namepatch)
        for directory in dir_list:
            try:
                float(directory)
                time_list.append(directory)
            except:
                pass
        time_list.sort(key=float)
        time_list = np.array(time_list)
        for timename in time_list:
            tab = readforce(path, namepatch, timename, name)
            if "tab_merge" in locals():
                for jj in range(np.size(tab[:, 0])):
                    if tab[jj, 0] > tab_merge[-1, 0]:
                        break
                    else:
                        continue
                if jj + 1 < np.size(tab[:, 0]):
                    tab_merge = np.concatenate([tab_merge, tab[jj:, :]])
            else:
                tab_merge = tab
        return tab_merge

    with open(os.path.join(path_namepatch, time_name, name + ".dat"), "rb") as f:
        content = f.read()
    data = content.split(b"\n")
    j = 0
    header = True
    for dummy, line in enumerate(data[:-1]):
        if "#".encode() in line:
            j += 1
        elif "#".encode() not in line and header == True:
            header = False
            line = line.replace(b"(", b"")
            line = line.replace(b")", b"")
            line = line.split()
            tab = np.zeros([len(data) - j - 1, len(line)], dtype=float)
            j = 0
            tab[j, :] = np.array(line, dtype=float)
        else:
            j += 1
            line = line.replace(b"(", b"")
            line = line.replace(b")", b"")
            line = line.split()
            tab[j, :] = np.array(line, dtype=float)
    return tab


def readprobes(path, probes_name="probes", time_name="0", name="U"):
    """ read the data contained in the force file .
        create the forces variables in the Forcesfile object

        Args:
            path: str\n
            probes_name: str\n
            time_name: str ('latestTime' and 'mergeTime' are supported)\n
            name: str

        Returns:
            array: array of time values and array of probes data;

        A way you might use me is:\n
            probe_data = read('path_of_OpenFoam_case', '0', 'probes', 'U')

    """

    path_probes_name = os.path.join(path, "postProcessing", probes_name)
    if time_name is "latestTime":
        time_name = _find_latesttime(path_probes_name)
    elif time_name is "mergeTime":
        time_list = []
        dir_list = os.listdir(path + "/postProcessing/" + probes_name)
        for directory in dir_list:
            try:
                float(directory)
                time_list.append(directory)
            except:
                pass
        time_list.sort(key=float)
        time_list = np.array(time_list)
        for timename in time_list:
            time_vect, tab = readprobes(path, probes_name, timename, name)
            if "tab_merge" in locals():
                for jj in range(np.size(time_vect[:])):
                    if time_vect[jj] > timevect_merge[-1]:
                        break
                    else:
                        continue
                if jj + 1 < np.size(time_vect[:]):
                    timevect_merge = np.concatenate([timevect_merge, time_vect[jj:]])
                    tab_merge = np.concatenate([tab_merge, tab[jj:, :]])
            else:
                timevect_merge = time_vect
                tab_merge = tab
        return timevect_merge, tab_merge

    with open(os.path.join(path_probes_name, time_name, name), "rb") as f:
        content = f.readlines()
    j = 0
    header = True
    for dummy, line in enumerate(content):
        if "#".encode() in line:
            j += 1
        elif "#".encode() not in line and header:
            header = False
            line = line.replace(b")", b"")
            line = line.split(b"(")
            try:
                dim = len(line[1].split())
            except IndexError:
                dim = 1
                line = line[0].split()
            time_vect = np.zeros(len(content) - j)
            time_vect[0] = line[0]
            tab = np.zeros([len(content) - j, len(line) - 1, dim], dtype=float)
            print(
                "Reading file "
                + os.path.join(
                    path, "postProcessing", probes_name, time_name, name
                )
            )
            print(
                str(len(line) - 1)
                + " probes over "
                + str(len(tab[:, 0, 0]))
                + " timesteps"
            )
            for k, probedata in enumerate(line[1:]):
                values = probedata.split()
                for l, vect in enumerate(values):
                    tab[0, k, l] = np.array(vect, dtype=float)
            j = 0
        else:
            j += 1
            line = line.replace(b")", b"")
            line = line.split(b"(")
            try:
                time_vect[j] = line[0]
            except ValueError:
                line = line[0].split()
                time_vect[j] = line[0]
            for k, probedata in enumerate(line[1:]):
                values = probedata.split()
                for l, vect in enumerate(values):
                    tab[j, k, l] = np.array(vect, dtype=float)
    return time_vect, tab
