#!/usr/bin/env python3
"""Generate a REAL decomposed OpenFOAM case (needs blockMesh and decomposePar).

The synthetic decomposed case of generate_bench_data.py only contains the
addressing files: it cannot be processed by reconstructPar, and its
decomposition is contiguous, which hides the reordering work. This script
builds a genuine case with OpenFOAM tools:

  * n x n x n hexahedral cells (blockMesh), default 100^3 = 1e6 cells
  * a non-uniform scalar field `alpha` (seeded RNG, global cell order)
  * decomposePar with the `simple` method on a (a b c) grid: processors hold
    blocks of the cube, so cellProcAddressing is NOT contiguous
  * processor*/0/alpha written in binary (controlDict writeFormat)
  * the top-level 0/ directory is removed afterwards, so that only the
    decomposed data remains (as in a real HPC run); reconstructPar -time 0
    -withZero recreates it
  * reference_alpha.npy: the field in global cell order, a ground truth that
    does not depend on any reader

Usage (OpenFOAM environment sourced):
    python generate_real_decomp_case.py --outdir bench/data/case_decomp_real \
        --n 100 --grid 4 4 4 --seed 42
"""
import argparse
import os
import shutil
import subprocess

import numpy as np

FOAMFILE = """FoamFile
{{
    version     2.0;
    format      ascii;
    class       {cls};
    object      {obj};
}}

"""


def write(path, cls, obj, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(FOAMFILE.format(cls=cls, obj=obj))
        f.write(body)


def run(cmd, case):
    print("$", " ".join(cmd), f"(case {case})")
    r = subprocess.run(cmd + ["-case", case], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True)
    if r.returncode != 0:
        raise SystemExit(r.stdout[-2000:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="bench/data/case_decomp_real")
    ap.add_argument("--n", type=int, default=100, help="cells per direction")
    ap.add_argument("--grid", type=int, nargs=3, default=[4, 4, 4],
                    help="simple decomposition: subdomains per direction")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--format", choices=["binary", "ascii"], default="binary",
                    help="writeFormat of the decomposed data (processor*/)")
    a = ap.parse_args()

    for exe in ("blockMesh", "decomposePar"):
        if shutil.which(exe) is None:
            raise SystemExit(f"{exe} not found: source the OpenFOAM environment")
    nproc = a.grid[0] * a.grid[1] * a.grid[2]
    ncells = a.n ** 3
    case = a.outdir
    if os.path.isdir(case):
        shutil.rmtree(case)

    write(f"{case}/system/controlDict", "dictionary", "controlDict", f"""
application     icoFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         0;
deltaT          1;
writeControl    timeStep;
writeInterval   1;
writeFormat     {a.format};
writeCompression off;
timeFormat      general;
timePrecision   6;
""")

    write(f"{case}/system/blockMeshDict", "dictionary", "blockMeshDict", f"""
vertices
(
    (0 0 0) (1 0 0) (1 1 0) (0 1 0)
    (0 0 1) (1 0 1) (1 1 1) (0 1 1)
);
blocks
(
    hex (0 1 2 3 4 5 6 7) ({a.n} {a.n} {a.n}) simpleGrading (1 1 1)
);
edges ();
boundary
(
    walls
    {{
        type patch;
        faces
        (
            (3 7 6 2) (0 4 7 3) (2 6 5 1)
            (1 5 4 0) (0 3 2 1) (4 5 6 7)
        );
    }}
);
mergePatchPairs ();
""")

    write(f"{case}/system/decomposeParDict", "dictionary", "decomposeParDict", f"""
numberOfSubdomains {nproc};
method          simple;
simpleCoeffs
{{
    n           ({a.grid[0]} {a.grid[1]} {a.grid[2]});
    delta       0.001;
}}
""")

    # needed by reconstructPar (it builds an fvMesh); content is not used
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import reconstructpar
    reconstructpar.ensure_system_dicts(case)

    # initial field, ASCII (decomposePar writes it in binary, see controlDict)
    values = np.random.default_rng(a.seed).random(ncells)
    os.makedirs(f"{case}/0", exist_ok=True)
    with open(f"{case}/0/alpha", "w") as f:
        f.write(FOAMFILE.format(cls="volScalarField", obj="alpha"))
        f.write("dimensions      [0 0 0 0 0 0 0];\n\n")
        f.write(f"internalField   nonuniform List<scalar>\n{ncells}\n(\n")
        f.write("\n".join(f"{v:.15e}" for v in values))
        f.write("\n)\n;\n\nboundaryField\n{\n    walls\n    {\n")
        f.write("        type            zeroGradient;\n    }\n}\n")

    run(["blockMesh"], case)
    run(["decomposePar", "-force"], case)

    shutil.rmtree(f"{case}/0")  # keep only the decomposed data
    np.save(f"{case}/reference_alpha.npy", values)
    print(f"\nReal decomposed case written to {case}: {ncells} cells, "
          f"{nproc} processors, simple ({a.grid[0]} {a.grid[1]} {a.grid[2]})")
    print("Run for instance:")
    print(f"  python bench/bench_compare.py --case {case} --time 0 "
          "--decomposed --with-reconstructpar --cold --runs 5")


if __name__ == "__main__":
    main()
