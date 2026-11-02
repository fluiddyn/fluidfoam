#!/usr/bin/env python3
"""Generate the benchmark datasets for fluidfoam's comparative benchmark.

Writes valid OpenFOAM case structures directly from Python (no OpenFOAM
installation required), under bench/data/:

  case_ascii/      1D slab mesh, scalar field, writeFormat ascii
  case_binary/     same field, writeFormat binary (LSB)
  case_binary_gz/  same field, binary + gzip
  case_decomp/     same field, decomposed into N processor dirs
                   (constant/polyMesh addressing files included)

Each case contains a non-uniform volScalarField `alpha` whose values are
deterministic (seeded RNG) so that equality checks across tools are
reproducible.

Usage:
    python generate_bench_data.py --outdir bench/data --ncells 1000000 --nproc 64
"""

import argparse
import gzip
import os
import shutil
import numpy as np

HEADER = """FoamFile
{{
    version     2.0;
    format      {format};{arch}
    class       volScalarField;
    location    "0";
    object      alpha;
}}

dimensions      [0 0 0 0 0 0 0];

"""

ARCH_LINE = '\n    arch        "LSB;label=32;scalar=64";'


def field_values(ncells, seed=42):
    rng = np.random.default_rng(seed)
    return rng.random(ncells)


def write_ascii_field(path, values):
    with open(path, "w") as f:
        f.write(HEADER.format(format="ascii", arch=""))
        f.write("internalField   nonuniform List<scalar> \n")
        f.write(f"{len(values)}\n")
        f.write("(\n")
        f.write("\n".join(f"{v:.15e}" for v in values))
        f.write("\n)\n;\n")
        f.write(BOUNDARY_FIELD)


def write_binary_field(path, values):
    payload = values.astype("<f8").tobytes()
    if True:
        with open(path, "wb") as f:
            f.write(HEADER.format(format="binary", arch=ARCH_LINE).encode())
            f.write(b"internalField   nonuniform List<scalar> \n")
            f.write(f"{len(values)}\n".encode())
            f.write(b"(")
            f.write(payload)
            f.write(b");\n")
            f.write(BOUNDARY_FIELD.encode())


BOUNDARY_FIELD = """boundaryField
{
    inlet
    {
        type            fixedValue;
        value           uniform 0;
    }
    outlet
    {
        type            zeroGradient;
    }
    walls
    {
        type            zeroGradient;
    }
}

// ************************************************************************* //
"""


ADDRESSING_HEADER = """FoamFile
{{
    version     2.0;
    format      ascii;
    class       labelList;
    location    "constant/polyMesh";
    object      {object};
}}

"""


def write_decomposed_case(outdir, values, nproc, binary=False):
    """Contiguous decomposition with proper addressing files."""
    if os.path.isdir(outdir):
        shutil.rmtree(outdir)
    chunks = np.array_split(values, nproc)
    offset = 0
    for p, chunk in enumerate(chunks):
        pdir = os.path.join(outdir, f"processor{p}")
        time_dir = os.path.join(pdir, "0")
        os.makedirs(time_dir, exist_ok=True)
        writer = write_binary_field if binary else write_ascii_field
        writer(os.path.join(time_dir, "alpha"), chunk)

        mesh_dir = os.path.join(pdir, "constant", "polyMesh")
        os.makedirs(mesh_dir, exist_ok=True)
        n_local = len(chunk)
        # cellProcAddressing: global index of each local cell
        with open(os.path.join(mesh_dir, "cellProcAddressing"), "w") as f:
            f.write(ADDRESSING_HEADER.format(object="cellProcAddressing"))
            f.write(f"{n_local}\n({offset}")
            f.write("".join(f" {offset + i}" for i in range(1, n_local)))
            f.write(")\n;\n")
        # faceProcAddressing / boundaryProcAddressing: same trivial layout
        for obj in ("faceProcAddressing", "boundaryProcAddressing"):
            with open(os.path.join(mesh_dir, obj), "w") as f:
                f.write(ADDRESSING_HEADER.format(object=obj))
                f.write(f"{n_local}\n({offset}")
                f.write("".join(f" {offset + i}" for i in range(1, n_local)))
                f.write(")\n;\n")
        offset += n_local


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="bench/data")
    ap.add_argument("--ncells", type=int, default=1_000_000)
    ap.add_argument("--nproc", type=int, default=64)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    values = field_values(args.ncells, args.seed)

    # 1. ASCII case
    d = os.path.join(args.outdir, "case_ascii", "0")
    os.makedirs(d, exist_ok=True)
    write_ascii_field(os.path.join(d, "alpha"), values)

    # 2. Binary case
    d = os.path.join(args.outdir, "case_binary", "0")
    os.makedirs(d, exist_ok=True)
    write_binary_field(os.path.join(d, "alpha"), values)

    # 3. Gzipped binary case (whole file gzipped as alpha.gz, which is
    # what OpenFOAM writes and what fluidfoam looks for: path + ".gz")
    d = os.path.join(args.outdir, "case_binary_gz", "0")
    os.makedirs(d, exist_ok=True)
    write_binary_field(os.path.join(d, "alpha"), values)
    with open(os.path.join(d, "alpha"), "rb") as fin, gzip.GzipFile(
        os.path.join(d, "alpha.gz"), "wb", mtime=0
    ) as fout:
        fout.write(fin.read())
    os.remove(os.path.join(d, "alpha"))

    # 4. Decomposed cases: ASCII and binary (real HPC runs write binary)
    write_decomposed_case(
        os.path.join(args.outdir, "case_decomp"), values, args.nproc
    )
    write_decomposed_case(
        os.path.join(args.outdir, "case_decomp_binary"), values, args.nproc,
        binary=True,
    )

    print(f"Datasets written to {args.outdir}/:")
    for name in ("case_ascii", "case_binary", "case_binary_gz",
                 "case_decomp", "case_decomp_binary"):
        size = 0
        for root, _, files in os.walk(os.path.join(args.outdir, name)):
            size += sum(
                os.path.getsize(os.path.join(root, f)) for f in files
            )
        print(f"  {name:16s} {size / 1e6:8.1f} MB")
    print(f"ncells={args.ncells} nproc={args.nproc} seed={args.seed}")


if __name__ == "__main__":
    main()
