"""Read OpenFoam PostProcessing Files for Python
=======================================================================
This module provides functions to list and read OpenFoam PostProcessing Files:

.. autofunction:: readforce
.. autofunction:: readprobes
"""
import os
import numpy as np 

def varinforce():
    """ return the var included in postProcessing force files."""

    return ['T', 'Fpx', 'Fpy', 'Fpz', 'Fvx', 'Fvy', 'Fvz', 'Fpox',
                 'Fpoy', 'Fpoz', 'Mpx', 'Mpy', 'Mpz', 'Mvx', 'Mvy', 'Mvz',
                 'Mpox','Mpoy','Mpoz']

def readforce(path, namepatch='forces', time_name='0', name='forces'):
    """ read the data contained in the force file .
    create the forces variables in the Forcesfile object

    Args:
        path: str\n
        time_name: str\n
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

    with open(os.path.join(path, 'postProcessing', namepatch, time_name,
                           name+'.dat'),'rb') as f:
        content = f.read()
    data = content.split(b'\n')
    j = 0
    header = True
    for i, line in enumerate(data[:-1]):
        if '#'.encode() in line:
            j += 1
        elif '#'.encode() not in line and header==True:
            header = False
            line = line.replace(b'(', b'')
            line = line.replace(b')', b'')
            line = line.split()
            tab = np.zeros([len(data)-j-1, len(line)], dtype=float)
            j = 0
            tab[j, :] = np.array(line, dtype=float)
        else:
            j += 1
            line = line.replace(b'(', b'')
            line = line.replace(b')', b'')
            line = line.split()
            tab[j, :] = np.array(line, dtype=float)
    return tab


def readprobes(path, probes_name='probes', time_name='0', name='U'):
    """ read the data contained in the force file .
        create the forces variables in the Forcesfile object

        Args:
            path: str\n
            probes_name: str\n
            time_name: str\n
            name: str

        Returns:
            array: array of time values and array of probes data;

        A way you might use me is:\n
            probe_data = read('path_of_OpenFoam_case', '0', 'probes', 'U')

    """
    with open(os.path.join(path, 'postProcessing', probes_name, time_name,
                           name), 'rb') as f:
        content = f.readlines()
    j = 0
    header = True
    for i, line in enumerate(content):
        if '#'.encode() in line:
            j += 1
        elif '#'.encode() not in line and header == True:
            header = False
            line = line.replace(b')', b'')
            line = line.split(b'(')
            dim = len(line[1].split())
            time_vect = np.zeros(len(content)-j)
            time_vect[0] = line[0]
            tab = np.zeros([len(content)-j, len(line)-1, dim],
                           dtype=float)
            print('Reading file ' + os.path.join(path, 'postProcessing',
                                                 probes_name, time_name, name))
            print(str(len(line)-1) + ' probes over ' + str(len(tab[:, 0, 0])) +
                  ' timesteps')
            for k, probedata in enumerate(line[1:]):
                values = probedata.split()
                for l, vect in enumerate(values):
                    tab[0, k, l] = np.array(vect, dtype=float)
            j = 0
        else:
            j += 1
            line = line.replace(b')', b'')
            line = line.split(b'(')
            time_vect[j] = line[0]
            for k, probedata in enumerate(line[1:]):
                values = probedata.split()
                for l, vect in enumerate(values):
                    tab[j, k, l] = np.array(vect, dtype=float)
    return time_vect, tab
