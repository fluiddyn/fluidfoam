#!/usr/bin/env python3
"""Check whether foamlib reads OpenFOAM addressing files natively.

For every processor of a decomposed case, cellProcAddressing is read with
foamlib (FoamFile(path)[None]) and with our own parser (read_label_list), and
the two results are compared. It tells whether the 'foamlib(addr)' variant
of the benchmark (which uses foamlib alone) can be trusted on your files and
with your foamlib version, and gives the format of the files (ASCII/binary,
label size) because foamlib's binary list parser infers the data type.

Usage:
    python check_foamlib_addressing.py --case bench/data/case_decomp_real
"""
import argparse
import os
import re
import time

import numpy as np

import readers_foamlib as rf


def describe(path):
    with open(path, "rb") as f:
        head = f.read(2000)
    fmt = re.search(rb"format\s+(\w+)\s*;", head)
    lab = re.search(rb"label=(\d+)", head)
    return (fmt.group(1).decode() if fmt else "?",
            lab.group(1).decode() if lab else "n/a")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--max-procs", type=int, default=0,
                    help="0 = all processors")
    a = ap.parse_args()

    try:
        import foamlib
        from foamlib import FoamFile
    except ImportError:
        raise SystemExit("foamlib is not installed")
    print("foamlib", getattr(foamlib, "__version__", "version unknown"))

    procs = sorted((d for d in os.listdir(a.case) if d.startswith("processor")),
                   key=lambda d: int(d[len("processor"):] or 0))
    if a.max_procs:
        procs = procs[:a.max_procs]
    ok = fail = err = 0
    t_native = t_parser = 0.0
    shown = False
    for p in procs:
        path = os.path.join(a.case, p, "constant", "polyMesh", "cellProcAddressing")
        if not os.path.exists(path) and os.path.exists(path + ".gz"):
            path += ".gz"
        if not shown:
            fmt, lab = describe(path) if not path.endswith(".gz") else ("gz", "?")
            print(f"{path}: format={fmt}, label size={lab}")
            shown = True
        t0 = time.perf_counter()
        ref = rf.read_label_list(path)
        t_parser += time.perf_counter() - t0
        try:
            t0 = time.perf_counter()
            with FoamFile(path) as f:
                got = np.asarray(f[None])
            t_native += time.perf_counter() - t0
        except Exception as e:  # noqa: BLE001
            err += 1
            print(f"  {p}: foamlib ERROR {type(e).__name__}: {str(e)[:120]}")
            continue
        if got.shape == ref.shape and np.array_equal(got, ref):
            ok += 1
        else:
            fail += 1
            print(f"  {p}: MISMATCH (shape {got.shape} vs {ref.shape}, dtype {got.dtype})")
    print(f"\n{len(procs)} files: {ok} identical, {fail} different, {err} errors")
    print(f"total time: foamlib {t_native:.3f}s, own parser {t_parser:.3f}s")
    if ok == len(procs):
        print("=> foamlib reads these files natively: use foamlib(addr).")
    else:
        print("=> foamlib cannot (reliably) read these files in this version: "
              "use foamlib(addr+parser) and say so in the paper.")


if __name__ == "__main__":
    main()
