""" Compute mesh grading and cell sizes
===========================================
This module provides functions to design OpenFoam mesh using blockMesh:

.. autofunction:: getgz
.. autofunction:: getdzs

"""

import numpy as np

def getgz(h, dz1, N):
    """ Given a domain size h, a first grid size dz1 and a number of points N
        this function returns the common ratio, the grading gz to enter
        in blockMesk and the z and dz vectors.
        Usage: z,dz,gz=getgz(h,dz1,N)
    """
    # polynomial p of the sequence terms summation between 0 and N-1
    p = np.zeros(N)
    p[0] = h / dz1 - 1
    p[1] = -h / dz1
    p[N - 1] = 1
    # Find the roots of the polynomial
    sol = np.roots(p)
    # Keep only the real non trivial solution
    toto = np.where(np.imag(sol) == 0)
    solreal = sol[toto]
    titi = np.where(np.real(solreal) > 0)
    titi = np.where(np.logical_and(np.real(solreal) > 0,
                                   np.real(solreal) < 0.9999))
    solgood = solreal[titi]
    # Compute the common ratio of the sequence
    try:
        r = 1. / np.real(np.real(solgood[0]))
    except IndexError:
        print("dz1 so high compared to the number of cell and the domain size")
        print("gz would be superior to 1 : NOT IMPLEMENTED")
        r = 1.
        gz = 0
    # Compute the grading factor for blockMesh
    gz = r ** (N - 2)
    # Compute the grid points position and the associated spacing
    z = np.zeros(N)
    dz = np.zeros(N - 1)
    for i in range(N - 1):
        z[i + 1] = z[i] + r ** i * dz1
        dz[i] = z[i + 1] - z[i]

    # print some output
    print("grid sizes, common ratio and grading factor")
    print('z[N-1]=', z[N - 1])
    print('dz[0]=', dz[0])
    print('dz[N-2]=', dz[N - 2])
    print('common ratio: r=', r)
    print('gz=', gz)
    print('1/gz=', 1. / gz)
    return z, dz, gz


def getdzs(h, gz, N):
    """ Given a domain size h, a grading factor gz and a number of points N
        this function returns the grid size of the first and the last
        points.
        Usage: dz1,dzN=getdzs(h,gz,N)
    """
    # Compute the common ratio of the sequence
    r = gz ** (1. / (N - 1))
    if r != 1:
        dz1 = h * (1. - r) / (1. - r ** (N - 1))
        dzN = gz * dz1
    else:
        dz1 = h / float(N - 1)
        dzN = dz1

    z = 0
    for i in range(N - 1):
        zn = z + r ** i * dz1
        z = zn
        #  print i+1,z

    #  print some output
    print("grid size of the first and last cells:")
    print('dz[0]=', dz1)
    print('dz[N-1]=', dzN)

    return dz1, dzN
