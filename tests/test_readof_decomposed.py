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


def write_label_list(path, values, binary=False):
    name = os.path.basename(path)
    head = HEADER.format(
        fmt="binary" if binary else "ascii", cls="labelList", obj=name, note=""
    )
    if binary:
        body = (
            b"%d\n(" % len(values)
            + struct.pack("<%di" % len(values), *values)
            + b")\n"
        )
        _write(path, "", binary=head.encode() + body)
    else:
        _write(
            path,
            head
            + "%d\n(\n" % len(values)
            + "".join("%d\n" % v for v in values)
            + ")\n",
        )


def write_boundary(meshdir, patches):
    """patches: list of (name, type, startFace, nFaces)."""
    text = HEADER.format(
        fmt="ascii", cls="polyBoundaryMesh", obj="boundary", note=""
    )
    text += "%d\n(\n" % len(patches)
    for name, ptype, start, n in patches:
        text += "    %s\n    {\n        type            %s;\n" % (name, ptype)
        if ptype == "processor":
            text += "        myProcNo        0;\n        neighbProcNo    1;\n"
        text += (
            "        nFaces          %d;\n        startFace       %d;\n    }\n"
            % (n, start)
        )
    _write(os.path.join(meshdir, "boundary"), text + ")\n")


def _list_text(values, kind):
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return "nonuniform List<%s> 0()" % kind
    if kind == "scalar":
        rows = "".join("%r\n" % float(v) for v in values)
    else:
        rows = "".join("(%r %r %r)\n" % tuple(map(float, v)) for v in values)
    return "nonuniform List<%s> \n%d\n(\n%s)\n;" % (kind, len(values), rows)


def write_patch_field(path, cls, name, patches):
    """patches: list of (patch name, type, value); value is a number or a
    tuple for a uniform value, an array for a list of values."""
    kind = "scalar" if cls == "volScalarField" else "vector"
    text = HEADER.format(fmt="ascii", cls=cls, obj=name, note="")
    text += "dimensions      [0 0 0 0 0 0 0];\n\n"
    text += "internalField   uniform %s;\n\nboundaryField\n{\n" % (
        "0" if kind == "scalar" else "(0 0 0)"
    )
    for pname, ptype, value in patches:
        if isinstance(value, np.ndarray):
            val = _list_text(value, kind)
        elif isinstance(value, tuple):
            val = "uniform (%s)" % " ".join(map(str, value))
        else:
            val = "uniform %s" % value
        text += (
            "    %s\n    {\n        type            %s;\n        value           %s;\n    }\n"
            % (pname, ptype, val.rstrip(";"))
        )
    _write(path, text + "}\n")


# global reference data ----------------------------------------------------
ZC = np.arange(NCELLS) + 0.5
ALPHA = 10.0 + np.arange(NCELLS)
U = np.stack(
    [np.arange(NCELLS), 2.0 * np.arange(NCELLS), -1.0 * np.arange(NCELLS)]
)
BETA = np.concatenate([np.arange(1, NLOC + 1), np.full(NLOC, 7.0)])
DZ = 0.1  # mesh motion at time 0.5

# patches of the global mesh (faces: internal 23, bottom 23, top 24, walls 25..120)
N_WALLS = 4 * NCELLS
G = np.arange(N_WALLS)
WALLS_D = np.stack(
    [G, 2.0 * G, G + 0.25], axis=1
)  # vector on the walls, global order
WALLS_S = 0.5 * G
UNIFORM_S_PROC0 = 5.5  # scalar on the walls: uniform on processor 0
BOTTOM_D, BOTTOM_S = np.array([[100.0, 200.0, 300.0]]), np.array([9.0])
TOP_D, TOP_S = (7, 7, 7), 7


# local meshes: faces 0..10 internal, 11 = local bottom, 12 = local top (the
# interface between the processors), 13.. the walls (4 per cell)
PROC_PATCHES = [
    [
        ("bottom", "wall", 11, 1),
        ("top", "wall", 61, 0),
        ("walls", "wall", 13, 4 * NLOC),
        ("procBoundary0to1", "processor", 12, 1),
    ],
    [
        ("bottom", "wall", 61, 0),
        ("top", "wall", 11, 1),
        ("walls", "wall", 13, 4 * NLOC),
        ("procBoundary1to0", "processor", 12, 1),
    ],
]
# faceProcAddressing: (global face index + 1), negative if the face is flipped
FACE_ADDR = [
    [m + 1 for m in range(NLOC - 1)]
    + [NCELLS + 1, NLOC]
    + [26 + k for k in range(4 * NLOC)],
    [-(NCELLS - 1 - m) for m in range(NLOC - 1)]
    + [NCELLS + 2, -NLOC]
    + [26 + 4 * (NCELLS - 1 - l) + j for l in range(NLOC) for j in range(4)],
]
# global index (0..95) of the local wall faces of each processor
LOCAL_WALLS = [
    np.arange(4 * NLOC),
    np.array([4 * (NCELLS - 1 - l) + j for l in range(NLOC) for j in range(4)]),
]


def local_patches(p, name):
    """Patch values written in the field file of the processor p.

    The patches that have no face on the processor are written as empty
    lists. The scalar is uniform on the walls of the processor 0, and the
    patch top is uniform (it is only on the processor 1).
    """
    if name == "Dw":
        none = np.zeros((0, 3))
        bottom = BOTTOM_D if p == 0 else none
        top = none if p == 0 else TOP_D
        walls = WALLS_D[LOCAL_WALLS[p]]
        interface = (0, 0, 0)
    else:
        none = np.zeros(0)
        bottom = BOTTOM_S if p == 0 else none
        top = none if p == 0 else TOP_S
        walls = UNIFORM_S_PROC0 if p == 0 else WALLS_S[LOCAL_WALLS[p]]
        interface = 0
    return [
        ("bottom", "calculated", bottom),
        ("top", "calculated", top),
        ("walls", "calculated", walls),
        (PROC_PATCHES[p][3][0], "processor", interface),
    ]


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
    nint = NCELLS - 1
    write_boundary(
        os.path.join(root, "constant", "polyMesh"),
        [
            ("bottom", "wall", nint, 1),
            ("top", "wall", nint + 1, 1),
            ("walls", "wall", nint + 2, N_WALLS),
        ],
    )
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
        meshdir = os.path.join(pdir, "constant", "polyMesh")
        write_label_list(
            os.path.join(meshdir, "faceProcAddressing"),
            FACE_ADDR[p],
            binary=(p == 0),
        )
        write_boundary(meshdir, PROC_PATCHES[p])
        write_patch_field(
            os.path.join(pdir, "0.5", "Dw"),
            "volVectorField",
            "Dw",
            local_patches(p, "Dw"),
        )
        write_patch_field(
            os.path.join(pdir, "0.5", "Sw"),
            "volScalarField",
            "Sw",
            local_patches(p, "Sw"),
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
    # the same case, reconstructed: global mesh and global fields
    ref = root + "_ref"
    shutil.copytree(root, ref, ignore=shutil.ignore_patterns("processor*"))
    write_patch_field(
        os.path.join(ref, "0.5", "Dw"),
        "volVectorField",
        "Dw",
        [
            ("bottom", "calculated", BOTTOM_D),
            ("top", "calculated", TOP_D),
            ("walls", "calculated", WALLS_D),
        ],
    )
    walls_s = WALLS_S.copy()
    walls_s[: 4 * NLOC] = UNIFORM_S_PROC0
    write_patch_field(
        os.path.join(ref, "0.5", "Sw"),
        "volScalarField",
        "Sw",
        [
            ("bottom", "calculated", BOTTOM_S),
            ("top", "calculated", TOP_S),
            ("walls", "calculated", walls_s),
        ],
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
    for f in (
        "cellProcAddressing",
        "faceProcAddressing",
        "boundary",
        "points",
        "faces",
        "owner",
        "neighbour",
    )
]
FIELD_FILES = [
    "0.5/" + f for f in ("alpha", "U", "beta", "Uu", "alphab", "Dw", "Sw")
]
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
            if rel.endswith("faceProcAddressing"):
                blocks.append(
                    _addr_binary(FACE_ADDR[p]).replace(
                        b"cellProcAddressing", b"faceProcAddressing"
                    )
                )
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
    for d in _case() + _collated_case() + (_case()[0] + "_ref",):
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
        for option in ("sets", "region"):
            with self.assertRaises(NotImplementedError):
                readof.readscalar(
                    root, "0.5", "alpha", verbose=False, **{option: "x"}
                )

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

    # ---- option boundary sur un cas décomposé ----------------------------------
    def read_patch(self, case, patch, name="Dw", time="0.5"):
        kind = readof.readscalar if name == "Sw" else readof.readvector
        return kind(case, time, name, boundary=patch, verbose=False)

    def check_patches(self, case):
        """The patches of a decomposed case give what the reconstructed case gives."""
        ref = _case()[0] + "_ref"
        for name in ("Dw", "Sw"):
            for patch in (
                "walls",
                "bottom",
                "top",
            ):  # bottom and top are on one processor only
                with self.subTest(
                    case=os.path.basename(case), field=name, patch=patch
                ):
                    np.testing.assert_array_equal(
                        self.read_patch(case, patch, name),
                        self.read_patch(ref, patch, name),
                    )

    def test_boundary_values_in_the_global_order(self):
        root, nomesh = _case()
        for case in (root, nomesh):
            np.testing.assert_array_equal(
                self.read_patch(case, "walls"), WALLS_D.T
            )
        expected = WALLS_S.copy()
        expected[: 4 * NLOC] = UNIFORM_S_PROC0  # uniform on the processor 0
        np.testing.assert_array_equal(
            self.read_patch(root, "walls", "Sw"), expected
        )
        np.testing.assert_array_equal(self.read_patch(root, "bottom"), BOTTOM_D.T)
        np.testing.assert_array_equal(
            self.read_patch(root, "top"), np.array([TOP_D]).T
        )

    def test_boundary_same_as_the_reconstructed_case(self):
        for case in _case():
            self.check_patches(case)

    def test_boundary_mesh(self):
        root, nomesh = _case()
        x, y, z = readof.readmesh(
            nomesh, boundary="walls", verbose=False
        )  # no root mesh
        xr, yr, zr = readof.readmesh(
            root, boundary="walls", verbose=False
        )  # global mesh
        for a, b in ((x, xr), (y, yr), (z, zr)):
            np.testing.assert_allclose(a, b)
        np.testing.assert_allclose(z, np.repeat(ZC, 4))
        z_bottom = readof.readmesh(nomesh, boundary="bottom", verbose=False)[2]
        z_top = readof.readmesh(nomesh, boundary="top", verbose=False)[2]
        np.testing.assert_allclose([z_bottom[0], z_top[0]], [0.0, float(NCELLS)])

    def test_boundary_dynamic_mesh(self):
        root, _ = _case()
        z = readof.readmesh(
            root, time_name="0.5", boundary="walls", verbose=False
        )[2]
        np.testing.assert_allclose(z, np.repeat(ZC, 4) + DZ)

    def test_boundary_structured_and_errors(self):
        root, nomesh = _case()
        s = readof.readscalar(
            root, "0.5", "Sw", boundary="bottom", structured=True, verbose=False
        )
        assert s.shape == (1, 1, 1) and s[0, 0, 0] == BOTTOM_S[0]
        d = readof.readvector(
            root, "0.5", "Dw", boundary="top", structured=True, verbose=False
        )
        assert d.shape == (3, 1, 1, 1)
        x = readof.readmesh(
            nomesh, boundary="bottom", structured=True, verbose=False
        )
        assert x[0].shape == (1, 1, 1)
        with self.assertRaises(ValueError):
            self.read_patch(root, "unknown")

    def test_collated_boundary(self):
        for case in _collated_case():
            self.check_patches(case)
            np.testing.assert_array_equal(
                self.read_patch(case, "walls"), WALLS_D.T
            )

    def test_collated_boundary_mesh(self):
        root, nomesh = _collated_case()
        ref = _case()[0] + "_ref"
        x, y, z = readof.readmesh(
            nomesh, boundary="walls", verbose=False
        )  # no root mesh
        for a, b in zip(
            (x, y, z), readof.readmesh(ref, boundary="walls", verbose=False)
        ):
            np.testing.assert_allclose(a, b)
        z = readof.readmesh(
            root, time_name="0.5", boundary="walls", verbose=False
        )[2]
        np.testing.assert_allclose(z, np.repeat(ZC, 4) + DZ)


if __name__ == "__main__":
    unittest.main()
