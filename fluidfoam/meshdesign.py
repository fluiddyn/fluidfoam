""" Compute mesh grading and cell sizes
===========================================
This module provides functions to design OpenFoam mesh using blockMesh:

.. autofunction:: getgz
.. autofunction:: getdzs

"""

import numpy as np


def getgz(h, dz1, N):
    """Given a domain size h, a first grid size dz1 and a number of points N
    this function returns the common ratio, the grading gz to enter
    in blockMesk and the z and dz vectors.
    Usage: z,dz,gz=getgz(h,dz1,N)
    """
    if dz1 == h/float(N):
        print("Uniform mesh")
        r = 1
        gz = 1
    else:
        # polynomial p of the sequence terms summation between 0 and N-1
        p = np.zeros(N+1)
        p[N] =  h / dz1 - 1
        p[N-1] = -h / dz1
        p[0] = 1
        # Find the roots of the polynomial
        sol = np.roots(p)
        # Keep only the real non trivial solution
        toto = np.where(np.imag(sol) == 0)
        solreal = sol[toto]
        titi = np.where(np.real(solreal) > 0)
        #print("Real solutions:",solreal)
        titi = np.where(
                np.logical_and(np.real(solreal) > 0, np.abs(np.real(solreal)-1) > 1e-6)
                )
        solgood = solreal[titi]
        #print("Good solution:",solgood)

        # Compute the common ratio of the sequence
        try:
            r = np.real(np.real(solgood[0]))
        except IndexError:
            print("There is a problem with input data or a bug")
        # Compute the grading factor for blockMesh
        gz = r ** (N - 1)
    # Compute the grid points position and the associated spacing
    z = np.zeros(N+1)
    dz = np.zeros(N)
    dz[0] = dz1
    for i in range(N-1):
        dz[i + 1] = r **(i+1) * dz1
        z[i + 1] = z[i] + dz[i]
    z[N] = z[N - 1] + dz[N - 1]
    # print some output
    print("grid sizes, common ratio and grading factor")
    print("z[N]   =", round(z[N],4))
    print("dz[0]  =", round(dz[0],4))
    print("dz[N-1]=", round(dz[N - 1],4))
    print("common ratio: r=", round(r,4))
    print("gz=", round(gz,4))
    print("1/gz=", round(1.0 / gz,4))
    return z, dz, gz


def getdzs(h, gz, N):
    """Given a domain size h, a grading factor gz and a number of points N
    this function returns the grid size of the first and the last
    points.
    Usage: dz1,dzN=getdzs(h,gz,N)
    """
    # Compute the common ratio of the sequence
    r = gz ** (1.0 / (N - 1))
    if r != 1:
        dz1 = h * (1.0 - r) / (1.0 - r ** N)
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
    print("dz[0]=", dz1)
    print("dz[N-1]=", dzN)

    return dz1, dzN
