"""Tests of the reading of decomposed cases (processor0, processor1, ...).

A synthetic case is built on the fly: a column of 24 hexahedral cells
(unit square section, z from 0 to 24) decomposed on 2 processors:

* processor0 holds the global cells 0..11 (same order),
* processor1 holds the global cells 23..12 (reversed order), so that the
  addressing is not trivial and a simple concatenation would give wrong
  results.

No OpenFOAM installation is needed.
"""

import functools
import os
import re
import shutil
import struct
import tempfile
import unittest

import numpy as np

try:
    from fluidfoam import readof
except ImportError:  # standalone use
    import readof

NCELLS = 24
NLOC = 12
ADDR = [np.arange(NLOC), np.arange(NCELLS - 1, NLOC - 1, -1)]
HEADER = (
    "FoamFile\n{{\n    version     2.0;\n    format      {fmt};\n"
    '    arch        "LSB;label=32;scalar=64";\n'
    "    class       {cls};\n{note}    object      {obj};\n}}\n\n"
)


def _write(path, text, binary=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(text.encode() if binary is None else binary)


def column_mesh(zs):
    n = len(zs) - 1
    pts = [(x, y, z) for z in zs for (x, y) in ((0, 0), (1, 0), (1, 1), (0, 1))]
    faces, owner, neigh = [], [], []
    for k in range(1, n):
        faces.append([4 * k + j for j in range(4)])
        owner.append(k - 1)
        neigh.append(k)
    nint = len(faces)
    faces.append([0, 1, 2, 3])
    owner.append(0)
    faces.append([4 * n + j for j in range(4)])
    owner.append(n - 1)
    for i in range(n):
        for j in range(4):
            a, b = j, (j + 1) % 4
            faces.append([4 * i + a, 4 * i + b, 4 * (i + 1) + b, 4 * (i + 1) + a])
            owner.append(i)
    return pts, faces, owner, neigh, nint


def write_mesh(meshdir, zs):
    pts, faces, owner, neigh, nint = column_mesh(zs)
    note = (
        '    note        "nPoints:%d  nCells:%d  nFaces:%d  nInternalFaces:%d";\n'
    )
    note = note % (len(pts), len(zs) - 1, len(faces), nint)
    h = lambda cls, obj: HEADER.format(fmt="ascii", cls=cls, obj=obj, note=note)
    _write(
        os.path.join(meshdir, "points"),
        HEADER.format(fmt="ascii", cls="vectorField", obj="points", note="")
        + "%d\n(\n" % len(pts)
        + "".join("(%r %r %r)\n" % tuple(map(float, p)) for p in pts)
        + ")\n",
    )
    _write(
        os.path.join(meshdir, "faces"),
        h("faceList", "faces")
        + "%d\n(\n" % len(faces)
        + "".join("4(%d %d %d %d)\n" % tuple(f) for f in faces)
        + ")\n",
    )
    _write(
        os.path.join(meshdir, "owner"),
        h("labelList", "owner")
        + "\n%d\n(\n" % len(owner)
        + "".join("%d\n" % o for o in owner)
        + ")\n",
    )
    _write(
        os.path.join(meshdir, "neighbour"),
        h("labelList", "neighbour")
        + "\n%d\n(\n" % len(neigh)
        + "".join("%d\n" % o for o in neigh)
        + ")\n",
    )


def write_field(path, cls, name, values=None, uniform=None):
    """values: (n,) scalar or (n, 3) vector ; uniform: value or tuple."""
    head = HEADER.format(fmt="ascii", cls=cls, obj=name, note="")
    head += "dimensions      [0 0 0 0 0 0 0];\n\n"
    if uniform is not None:
        if isinstance(uniform, tuple):
            internal = "internalField   uniform (%s);\n" % " ".join(
                map(str, uniform)
            )
        else:
            internal = "internalField   uniform %s;\n" % uniform
    elif values.ndim == 1:
        internal = (
            "internalField   nonuniform List<scalar> \n%d\n(\n" % len(values)
            + "".join("%r\n" % float(v) for v in values)
            + ")\n;\n"
        )
    else:
        internal = (
            "internalField   nonuniform List<vector> \n%d\n(\n" % len(values)
            + "".join("(%r %r %r)\n" % tuple(map(float, v)) for v in values)
            + ")\n;\n"
        )
    tail = "\nboundaryField\n{\n    top\n    {\n        type  zeroGradient;\n    }\n}\n"
    _write(path, head + internal + tail)


def write_addressing(meshdir, addr, binary=False):
    path = os.path.join(meshdir, "cellProcAddressing")
    if not binary:
        _write(
            path,
            HEADER.format(
                fmt="ascii", cls="labelList", obj="cellProcAddressing", note=""
            )
            + "%d\n(\n" % len(addr)
            + "".join("%d\n" % a for a in addr)
            + ")\n",
        )
    else:
        head = HEADER.format(
            fmt="binary", cls="labelList", obj="cellProcAddressing", note=""
        )
        body = (
            b"%d\n(" % len(addr) + struct.pack("<%di" % len(addr), *addr) + b")\n"
        )
        _write(path, "", binary=head.encode() + body)


def write_binary_scalar(path, values):
    head = HEADER.format(
        fmt="binary", cls="volScalarField", obj="alphab", note=""
    )
    head += "dimensions      [0 0 0 0 0 0 0];\n\n"
    body = (
        b"internalField   nonuniform List<scalar> \n%d\n(" % len(values)
        + struct.pack("<%dd" % len(values), *map(float, values))
        + b")\n;\n\nboundaryField\n{\n    top\n    {\n        type  zeroGradient;\n    }\n}\n"
    )
    _write(path, "", binary=head.encode() + body)


# global reference data ----------------------------------------------------
ZC = np.arange(NCELLS) + 0.5
ALPHA = 10.0 + np.arange(NCELLS)
U = np.stack(
    [np.arange(NCELLS), 2.0 * np.arange(NCELLS), -1.0 * np.arange(NCELLS)]
)
BETA = np.concatenate([np.arange(1, NLOC + 1), np.full(NLOC, 7.0)])
DZ = 0.1  # mesh motion at time 0.5


@functools.lru_cache(maxsize=None)
def _case():
    root = tempfile.mkdtemp(prefix="ffdecomp_")
    # root: global mesh (decomposePar keeps it) and a time 0
    write_mesh(
        os.path.join(root, "constant", "polyMesh"), np.arange(NCELLS + 1.0)
    )
    write_field(
        os.path.join(root, "0", "alpha"),
        "volScalarField",
        "alpha",
        values=np.full(NCELLS, 99.0),
    )
    # a case without any root mesh, same processors
    for p in range(2):
        pdir = os.path.join(root, "processor%d" % p)
        zs = (
            (np.arange(NLOC + 1.0) + p * NLOC)
            if p == 0
            else (NCELLS - np.arange(NLOC + 1.0))
        )
        write_mesh(os.path.join(pdir, "constant", "polyMesh"), zs)
        write_addressing(
            os.path.join(pdir, "constant", "polyMesh"), ADDR[p], binary=(p == 1)
        )
        # moved points at time 0.5 (dynamic mesh)
        pts_dir = os.path.join(pdir, "0.5", "polyMesh")
        write_mesh(pts_dir, zs + DZ)
        for f in ("faces", "owner", "neighbour"):
            os.remove(os.path.join(pts_dir, f))
        write_field(
            os.path.join(pdir, "0.5", "alpha"),
            "volScalarField",
            "alpha",
            values=ALPHA[ADDR[p]],
        )
        write_field(
            os.path.join(pdir, "0.5", "U"),
            "volVectorField",
            "U",
            values=U[:, ADDR[p]].T,
        )
        write_binary_scalar(os.path.join(pdir, "0.5", "alphab"), ALPHA[ADDR[p]])
        if p == 0:
            write_field(
                os.path.join(pdir, "0.5", "beta"),
                "volScalarField",
                "beta",
                values=BETA[ADDR[p]],
            )
        else:
            write_field(
                os.path.join(pdir, "0.5", "beta"),
                "volScalarField",
                "beta",
                uniform=7,
            )
            write_field(
                os.path.join(pdir, "0.5", "Uu"),
                "volVectorField",
                "Uu",
                uniform=(1, 2, 3),
            )
        if p == 0:
            write_field(
                os.path.join(pdir, "0.5", "Uu"),
                "volVectorField",
                "Uu",
                values=np.tile([1.0, 2.0, 3.0], (NLOC, 1)),
            )
    # copy without root mesh
    nomesh = root + "_nomesh"
    shutil.copytree(root, nomesh)
    shutil.rmtree(os.path.join(nomesh, "constant"))
    return root, nomesh


# --------------------------------------------------------------------------
# collated case (processors2/, decomposedBlockData): one file per field with
# one block per processor; as written by OpenFOAM, only the block of rank 0
# carries the FoamFile header.
# --------------------------------------------------------------------------
_HDR = re.compile(rb"\s*FoamFile\s*\{.*?\}\n", re.S)
MESH_FILES = [
    "constant/polyMesh/" + f
    for f in ("cellProcAddressing", "points", "faces", "owner", "neighbour")
]
FIELD_FILES = ["0.5/" + f for f in ("alpha", "U", "beta", "Uu", "alphab")]
POINTS_T = ["0.5/polyMesh/points"]


def _addr_binary(addr):
    head = HEADER.format(
        fmt="binary", cls="labelList", obj="cellProcAddressing", note=""
    )
    return (
        head.encode()
        + b"%d\n(" % len(addr)
        + struct.pack("<%di" % len(addr), *addr)
        + b")\n"
    )


def _collate(src_root, dst_root, rels, dirname="processors2"):
    for rel in rels:
        blocks = []
        for p in range(2):
            if rel.endswith("cellProcAddressing"):  # same format on all ranks
                blocks.append(_addr_binary(ADDR[p]))
                continue
            with open(os.path.join(src_root, "processor%d" % p, rel), "rb") as f:
                blocks.append(f.read())
        header = _HDR.match(blocks[0]).group(0)
        # drop the per-processor note: counts differ from one processor to another
        header = re.sub(rb"    note .*\n", b"", header)
        blocks[0] = header + blocks[0][_HDR.match(blocks[0]).end() :]
        blocks[1:] = [_HDR.sub(b"", b, count=1) for b in blocks[1:]]
        cls = re.search(rb"class\s+(\w+);", header).group(1).decode()
        head = (
            "FoamFile\n{\n    version     2.0;\n    format      binary;\n"
            '    arch        "LSB;label=32;scalar=64";\n'
            "    class       decomposedBlockData;\n"
            '    location    "%s";\n    object      %s;\n'
            "    data.format ascii;\n    data.class  %s;\n}\n"
            "// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //\n\n\n"
        ) % (os.path.dirname(rel), os.path.basename(rel), cls)
        body = b"".join(
            b"// processor%d\n%d\n(" % (r, len(b)) + b + b")\n\n"
            for r, b in enumerate(blocks)
        )
        _write(
            os.path.join(dst_root, dirname, rel),
            "",
            binary=head.encode() + body[:-1],
        )


@functools.lru_cache(maxsize=None)
def _collated_case():
    root, nomesh = _case()
    out = []
    for src in (root, nomesh):
        dst = src + "_collated"
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("processor*"))
        _collate(root, dst, MESH_FILES + FIELD_FILES + POINTS_T)
        out.append(dst)
    return tuple(out)


def setUpModule():
    _case()
    _collated_case()


def tearDownModule():
    for d in _case() + _collated_case():
        shutil.rmtree(d, ignore_errors=True)


class TestDecomposedCases(unittest.TestCase):

    def test_scalar_reordered(self):
        root, _ = _case()
        alpha = readof.readscalar(root, "0.5", "alpha", verbose=False)
        np.testing.assert_allclose(alpha, ALPHA)

    def test_vector_reordered(self):
        root, _ = _case()
        u = readof.readvector(root, "0.5", "U", verbose=False)
        assert u.shape == (3, NCELLS)
        np.testing.assert_allclose(u, U)

    def test_uniform_on_one_processor(self):
        root, _ = _case()
        beta = readof.readscalar(root, "0.5", "beta", verbose=False)
        np.testing.assert_allclose(beta, BETA)
        uu = readof.readvector(root, "0.5", "Uu", verbose=False)
        np.testing.assert_allclose(
            uu, np.tile([[1.0], [2.0], [3.0]], (1, NCELLS))
        )

    def test_readfield_and_structured(self):
        root, _ = _case()
        alpha = readof.readfield(root, "0.5", "alpha", verbose=False)
        np.testing.assert_allclose(alpha, ALPHA)
        a_s = readof.readscalar(
            root, "0.5", "alpha", structured=True, verbose=False
        )
        assert a_s.shape == (1, 1, NCELLS)
        np.testing.assert_allclose(a_s.ravel(), ALPHA)
        u_s = readof.readvector(root, "0.5", "U", structured=True, verbose=False)
        assert u_s.shape == (3, 1, 1, NCELLS)

    def test_mesh_without_root_mesh(self):
        root, nomesh = _case()
        x, y, z = readof.readmesh(nomesh, verbose=False)
        np.testing.assert_allclose(z, ZC)
        np.testing.assert_allclose(x, 0.5)
        np.testing.assert_allclose(y, 0.5)
        # same result as the global mesh kept in the root directory
        xr, yr, zr = readof.readmesh(root, verbose=False)
        np.testing.assert_allclose(z, zr)

    def test_dynamic_mesh_from_processors(self):
        root, _ = _case()
        x, y, z = readof.readmesh(root, time_name="0.5", verbose=False)
        np.testing.assert_allclose(z, ZC + DZ)

    def test_latest_time_prefers_processors(self):
        root, _ = _case()
        alpha = readof.readscalar(root, "latestTime", "alpha", verbose=False)
        np.testing.assert_allclose(alpha, ALPHA)  # not the root time 0 (all 99)

    def test_reconstructed_case_has_priority(self):
        root, _ = _case()
        alpha = readof.readscalar(root, "0", "alpha", verbose=False)
        np.testing.assert_allclose(alpha, 99.0)

    def test_typefield_and_unsupported_options(self):
        root, _ = _case()
        assert readof.typefield(root, "0.5", "U", verbose=False) == "vector"
        try:
            readof.readscalar(root, "0.5", "alpha", boundary="top", verbose=False)
        except NotImplementedError:
            pass
        else:
            raise AssertionError("NotImplementedError expected")

    def test_openfoamfile_public_attributes(self):
        # lines_stripped and boundary are computed on demand but stay available
        root, _ = _case()
        f = readof.OpenFoamFile(
            os.path.join(root, "processor0"), "0.5", "alpha", verbose=False
        )
        assert (
            f._lines_stripped is None and f._boundary is None
        )  # not computed yet
        assert f.header[b"format"] == b"ascii"
        assert f.dimensions == (0, 0, 0, 0, 0, 0, 0)
        assert f.lines_stripped[0] == b"FoamFile"
        assert b"top" in f.boundary
        f.boundary = {"custom": 1}  # still assignable
        assert f.boundary == {"custom": 1}

    def test_binary_uncollated(self):
        root, _ = _case()
        np.testing.assert_allclose(
            readof.readscalar(root, "0.5", "alphab", verbose=False), ALPHA
        )

    def test_collated_fields(self):
        root, _ = _collated_case()
        assert not [
            d
            for d in os.listdir(root)
            if d.startswith("processor") and d[9:10] != "s"
        ]
        np.testing.assert_allclose(
            readof.readscalar(root, "0.5", "alpha", verbose=False), ALPHA
        )
        np.testing.assert_allclose(
            readof.readscalar(root, "0.5", "alphab", verbose=False), ALPHA
        )  # binary
        np.testing.assert_allclose(
            readof.readvector(root, "0.5", "U", verbose=False), U
        )
        np.testing.assert_allclose(
            readof.readscalar(root, "0.5", "beta", verbose=False), BETA
        )  # uniform on 1 proc
        np.testing.assert_allclose(
            readof.readfield(root, "0.5", "alpha", verbose=False), ALPHA
        )
        a_s = readof.readscalar(
            root, "0.5", "alpha", structured=True, verbose=False
        )
        assert a_s.shape == (1, 1, NCELLS)

    def test_collated_latest_time_priority_typefield(self):
        root, _ = _collated_case()
        np.testing.assert_allclose(
            readof.readscalar(root, "latestTime", "alpha", verbose=False), ALPHA
        )
        np.testing.assert_allclose(
            readof.readscalar(root, "0", "alpha", verbose=False), 99.0
        )
        assert readof.typefield(root, "0.5", "U", verbose=False) == "vector"

    def test_collated_mesh_without_root_mesh(self):
        _, nomesh = _collated_case()
        x, y, z = readof.readmesh(nomesh, verbose=False)
        np.testing.assert_allclose(z, ZC)
        np.testing.assert_allclose(x, 0.5)

    def test_collated_dynamic_mesh(self):
        root, _ = _collated_case()
        x, y, z = readof.readmesh(root, time_name="0.5", verbose=False)
        np.testing.assert_allclose(z, ZC + DZ)


if __name__ == "__main__":
    unittest.main()
