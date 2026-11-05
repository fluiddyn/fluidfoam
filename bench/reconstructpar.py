"""OpenFOAM's reconstructPar as a competitor for decomposed cases.

Workflow: reconstructPar for ONE field (on a copy of the case, because it
writes <case>/<time>/<field>), then reading of the reconstructed field with
fluidfoam. It needs an OpenFOAM installation and a REAL decomposed case
(see generate_real_decomp_case.py).
"""
import os
import shutil
import subprocess
import time as _time

import readers_fluidfoam

SPLIT = {}  # sub-timings recorded by the reader (cleared by the driver)


def clean_reconstructed(work, timename, name):
    """Remove the reconstructed field so that each run does the full work."""
    tdir = os.path.join(work, timename)
    for fn in (name, name + ".gz"):
        p = os.path.join(tdir, fn)
        if os.path.exists(p):
            os.remove(p)
    if os.path.isdir(tdir) and not os.listdir(tdir):
        os.rmdir(tdir)


FVSCHEMES = """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvSchemes;
}

ddtSchemes          { default Euler; }
gradSchemes         { default Gauss linear; }
divSchemes          { default none; }
laplacianSchemes    { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes       { default corrected; }
"""

FVSOLUTION = """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvSolution;
}

solvers
{
}
"""


def ensure_system_dicts(work):
    """reconstructPar builds an fvMesh, so it needs system/fvSchemes and
    system/fvSolution even though they are not used. Create minimal ones in
    the working COPY when the case does not have them."""
    sysdir = os.path.join(work, "system")
    os.makedirs(sysdir, exist_ok=True)
    for name, text in (("fvSchemes", FVSCHEMES), ("fvSolution", FVSOLUTION)):
        path = os.path.join(sysdir, name)
        if not os.path.exists(path):
            with open(path, "w") as f:
                f.write(text)


def check_case(case):
    if shutil.which("reconstructPar") is None:
        raise SystemExit("reconstructPar not found: source the OpenFOAM environment")
    for needed in (os.path.join(case, "constant", "polyMesh", "points"),
                   os.path.join(case, "processor0", "constant", "polyMesh",
                                "points")):
        if not os.path.exists(needed):
            raise SystemExit(
                f"{needed} not found: reconstructPar needs a real decomposed "
                "case (see generate_real_decomp_case.py)"
            )


def make_reader(work):
    """Reader working on the copy 'work' (the 'case' argument is ignored)."""

    ensure_system_dicts(work)

    def reader(case, timename, name):
        if readers_fluidfoam.fluidfoam is None:
            raise RuntimeError("fluidfoam is needed to read the reconstructed field")
        clean_reconstructed(work, timename, name)
        cmd = ["reconstructPar", "-case", work, "-time", timename,
               "-fields", f"({name})"]
        if timename in ("0", "0.0"):
            cmd.append("-withZero")  # time 0 is skipped otherwise
        t0 = _time.perf_counter()
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True)
        t1 = _time.perf_counter()
        if r.returncode != 0:
            raise RuntimeError("reconstructPar failed: " + r.stderr[-800:])
        arr = readers_fluidfoam.fluidfoam.readscalar(work, timename, name)
        t2 = _time.perf_counter()
        SPLIT.setdefault("reconstructPar", []).append(t1 - t0)
        SPLIT.setdefault("read reconstructed field", []).append(t2 - t1)
        return arr

    return reader
