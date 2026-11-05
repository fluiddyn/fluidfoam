"""Quality tests for readof: error handling, robustness and API of the
fixes made for the 0.4.0 release.

A tiny synthetic case is built on the fly (no OpenFOAM installation
needed) to check:

* a nonexistent boundary raises ValueError (no longer sys.exit),
* a boundaryField value written as a multiline nonuniform List<...>
  is read correctly (a pre-0.4.0 IndexError),
* a compact one-line FoamFile header ("FoamFile { version 2.0; ... }")
  is parsed correctly (a pre-0.4.0 silent failure),
* getVolumes reads a decomposed case (cells scattered back in the
  global order thanks to cellProcAddressing),
* set_nthreads accepts ints and rejects invalid values.

"""

import os
import tempfile
import unittest

import numpy as np

try:
    from fluidfoam import readof
except ImportError:  # standalone use
    import readof

HEADER = """FoamFile
{{
    version     2.0;
    format      ascii;
    class       {cls};
    object      {obj};
}}

"""

MESH_BOUNDARY = HEADER.format(cls="polyBoundaryMesh", obj="boundary") + """3
(
inlet
{
    type            patch;
    startFace       0;
    nFaces          2;
}
outlet
{
    type            patch;
    startFace       2;
    nFaces          2;
}
top
{
    type            patch;
    startFace       4;
    nFaces          1;
}
)

"""

MESH_OWNER = HEADER.format(cls="labelList", obj="owner") + """5
(0 1 2 3 3)

"""


def _write_case(tmpdir):
    """A 4-cell case with patches inlet (2 faces), outlet (2 faces)."""
    mesh = os.path.join(tmpdir, "constant", "polyMesh")
    os.makedirs(mesh, exist_ok=True)
    os.makedirs(os.path.join(tmpdir, "0"), exist_ok=True)
    with open(os.path.join(mesh, "boundary"), "w") as f:
        f.write(MESH_BOUNDARY)
    with open(os.path.join(mesh, "owner"), "w") as f:
        f.write(MESH_OWNER)

    # scalar field, multiline nonuniform internalField
    with open(os.path.join(tmpdir, "0", "alpha"), "w") as f:
        f.write(
            HEADER.format(cls="volScalarField", obj="alpha")
            + """dimensions [0 0 0 0 0 0 0];

internalField nonuniform List<scalar>
4
(1.1
2.2
3.3
4.4)
;

boundaryField
{
    inlet
    {
        type            fixedValue;
        value           nonuniform List<scalar>
2
(9.9
8.8)
;
    }
    outlet
    {
        type            zeroGradient;
    }
    top
    {
        type            fixedValue;
        value           uniform 7.7;
    }
}

"""
        )

    # vector field, multiline nonuniform value on a patch
    with open(os.path.join(tmpdir, "0", "U"), "w") as f:
        f.write(
            HEADER.format(cls="volVectorField", obj="U")
            + """dimensions [0 1 -1 0 0 0 0];

internalField nonuniform List<vector>
4
(
(0 0 0)
(1 1 1)
(2 2 2)
(3 3 3)
)
;

boundaryField
{
    inlet
    {
        type            fixedValue;
        value           nonuniform List<vector>
2
(
(0.1 0.2 0.3)
(0.4 0.5 0.6)
)
;
    }
    outlet
    {
        type            zeroGradient;
    }
}

"""
        )


class QualityTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.path = self._tmpdir.name
        _write_case(self.path)

    def test_nonexistent_boundary_raises_valueerror(self):
        # a nonexistent patch must raise, not sys.exit the process
        with self.assertRaises(ValueError):
            readof.OpenFoamFile(
                self.path,
                time_name="0",
                name="alpha",
                boundary="nosuchpatch",
                verbose=False,
            )

    def test_multiline_nonuniform_boundary_value(self):
        # "value nonuniform List<scalar>" followed by data on the next
        # lines used to crash with IndexError (pre-0.4.0)
        alpha = readof.OpenFoamFile(
            self.path,
            time_name="0",
            name="alpha",
            boundary="inlet",
            verbose=False,
        )
        self.assertEqual(alpha.values.size, 2)
        self.assertAlmostEqual(alpha.values[0], 9.9)
        self.assertAlmostEqual(alpha.values[1], 8.8)

        u = readof.OpenFoamFile(
            self.path,
            time_name="0",
            name="U",
            boundary="inlet",
            verbose=False,
        )
        self.assertEqual(u.values.size, 6)
        for got, expected in zip(u.values, [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]):
            self.assertAlmostEqual(got, expected)

    def test_uniform_boundary_value(self):
        alpha = readof.OpenFoamFile(
            self.path,
            time_name="0",
            name="alpha",
            boundary="top",
            verbose=False,
        )
        self.assertEqual(alpha.values.size, 1)
        self.assertAlmostEqual(alpha.values[0], 7.7)

    def test_compact_one_line_header(self):
        # a compact header (everything on one line) used to yield an empty
        # header and a silent parsing failure (pre-0.4.0)
        path = os.path.join(self.path, "0", "pcompact")
        with open(path, "w") as f:
            f.write(
                "FoamFile { version 2.0; format ascii; "
                "class volScalarField; object p; }\n"
                "dimensions [0 2 -1 0 0 0 0];\n\n"
                "internalField nonuniform List<scalar>\n2\n(1.5\n2.5)\n;\n"
            )
        field = readof.OpenFoamFile(
            os.path.dirname(path),
            name=os.path.basename(path),
            verbose=False,
        )
        self.assertEqual(field.type_data, "scalar")
        self.assertEqual(field.values.size, 2)
        self.assertAlmostEqual(field.values[0], 1.5)
        self.assertAlmostEqual(field.values[1], 2.5)
        self.assertEqual(field.dimensions, (0, 2, -1, 0, 0, 0, 0))

    def test_getvolumes_decomposed(self):
        # a 4-cell column split on 2 processors; the cells must come back
        # in the global order thanks to cellProcAddressing. A separate
        # directory is used: the fallback triggers only when the root case
        # has no constant/polyMesh.
        decdir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(decdir))
        header = (
            "FoamFile\n{\n    version     2.0;\n    format      ascii;\n"
            "    class       %s;\n    object      %s;\n}\n\n"
        )

        def write_mesh(root, ncells, z0):
            mesh = os.path.join(root, "constant", "polyMesh")
            os.makedirs(mesh, exist_ok=True)
            pts = [
                (x, y, z0 + k)
                for k in range(ncells + 1)
                for (x, y) in ((0, 0), (1, 0), (1, 1), (0, 1))
            ]
            with open(os.path.join(mesh, "points"), "w") as f:
                f.write(header % ("vectorArray", "points"))
                f.write("%d\n(\n" % len(pts))
                for p in pts:
                    f.write("(%g %g %g)\n" % p)
                f.write(")\n\n")
            faces, owner, neigh = [], [], []
            for k in range(1, ncells):
                faces.append([4 * k + j for j in range(4)])
                owner.append(k - 1)
                neigh.append(k)
            faces.append([0, 1, 2, 3])
            owner.append(0)
            faces.append([4 * ncells + j for j in range(4)])
            owner.append(ncells - 1)
            for c in range(ncells):
                for j in range(4):
                    faces.append(
                        [
                            4 * c + j,
                            4 * c + (j + 1) % 4,
                            4 * (c + 1) + (j + 1) % 4,
                            4 * (c + 1) + j,
                        ]
                    )
                    owner.append(c)
            for name, cls, values in (
                ("faces", "faceList", None),
                ("owner", "labelList", owner),
                ("neighbour", "labelList", neigh),
            ):
                with open(os.path.join(mesh, name), "w") as f:
                    f.write(header % (cls, name))
                    if values is None:
                        f.write("%d\n(\n" % len(faces))
                        for fc in faces:
                            f.write(
                                "%d(%s)\n"
                                % (len(fc), " ".join(str(i) for i in fc))
                            )
                        f.write(")\n\n")
                    else:
                        f.write(
                            "%d\n(%s)\n\n"
                            % (len(values), " ".join(str(v) for v in values))
                        )
            with open(os.path.join(mesh, "boundary"), "w") as f:
                f.write(header % ("polyBoundaryMesh", "boundary"))
                f.write("0\n()\n\n")

        write_mesh(os.path.join(decdir, "processor0"), 2, 0)
        write_mesh(os.path.join(decdir, "processor1"), 2, 2)
        for pdir, addr in (
            ("processor0", [0, 1]),
            ("processor1", [2, 3]),
        ):
            ap = os.path.join(
                decdir, pdir, "constant", "polyMesh", "cellProcAddressing"
            )
            with open(ap, "w") as f:
                f.write(header % ("labelList", "cellProcAddressing"))
                f.write(
                    "%d\n(%s)\n\n" % (len(addr), " ".join(str(a) for a in addr))
                )

        centroids, volumes = readof.getVolumes(decdir, verbose=False)
        expected = np.array(
            [[0.5, 0.5, 0.5], [0.5, 0.5, 1.5], [0.5, 0.5, 2.5], [0.5, 0.5, 3.5]]
        )
        self.assertTrue(np.allclose(centroids, expected))
        self.assertTrue(np.allclose(volumes, 1.0))

        # box and structured are not supported on decomposed cases
        with self.assertRaises(NotImplementedError):
            readof.getVolumes(decdir, box=((0, 0, 0), (1, 1, 1)))
        with self.assertRaises(NotImplementedError):
            readof.getVolumes(decdir, structured=True)

    def test_set_nthreads(self):
        old = readof.NTHREADS
        self.addCleanup(readof.set_nthreads, old)
        for n in (-1, 0, 1, 4):
            readof.set_nthreads(n)
            self.assertEqual(readof.NTHREADS, int(n))
        with self.assertRaises(ValueError):
            readof.set_nthreads("notanumber")

    def test_effective_nthreads(self):
        old = readof.NTHREADS
        self.addCleanup(readof.set_nthreads, old)
        readof.set_nthreads(0)
        self.assertEqual(readof._effective_nthreads(8), 1)
        readof.set_nthreads(1)
        self.assertEqual(readof._effective_nthreads(8), 1)
        readof.set_nthreads(4)
        self.assertEqual(readof._effective_nthreads(2), 2)
        self.assertEqual(readof._effective_nthreads(16), 4)
        readof.set_nthreads(-1)
        self.assertEqual(readof._effective_nthreads(1), 1)
        self.assertGreaterEqual(readof._effective_nthreads(64), 2)


if __name__ == "__main__":
    unittest.main()
