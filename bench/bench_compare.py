#!/usr/bin/env python3
"""Comparative reading benchmark: fluidfoam vs PyFoam vs Ofpp vs foamlib
(and, optionally, OpenFOAM's reconstructPar for decomposed cases).

This file is only the DRIVER (timing, memory, equality, report). The code that
each tool needs is in separate modules, so that what a user must write with
each tool is visible:

    readers_fluidfoam.py   fluidfoam      (one call, also for decomposed cases)
    readers_foamlib.py     foamlib        (per-processor assembly code)
    readers_other.py       Ofpp, PyFoam
    reconstructpar.py      reconstructPar + reading (needs OpenFOAM)

Protocol:
- 4 synthetic datasets (A: ASCII, B: binary, C: gzipped binary, D: decomposed)
  and 1 real decomposed case (E, generate_real_decomp_case.py)
- median of N runs, warm cache; client-cold runs with --cold
- peak memory via tracemalloc
- value equality between tools, against a ground-truth array when the case
  provides one (reference_<field>.npy)
- amount of user code needed to get the array (lines of Python)

Usage:
    python bench_compare.py --case bench/data/case_binary --time 0 --runs 10
    python bench_compare.py --case bench/data/case_decomp_real --time 0 \
        --decomposed --with-reconstructpar --cold --runs 5
"""

import argparse
import ast
import inspect
import os
import shutil
import statistics
import tempfile
import textwrap
import time
import tracemalloc

import numpy as np

import readers_fluidfoam
import readers_foamlib
import readers_other
import reconstructpar

MODULES = (readers_fluidfoam, readers_foamlib, readers_other)
TOOLS = {}
TOOLS_DECOMPOSED = {}
USER_CODE = {}
USER_CODE_DECOMPOSED = {}
for _m in MODULES:
    TOOLS.update(_m.READERS)
    TOOLS_DECOMPOSED.update(_m.READERS_DECOMPOSED)
    USER_CODE.update(_m.USER_CODE)
    USER_CODE_DECOMPOSED.update(_m.USER_CODE_DECOMPOSED)


# ---------------------------------------------------------------- helpers
def evict(path):
    """Drop the client-side cached pages of all files under path.

    Uses posix_fadvise(DONTNEED): no root needed. Only the client page cache
    is affected (the NFS server cache cannot be flushed from user space), so
    'cold' means 'client-cold'.
    """
    for root, _, files in os.walk(path):
        for f in files:
            try:
                fd = os.open(os.path.join(root, f), os.O_RDONLY)
                try:
                    os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
                finally:
                    os.close(fd)
            except OSError:
                pass


def count_user_lines(funcs):
    """Lines of Python in the given functions (body only: no def line, no
    docstring, no blank or comment-only lines)."""
    total = 0
    for fn in funcs:
        src = textwrap.dedent(inspect.getsource(fn))
        node = ast.parse(src).body[0]
        body = node.body
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(getattr(body[0], "value", None), ast.Constant)
                and isinstance(body[0].value.value, str)):
            body = body[1:]
        if not body:
            continue
        lines = src.splitlines()[body[0].lineno - 1: node.end_lineno]
        total += sum(1 for ln in lines
                     if ln.strip() and not ln.strip().startswith("#"))
    return total


# ------------------------------------------------------------------- driver
def run_benchmark(reader, case, timename, fieldname, nruns,
                  cold=False, cold_path=None):
    # Timing first, WITHOUT tracemalloc: it slows down allocations by an
    # order of magnitude and would bias the comparison between tools.
    reconstructpar.SPLIT.clear()
    times = []
    result = None
    for _ in range(nruns):
        if cold:
            evict(cold_path or case)  # not timed
        t0 = time.perf_counter()
        result = reader(case, timename, fieldname)
        times.append(time.perf_counter() - t0)
    split = {k: list(v) for k, v in reconstructpar.SPLIT.items()}
    # Memory measured ONCE, separately, with tracemalloc (Python allocations
    # only: for reconstructPar this is the reading of the reconstructed field).
    tracemalloc.start()
    result = reader(case, timename, fieldname)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "median_s": statistics.median(times),
        "min_s": min(times),
        "peak_mb": peak / 1e6,
        "shape": np.asarray(result).shape,
        "split": split,
    }


def check_equality(values, reference=None, tol=1e-12):
    """Compare every tool with the reference (ground truth if available,
    otherwise the first tool). Returns one status line per tool."""
    names = list(values)
    if reference is None:
        ref_name, ref = names[0], np.asarray(values[names[0]])
        others = names[1:]
    else:
        ref_name, ref = "ground truth", np.asarray(reference)
        others = names
    lines = []
    for n in others:
        b = np.asarray(values[n])
        if ref.shape != b.shape:
            lines.append(f"  {n}: FAIL shape {b.shape} vs {ref_name} {ref.shape}")
        elif not np.allclose(ref, b, rtol=tol, atol=tol):
            lines.append(f"  {n}: FAIL values differ from {ref_name}")
        else:
            lines.append(f"  {n}: OK (vs {ref_name})")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--time", default="latestTime", help="'latestTime' or e.g. '25'")
    ap.add_argument("--field", default="alpha")
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--decomposed", action="store_true")
    ap.add_argument("--nproc", type=int, default=0)
    ap.add_argument("--cold", action="store_true",
                    help="evict the client page cache before each timed run")
    ap.add_argument("--with-reconstructpar", action="store_true",
                    help="decomposed only: also time reconstructPar + reading "
                         "(real decomposed case, run on a copy)")
    ap.add_argument("--workdir", default=None,
                    help="where to copy the case for reconstructPar")
    args = ap.parse_args()

    tools = TOOLS_DECOMPOSED if args.decomposed else TOOLS
    user_code = USER_CODE_DECOMPOSED if args.decomposed else USER_CODE
    print(f"case={args.case} field={args.field} runs={args.runs} "
          f"cache={'client-cold' if args.cold else 'warm'}")
    print(f"tools available: {', '.join(tools)}")
    if not tools:
        raise SystemExit("no tool installed")
    if args.decomposed:
        for name in TOOLS:
            if not any(k.startswith(name) for k in tools):
                print(f"{name}: skipped (no decomposed support)")

    # resolve 'latestTime'
    timename = args.time
    if timename == "latestTime":
        if args.decomposed:
            # time dirs live inside processorN/, e.g. processor0/0
            procs = sorted(d for d in os.listdir(args.case)
                           if d.startswith("processor"))
            if not procs:
                raise SystemExit(
                    f"no processorN dirs in {args.case}: not a decomposed case?"
                )
            scan = os.path.join(args.case, procs[0])
        else:
            scan = args.case
        dirs = [d for d in os.listdir(scan)
                if d[0].isdigit() and float(d) >= 0]
        if not dirs:
            raise SystemExit(f"no time directories found in {scan}")
        timename = max(dirs, key=float)
        print(f"latest time = {timename}")

    # entries: (display name, reader, case given to reader, path to evict)
    entries = [(n, r, args.case, args.case) for n, r in tools.items()]

    work = None
    if args.with_reconstructpar:
        if not args.decomposed:
            raise SystemExit("--with-reconstructpar needs --decomposed")
        reconstructpar.check_case(args.case)
        work = args.workdir or tempfile.mkdtemp(
            prefix="bench_reconstruct_",
            dir=os.path.dirname(os.path.abspath(args.case)))
        if os.path.exists(work):
            shutil.rmtree(work)
        print(f"copying the case to {work} (reconstructPar writes into it) ...")
        shutil.copytree(args.case, work)
        entries.append(("reconstructPar+read", reconstructpar.make_reader(work),
                        args.case, work))

    reference = None
    ref_path = os.path.join(args.case, f"reference_{args.field}.npy")
    if os.path.exists(ref_path):
        reference = np.load(ref_path)
        print(f"ground truth: {ref_path}")

    results = {}
    values = {}
    try:
        for name, fn, case_arg, evict_path in entries:
            try:
                r = run_benchmark(fn, case_arg, timename, args.field, args.runs,
                                  cold=args.cold, cold_path=evict_path)
                results[name] = r
                values[name] = fn(case_arg, timename, args.field)
                print(f"{name:20s} median={r['median_s']:.3f}s  "
                      f"min={r['min_s']:.3f}s  peak={r['peak_mb']:.1f}MB  "
                      f"shape={r['shape']}")
                for k, v in r["split"].items():
                    print(f"{'':22s}- {k}: median={statistics.median(v):.3f}s")
            except Exception as e:
                print(f"{name:20s} FAILED: {e}")
    finally:
        if work is not None and os.path.exists(work):
            shutil.rmtree(work)

    if values:
        print("equality check:")
        for line in check_equality(values, reference):
            print(line)

    print("\nuser code needed to get the array (lines of Python, "
          "excluding imports; foamlib(addr+parser) excludes its labelList parser):")
    for name in results:
        if name in user_code:
            print(f"  {name:20s} {count_user_lines(user_code[name]):3d} line(s)")
        elif name == "reconstructPar+read":
            print(f"  {name:20s} external OpenFOAM command (needs an OpenFOAM "
                  "installation) + 1 read call")


if __name__ == "__main__":
    main()
