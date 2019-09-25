"""Write, Read and Plot 1D input files for swak4foam
==========================================================================
This module allows to read OpenFoam output of one dimensional computation
and then write, plot and read input files for Boundary and Initial
Conditions imposition in 3D computation (via swak4foam):

.. autofunction:: create1dprofil

.. autofunction:: read1dprofil

.. autofunction:: plot1dprofil

"""
#
# ---------------- Module General Import and Declarations ---------------
#
import numpy as np
from fluidfoam.readof import typefield, readmesh, readfield


def create1dprofil_spe(pathw, waxis, var, varname, typevar):
    """
    This function provides way to write specific 1D profil (var array)
    in OpenFoam Format in the 1d_profil folder of pathw
    (for BC imposition in 2D or 3D case for example).

    Args:
        pathw: str\n
        waxis: numpy array\n
        var: numpy array\n
        varname: str\n
        typevar: str\n

    Returns:
        status: 'create specific 1D profil: done' if ok

    A way you might use me is:\n
        status = fluidfoam.create1dprofil_spe("pathw", z, epsilon,
        "epsilon", "scalar")

    Please note that the 1d_profil directory must be existing in the pathw
    directory
    """

    size1d = waxis.shape[0]
    filename = ''
    field = var
    filename = ''+varname

    if typevar == 'scalar':
        filename1 = pathw+'/1d_profil/'+filename+'.xy'
        f = open(filename1, "w")
        f.write('(\n')
        if field.shape==(1,):
            for cell in range(size1d):
                f.write('('+str(waxis[cell])+' '+str(field[0])+')\n')
        else:
            for cell in range(size1d):
                f.write('('+str(waxis[cell])+' '+str(field[cell])+')\n')
        f.write(')\n')
        f.close()
    elif typevar == 'vector':
        for i in range(3):
            filename1 = pathw+'/1d_profil/'+filename+str(i)+'.xy'
            f = open(filename1, "w")
            f.write('(\n')
            if field.shape==(3,1):
                for cell in range(size1d):
                    f.write('('+str(waxis[cell])+' '+str(field[i, 0])+')\n')
            else:
                for cell in range(size1d):
                    f.write('('+str(waxis[cell])+' '+str(field[i, cell])+')\n')
            f.write(')\n')
            f.close()
    else:
        print('PROBLEM with input: Good input is for example :')
        print('fluidfoam.create1dprofil_spe("/data/1dcompute/", Y, epsilon, "epsilon", "scalar")\n')
    status = 'create 1D profiles: done'
    return status


def create1dprofil(pathr, pathw, timename, axis ,varlist):
    """
    This function provides way to read 1D profiles at time timename of pathr
    and write them in OpenFoam Format in the 1d_profil folder of pathw
    (for BC imposition in 2D or 3D case for example).

    Args:
        pathr: str\n
        pathw: str\n
        timename: str\n
        axis: str\n
        varlist: list of str\n

    Returns:
        status: 'create 1D profiles: done' if ok

    A way you might use me is:\n
        status = fluidfoam.create1dprofil("path_of_case", "pathw", time, 'Y',
        ['Ua', 'Ub'])

    Please note that the 1d_profil directory must be existing in the pathw
    directory
    """

    X, Y, Z = readmesh(pathr)
    size1d = Y.shape[0]
    filename = ''
    for var in varlist:
        field = readfield(pathr, timename, var)
        typevar = typefield(pathr, timename, var)

        if axis=='X':
            waxis=X
        elif axis=='Y':
            waxis=Y
        elif axis=='Z':
            waxis=Z
        else:
            print('axis does not exist, please check input parameters\n')

        filename = ''+var

        if typevar == 'scalar':
            filename1 = pathw+'/1d_profil/'+filename+'.xy'
            f = open(filename1, "w")
            f.write('(\n')
            if field.shape==(1,):
                for cell in range(size1d):
                    f.write('('+str(waxis[cell])+' '+str(field[0])+')\n')
            else:
                for cell in range(size1d):
                    f.write('('+str(waxis[cell])+' '+str(field[cell])+')\n')
#            np.savetxt(f, np.c_[Y, field], fmt="(%s %s)")
            f.write(')\n')
            f.close()
        elif typevar == 'vector':
            for i in range(3):
                filename1 = pathw+'/1d_profil/'+filename+str(i)+'.xy'
                f = open(filename1, "w")
                f.write('(\n')
                if field.shape==(3,1):
                    for cell in range(size1d):
                        f.write('('+str(waxis[cell])+' '+str(field[i, 0])+')\n')
                else:
                    for cell in range(size1d):
                        f.write('('+str(waxis[cell])+' '+str(field[i, cell])+')\n')
                f.write(')\n')
                f.close()
            print('Warning for pyof users : Ua=Ua0, Va=Ua2, Wa=Ua1\n')
        else:
            print('PROBLEM with varlist input: Good input is for example :')
            print('fluidfoam.create1dprofil("/data/1dcompute/", "/data/1dcompute/", "750", "Y",[\'omega\',\'p\'])\n')
    status = 'create 1D profiles: done'
    return status


def read1dprofil(file_name):
    """This function provides way to read and return 1D profil created by the
    create1dprofil function. file_name can be a complete path.

    Args:
        filename: str

    Returns:
        z: 1d mesh corresponding to 1d profil\n
        field: scalar value of the field specified via filename\n
        size1d: size of the 1d profil

    A way you might use me is:\n
        z, a, size1d = fluidfoam.read1dprofil("path_of_case/1d_profil/a.xy")
    """

    with open(file_name) as handle:

        size1d = len(handle.readlines())-2
        z = np.empty(size1d)
        field = np.empty(size1d)
        handle.seek(0)
        for line_num, line in enumerate(handle):
            if ((line_num != 0) & (line_num != size1d+1)):
                line = line.replace(')', '')
                line = line.replace('(', '')
                cols = line.split()
                z[(line_num-1)] = cols[0]
                field[(line_num-1)] = cols[1]
        return z, field, size1d


def plot1dprofil(pathr, varlist):
    """This function provides way to plot 1D profiles created by the
    create1dprofil function.

    Args:
        pathr: str (must be the full path of the 1d_profil directory)\n
        varlist: list of str

    A way you might use me is:\n
        fluidfoam.plot1dprofil("path_of_case/1d_profil", ['Ua', 'Ub', 'alpha'])
    """

    import matplotlib.pyplot as plt

    z, field, size1d = read1dprofil(pathr+"/"+varlist[0]+".xy")
    fields = np.empty([len(varlist), size1d])
    fields[0] = field
    for i in range(len(varlist)-1):
        z, field, size1d = read1dprofil(pathr+"/"+varlist[i+1]+".xy")
        fields[i+1] = field

    dummy, axarr = plt.subplots(1, len(varlist), sharey=True)
    for i, dummy in enumerate(varlist):
        axarr[i].plot(fields[i], z)
        axarr[i].set_title(varlist[i])
    plt.show()
    return
