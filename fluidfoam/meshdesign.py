"""Design of graded meshes for blockMesh
==========================================

This module provides two functions to design one-dimensional graded
(geometrically stretched) meshes for OpenFOAM's blockMesh utility:

- :func:`getgz`: given the domain size, the first cell size and the number
  of cells, compute the expansion ratio, the blockMesh grading factor and
  the cell face positions and cell sizes.
- :func:`getdzs`: the inverse problem: given the domain size, the grading
  factor and the number of cells, compute the first and last cell sizes.

These are the quantities needed to resolve near-wall gradients on
non-uniform meshes: the mesh is refined towards the wall with a constant
expansion ratio, and blockMesh is parametrised with the ratio of the last
to the first cell size (the grading factor).

"""

import numpy as np


def getgz(
    h: float, dz1: float, N: int, verbose: bool = False
) -> tuple[np.ndarray, np.ndarray, float]:
    """Compute the grading of a geometrically stretched mesh.

    Given a domain size ``h``, a first cell size ``dz1`` and a number of
    cells ``N``, return the cell face positions, the cell sizes, and the
    grading factor to enter in blockMesh.

    Args:
        h: float, domain size.

        dz1: float, size of the first cell.

        N: int, number of cells.

        verbose: bool, print the mesh characteristics if True.

    Returns:
        tuple: (z, dz, gz) where z is the array of the cell face positions
        (size N + 1, from 0 to h), dz the array of the cell sizes (size N)
        and gz the grading factor (ratio of the last to the first cell
        size).

    Usage: z, dz, gz = fluidfoam.getgz(h, dz1, N)

    """
    if dz1 == h / float(N):
        if verbose:
            print("Uniform mesh")
        r = 1.0
        gz = 1.0
    else:
        # The cell sizes form a geometric sequence: dz_i = r**i * dz1.
        # Their sum equals h, which yields a polynomial equation in r.
        # sum_{i=0}^{N-1} r**i = h / dz1
        p = np.zeros(N + 1)
        p[N] = h / dz1 - 1
        p[N - 1] = -h / dz1
        p[0] = 1
        # Find the roots of the polynomial and keep the single real,
        # positive solution other than 1.
        sol = np.roots(p)
        sol = sol[np.abs(np.imag(sol)) < 1e-10]
        sol = np.real(sol)
        sol = sol[np.logical_and(sol > 0, np.abs(sol - 1) > 1e-6)]
        if sol.size == 0:
            raise ValueError(
                "getgz: no valid expansion ratio found; check h, dz1 and N "
                "(they must define a feasible geometric grading)"
            )
        r = float(sol[0])
        # Grading factor for blockMesh
        gz = r ** (N - 1)

    # Cell face positions and cell sizes
    dz = np.zeros(N)
    dz[0] = dz1
    for i in range(N - 1):
        dz[i + 1] = r ** (i + 1) * dz1
    z = np.concatenate(([0.0], np.cumsum(dz)))
    if verbose:
        print("mesh grading characteristics:")
        print(f"  domain height      h     = {h:.6g}")
        print(f"  first cell size    dz[0] = {dz[0]:.6g}")
        print(f"  last cell size     dz[-1]= {dz[-1]:.6g}")
        print(f"  expansion ratio     r    = {r:.6g}")
        print(f"  grading factor      gz   = {gz:.6g}")
        print(f"  inverse grading   1/gz   = {1.0 / gz:.6g}")
    return z, dz, gz


def getdzs(h: float, gz: float, N: int) -> tuple[float, float]:
    """Compute the first and last cell sizes of a graded mesh.

    Given a domain size ``h``, a grading factor ``gz`` and a number of
    cells ``N``, return the first and last cell sizes.

    Args:
        h: float, domain size.

        gz: float, grading factor (ratio of the last to the first cell
        size).

        N: int, number of cells.

    Returns:
        tuple: (dz1, dzN) where dz1 is the first cell size and dzN the
        last cell size.

    Usage: dz1, dzN = fluidfoam.getdzs(h, gz, N)

    """
    # Expansion ratio of the geometric sequence
    r = gz ** (1.0 / (N - 1))
    if np.isclose(r, 1.0):
        # uniform mesh (also handles gz == 1 given as int)
        dz1 = h / float(N)
        dzN = dz1
    else:
        dz1 = h * (1.0 - r) / (1.0 - r**N)
        dzN = gz * dz1
    return dz1, dzN
