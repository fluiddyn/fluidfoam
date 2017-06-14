"""    Module that allows to write 1D profiles in OpenFoam format
                  for boundary conditions imposition
"""
#
# ---------------- Module General Import and Declarations ---------------
#
import numpy as np
from fluidfoam.readof import typefield, readmesh, readfield 
#
# --------------------Module functions description----------------------
#

def create1dprofil(pathr, pathw, timeName, varList):
    """ Read 1D profiles at time timeName of pathr and write them in
        openfoam format in the 1d_profil folder of pathw.
    """
#
#        --------------------Reading part---------------------
#
    X, Y, Z = readmesh(pathr+'0/')
    dct = {'y': Y}
#    for i in range(len(varList)):
#         axarr[i].plot(fields[i], z)

    fileName = ''
    for var in varList:
        field = readfield(pathr, timeName, var)
        typevar = typefield(pathr, timeName, var)

        fileName = ''+var

        if typevar == 'scalar':
            filename = pathw+'1d_profil/'+fileName+'.xy'
            f = open(filename, "w")
            f.write('(\n')
            np.savetxt(f, np.c_[Y, field], fmt="(%s %s)")
            f.write(')\n')
            f.close()
        elif typevar == 'vector':
            for i in range(3):
                filename = pathw+'1d_profil/'+fileName+str(i)+'.xy'
                f = open(filename, "w")
                f.write('(\n')
                np.savetxt(f, np.c_[Y, field[i,:]], fmt="(%s %s)")
                f.write(')\n')
                f.close()
            print('Warning for pyof users : Ua=Ua0, Va=Ua2, Wa=Ua1\n')
        else:
            print('PROBLEM with varList input: Good input is for example :')
            print('fluidfoam.create1dprofile("/data/1dcompute/", "/data/1dcompute/", "750", [\'omega\',\'p\'])\n')
    status = 'create 1D profiles: done'
    return status


def read1dprofil(file_name):
    """
       :param file_name: the input file name
    """
    with open(file_name) as handle:

        size1d = len(handle.readlines())-2
        z=np.empty(size1d)
        field=np.empty(size1d)
        handle.seek(0)
        for line_num, line in enumerate(handle):
            if ((line_num!=0) & (line_num!=size1d+1)):
                line = line.replace(')','')
                line = line.replace('(','')
                cols = line.split()
                z[(line_num-1)] = cols[0]
                field[(line_num-1)] = cols[1]
        return z, field, size1d


def plot1dprofil(pathr, varList):
    import matplotlib.pyplot as plt

    z, field, size1d = read1dprofil(pathr+"/"+varList[0]+".xy")
    fields = np.empty([len(varList), size1d])
    fields[0] = field
    for i in range(len(varList)-1):
        z, field, size1d = read1dprofil(pathr+"/"+varList[i+1]+".xy")
        fields[i+1] = field

    f, axarr = plt.subplots(1, len(varList), sharey=True)
    for i in range(len(varList)):
        axarr[i].plot(fields[i], z)
        axarr[i].set_title(varList[i])
    plt.show()
    return



