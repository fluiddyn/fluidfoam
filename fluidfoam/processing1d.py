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
    filename = ""
    field = var
    filename = "" + varname

    if typevar == "scalar":
        filename1 = pathw + "/1d_profil/" + filename + ".xy"
        f = open(filename1, "w")
        f.write("(\n")
        if field.shape == (1,):
            for cell in range(size1d):
                f.write("(" + str(waxis[cell]) + " " + str(field[0]) + ")\n")
        else:
            for cell in range(size1d):
                f.write("(" + str(waxis[cell]) + " " + str(field[cell]) + ")\n")
        f.write(")\n")
        f.close()
    elif typevar == "vector":
        for i in range(3):
            filename1 = pathw + "/1d_profil/" + filename + str(i) + ".xy"
            f = open(filename1, "w")
            f.write("(\n")
            if field.shape == (3, 1):
                for cell in range(size1d):
                    f.write(
                        "(" + str(waxis[cell]) + " " + str(field[i, 0]) + ")\n"
                    )
            else:
                for cell in range(size1d):
                    f.write(
                        "(" + str(waxis[cell]) + " " + str(field[i, cell]) + ")\n"
                    )
            f.write(")\n")
            f.close()
    else:
        print("PROBLEM with input: Good input is for example :")
        print(
            'fluidfoam.create1dprofil_spe("/data/1dcompute/", Y, epsilon, "epsilon", "scalar")\n'
        )
    status = "create 1D profiles: done"
    return status


def create1dprofil(pathr, pathw, timename, axis, varlist):
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
    filename = ""
    for var in varlist:
        field = readfield(pathr, timename, var)
        typevar = typefield(pathr, timename, var)

        if axis == "X":
            waxis = X
        elif axis == "Y":
            waxis = Y
        elif axis == "Z":
            waxis = Z
        else:
            print("axis does not exist, please check input parameters\n")

        filename = "" + var

        if typevar == "scalar":
            filename1 = pathw + "/1d_profil/" + filename + ".xy"
            f = open(filename1, "w")
            f.write("(\n")
            if field.shape == (1,):
                for cell in range(size1d):
                    f.write("(" + str(waxis[cell]) + " " + str(field[0]) + ")\n")
            else:
                for cell in range(size1d):
                    f.write(
                        "(" + str(waxis[cell]) + " " + str(field[cell]) + ")\n"
                    )
            #            np.savetxt(f, np.c_[Y, field], fmt="(%s %s)")
            f.write(")\n")
            f.close()
        elif typevar == "vector":
            for i in range(3):
                filename1 = pathw + "/1d_profil/" + filename + str(i) + ".xy"
                f = open(filename1, "w")
                f.write("(\n")
                if field.shape == (3, 1):
                    for cell in range(size1d):
                        f.write(
                            "("
                            + str(waxis[cell])
                            + " "
                            + str(field[i, 0])
                            + ")\n"
                        )
                else:
                    for cell in range(size1d):
                        f.write(
                            "("
                            + str(waxis[cell])
                            + " "
                            + str(field[i, cell])
                            + ")\n"
                        )
                f.write(")\n")
                f.close()
            print("Warning for pyof users : Ua=Ua0, Va=Ua2, Wa=Ua1\n")
        else:
            print("PROBLEM with varlist input: Good input is for example :")
            print(
                'fluidfoam.create1dprofil("/data/1dcompute/", "/data/1dcompute/", "750", "Y",[\'omega\',\'p\'])\n'
            )
    status = "create 1D profiles: done"
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

        size1d = len(handle.readlines()) - 2
        z = np.empty(size1d)
        field = np.empty(size1d)
        handle.seek(0)
        for line_num, line in enumerate(handle):
            if (line_num != 0) & (line_num != size1d + 1):
                line = line.replace(")", "")
                line = line.replace("(", "")
                cols = line.split()
                z[(line_num - 1)] = cols[0]
                field[(line_num - 1)] = cols[1]
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

    z, field, size1d = read1dprofil(pathr + "/" + varlist[0] + ".xy")
    fields = np.empty([len(varlist), size1d])
    fields[0] = field
    for i in range(len(varlist) - 1):
        z, field, size1d = read1dprofil(pathr + "/" + varlist[i + 1] + ".xy")
        fields[i + 1] = field

    dummy, axarr = plt.subplots(1, len(varlist), sharey=True)
    for i, dummy in enumerate(varlist):
        axarr[i].plot(fields[i], z)
        axarr[i].set_title(varlist[i])
    plt.show()
    return

def create1dprofilDFSEM(pathr, pathw, boundaryname, timename, axis, 
                         Uname,kname,omeganame,Rname,axisW):
    """
    This function provides way to read 1D profiles at time timename of pathr
    and write them in OpenFoam Format in the 1d_profil folder of pathw
    (for BC imposition in 2D or 3D case for example).

    Args:
        pathr: str\n
        pathw: str\n
        boundaryname: str\n
        timename: str\n
        axis: str\n 
        Uname : str\n
        kname : str \n
        omeganame : str \n
        Rname : str \n
        axisW : str\n 

    Returns:
        status: 'create 1D profiles for DFSEM: done' if ok

    A way you might use me is:\n
        status = fluidfoam.create1dprofil("path_of_case", "pathw", time, 'Y',
                                           Uname,kname,omeganame,Rname)

    Please note that the boundaryname directory must be existing in the pathw
    directory
    """

    X, Y, Z = readmesh(pathr)
    size1d = Y.shape[0]
    filename = ""
 
    filename1 = pathw + "/constant/boundaryData/" + boundaryname + "/points"
    f = open(filename1, "w")
    f.write("(\n")
    for cell in range(size1d):
          if axisW == axis:
                f.write(
                 "(" + str(X[cell]) + " " + str(Y[cell]) + " " 
                     + str(Z[cell]) + ")\n"
                )
          elif np.logical_and(axis=='Y' , axisW == 'Z'):
                f.write(
                 "(" + str(X[cell]) + " " + str(Z[cell]) + " " 
                     + str(Y[cell]) + ")\n"
                )
    f.write(")\n")
    f.close()
    
    U = readfield(pathr, timename, Uname)
    k = readfield(pathr, timename, kname)
    omega = readfield(pathr, timename,omeganame)
    R = readfield(pathr, timename, Rname)
    
    filename1 = pathw + "/constant/boundaryData/" + boundaryname + "/0/L"
    
    L = np.sqrt(k)/omega
    for cell in range(size1d):
          L[cell] = min(L[cell],0.41*(np.max(Y)-Y[cell]))
    f = open(filename1, "w")
    f.write("(\n")
    for cell in range(size1d):
          f.write(str(L[cell])+"\n")
    f.write(")\n")
    f.close()
    
    filename1 = pathw + "/constant/boundaryData/" + boundaryname + "/0/U"
    #U = varlist[0]
    f = open(filename1, "w")
    f.write("(\n")
    for cell in range(size1d):
          if axisW == axis:
                f.write(
                  "("
                   + str(U[0, cell])
                   + " "
                   + str(U[1, cell])
                   + " "
                   + str(U[2, cell])
                   + ")\n"
                 )
          elif np.logical_and(axis=='Y' , axisW == 'Z'):
                f.write(
                  "("
                   + str(U[0, cell])
                   + " "
                   + str(U[2, cell])
                   + " "
                   + str(U[1, cell])
                   + ")\n"
                 )
          else:
                print("please implement this option")
                break
    f.write(")\n")
    f.close()
    
    filename1 = pathw + "/constant/boundaryData/" + boundaryname + "/0/R"
    #R = varlist[3]
    f = open(filename1, "w")
    f.write("(\n")
    for cell in range(size1d):
          if axisW == axis:
                #0:XX , 1:XY , 2:XZ , 3:YY , 4:YZ , 5:ZZ
                #0:XX , 1:XY , 2:XZ , 3:YX , 4:YY , 5:YZ , 6:ZX , 7:ZY , 8:ZZ
                f.write(
                  "("
                   + str(R[0, cell])
                   + " "
                   + str(R[1, cell])
                   + " "
                   + str(R[2, cell])
                   + " "
                   + str(R[3, cell])
                   + " "
                   + str(R[4, cell])
                   + " "
                   + str(R[5, cell])
                   + ")\n"
                 )
          elif np.logical_and(axis=='Y' , axisW == 'Z'):
                #0:XX , 1:XY , 2:XZ , 3:YY , 4:YZ , 5:ZZ
                #0:XX , 1:XY , 2:XZ , 3:YX , 4:YY , 5:YZ , 6:ZX , 7:ZY , 8:ZZ
                f.write(
                  "("
                   + str(R[0, cell])
                   + " "
                   + str(R[2, cell])
                   + " "
                   + str(R[1, cell])
                   + " "
                   + str(R[3, cell])
                   + " "
                   + str(R[4, cell])
                   + " "
                   + str(R[5, cell])
                   + ")\n"
                 )
    f.write(")\n")
    f.close()

    status = "create 1D profiles DFSEM: done"
    return status

def read1dprofilDFSEM(file_name, boundary_name, time_name, axis):
    """This function provides way to read and return 1D profil created by the
    create1dprofilDFSEM function. file_name can be a complete path.

    Args:
        file_name: str
        boundary_name: str
        time_name: str
        axis: str

    Returns:
        coord: 1d mesh corresponding to 1d profil\n
        U: Velocity field profile (x-component)\n
        L: Turbulent length scale \n
        R: Reynolds shear stress \n
        size1d: size of the 1d profil

    A way you might use me is:\n
        pos, U, k, omega, R, size1d = fluidfoam.read1dprofilDFSEM("path_of_case","boundaryName")
    """
    import os
    # read points
    basepath = os.path.join(file_name, 'constant/boundaryData', boundary_name)
    file_namep = os.path.join(basepath, 'points')
    if axis == "X":
        index = 0
    elif axis == "Y":
        index = 1
    elif axis == "Z":
        index = 2
        
    with open(file_namep) as handle:

        size1d = len(handle.readlines()) - 2
        coord = np.empty(size1d)
        handle.seek(0)
        for line_num, line in enumerate(handle):
            if (line_num != 0) & (line_num != size1d + 1):
                line = line.replace(")", "")
                line = line.replace("(", "")
                cols = line.split()
                coord[(line_num - 1)] = cols[index]
    # read U
    file_nameU = os.path.join(basepath, time_name, 'U')
    with open(file_nameU) as handle:

        size1d = len(handle.readlines()) - 2
        U = np.empty(size1d)
        handle.seek(0)
        for line_num, line in enumerate(handle):
            if (line_num != 0) & (line_num != size1d + 1):
                line = line.replace(")", "")
                line = line.replace("(", "")
                cols = line.split()
                U[(line_num - 1)] = cols[0]
    # read L
    file_nameL = os.path.join(basepath, time_name, 'L')
    with open(file_nameL) as handle:

        size1d = len(handle.readlines()) - 2
        L = np.empty(size1d)
        handle.seek(0)
        for line_num, line in enumerate(handle):
            if (line_num != 0) & (line_num != size1d + 1):
                line = line.replace(")", "")
                line = line.replace("(", "")
                cols = line.split()
                L[(line_num - 1)] = cols[0]
    # read R
    file_nameR = os.path.join(basepath, time_name, 'R')
    with open(file_nameR) as handle:

        size1d = len(handle.readlines()) - 2
        R = np.empty((size1d,6))
        handle.seek(0)
        for line_num, line in enumerate(handle):
            if (line_num != 0) & (line_num != size1d + 1):
                line = line.replace(")", "")
                line = line.replace("(", "")
                cols = line.split()
                R[(line_num - 1),:] = cols[:]
    
    return coord, U, L, R, size1d
