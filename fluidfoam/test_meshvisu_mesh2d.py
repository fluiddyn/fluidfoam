"""Tests of MeshVisu on small synthetic 2D meshes.

The meshes are written in a temporary directory, so no OpenFoam case is
needed. The tests check the segments returned by ``get_all_edgesInBox``
against what is expected from the geometry:

* a regular grid of NX x NY cells has NX*(NY+1) + NY*(NX+1) distinct segments
  in the plane of the mesh, all of length 1 (no duplicated segment from the
  opposite plane, no zero-length segment from the edges normal to the plane),
* the same holds in the 'xy', 'xz' and 'yz' planes,
* the box, ``update_box`` and ``time_name`` options.
"""

import os
import shutil
import tempfile
import unittest

import numpy as np

from fluidfoam import MeshVisu

NX, NY = 5, 4  # number of cells of the grid
DZ = 0.1  # thickness of the mesh (third direction)
SHIFT = 0.5  # displacement along x of the points written in a time directory
N_SEGMENTS = NX * (NY + 1) + NY * (NX + 1)  # distinct segments of the grid

PLANES = ("xy", "xz", "yz")


def _header(cls, obj):
    return (
        "FoamFile\n{\n    version     2.0;\n    format      ascii;\n"
        "    class       %s;\n    object      %s;\n}\n\n" % (cls, obj)
    )


def _write_points(directory, points, shift=0.0):
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, "points"), "w") as f:
        f.write(_header("vectorField", "points"))
        f.write("%d\n(\n" % len(points))
        for x, y, z in points:
            f.write("(%r %r %r)\n" % (float(x) + shift, float(y), float(z)))
        f.write(")\n")


def _write_faces(directory, faces):
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, "faces"), "w") as f:
        f.write(_header("faceList", "faces"))
        f.write("%d\n(\n" % len(faces))
        for face in faces:
            f.write("%d(%s)\n" % (len(face), " ".join(str(p) for p in face)))
        f.write(")\n")


def _write_case(root, points, faces):
    """constant/polyMesh/{points,faces} and a time directory 0.1 whose points
    are shifted along x (as in a moving mesh)."""
    _write_points(os.path.join(root, "constant", "polyMesh"), points)
    _write_faces(os.path.join(root, "constant", "polyMesh"), faces)
    _write_points(os.path.join(root, "0.1", "polyMesh"), points, shift=SHIFT)


def _grid(nx, ny, plane):
    """Points and faces of a grid of nx x ny cells, one cell thick.

    In the 2D coordinates of the plane, the grid is [0, nx] x [0, ny]; the
    thickness DZ is along the direction normal to the plane.
    """
    place = {
        "xy": lambda i, j, k: (i, j, k * DZ),
        "xz": lambda i, j, k: (i, k * DZ, j),
        "yz": lambda i, j, k: (k * DZ, i, j),
    }[plane]
    nlayer = (nx + 1) * (ny + 1)

    def p(i, j, k):
        return k * nlayer + j * (nx + 1) + i

    points = [
        place(i, j, k)
        for k in (0, 1)
        for j in range(ny + 1)
        for i in range(nx + 1)
    ]
    faces = []
    for j in range(ny):
        for i in range(nx):  # faces in the two planes of the mesh
            faces.append(
                [p(i, j, 0), p(i, j + 1, 0), p(i + 1, j + 1, 0), p(i + 1, j, 0)]
            )
            faces.append(
                [p(i, j, 1), p(i + 1, j, 1), p(i + 1, j + 1, 1), p(i, j + 1, 1)]
            )
    for j in range(ny):
        for i in range(nx + 1):  # faces normal to the first direction
            faces.append([p(i, j, 0), p(i, j + 1, 0), p(i, j + 1, 1), p(i, j, 1)])
    for j in range(ny + 1):
        for i in range(nx):  # faces normal to the second direction
            faces.append([p(i, j, 0), p(i + 1, j, 0), p(i + 1, j, 1), p(i, j, 1)])
    return points, faces


def _box(plane, lo, hi):
    """3D box from a rectangle (lo, hi) given in the 2D coordinates of the plane."""
    if plane == "xy":
        return ((lo[0], lo[1], -1), (hi[0], hi[1], 1))
    if plane == "xz":
        return ((lo[0], -1, lo[1]), (hi[0], 1, hi[1]))
    return ((-1, lo[0], lo[1]), (1, hi[0], hi[1]))


def _segments(mesh):
    """Segments of the mesh as an array of shape (n, 2, 2)."""
    return np.array(mesh.get_all_edgesInBox(), dtype=float).reshape(-1, 2, 2)


def _as_set(segments):
    """Set of segments, independent of their orientation and order."""
    return {tuple(sorted(map(tuple, seg))) for seg in segments.tolist()}


class MeshVisuMesh2DTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="fluidfoam_meshvisu_")
        cls.cases = {}
        for plane in PLANES:
            root = os.path.join(cls.tmp, "grid_" + plane)
            _write_case(root, *_grid(NX, NY, plane))
            cls.cases[plane] = root

        # one triangular prism: mixed triangular and quadrangular faces
        prism = os.path.join(cls.tmp, "prism")
        points = [
            (0, 0, 0),
            (1, 0, 0),
            (0, 1, 0),
            (0, 0, DZ),
            (1, 0, DZ),
            (0, 1, DZ),
        ]
        faces = [[0, 2, 1], [3, 4, 5], [0, 1, 4, 3], [1, 2, 5, 4], [2, 0, 3, 5]]
        _write_case(prism, points, faces)
        cls.prism = prism

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def mesh(self, plane, **kwargs):
        return MeshVisu(
            path=self.cases[plane], plane=plane, verbose=False, **kwargs
        )

    def test_number_of_segments(self):
        for plane in PLANES:
            with self.subTest(plane=plane):
                self.assertEqual(
                    len(self.mesh(plane).get_all_edgesInBox()), N_SEGMENTS
                )

    def test_no_zero_length_segment(self):
        for plane in PLANES:
            with self.subTest(plane=plane):
                seg = _segments(self.mesh(plane))
                length = np.linalg.norm(seg[:, 0] - seg[:, 1], axis=1)
                self.assertTrue(np.all(length > 0))

    def test_segments_are_the_edges_of_the_grid(self):
        # all the edges of a regular grid have a length 1 and are aligned with
        # an axis; no segment is listed twice
        for plane in PLANES:
            with self.subTest(plane=plane):
                seg = _segments(self.mesh(plane))
                length = np.linalg.norm(seg[:, 0] - seg[:, 1], axis=1)
                np.testing.assert_allclose(length, 1.0)
                self.assertEqual(len(_as_set(seg)), len(seg))
                self.assertEqual(seg[..., 0].min(), 0)
                self.assertEqual(seg[..., 0].max(), NX)
                self.assertEqual(seg[..., 1].min(), 0)
                self.assertEqual(seg[..., 1].max(), NY)

    def test_triangular_faces(self):
        # the segments of the triangle in the plane of the mesh
        mesh = MeshVisu(path=self.prism, verbose=False)
        seg = _segments(mesh)
        length = np.sort(np.linalg.norm(seg[:, 0] - seg[:, 1], axis=1))
        np.testing.assert_allclose(length, [1.0, 1.0, np.sqrt(2.0)])

    def test_box_keeps_the_segments_with_a_point_inside(self):
        lo, hi = (0, 0), (2, 2)
        for plane in PLANES:
            with self.subTest(plane=plane):
                full = _segments(self.mesh(plane))
                boxed = _segments(self.mesh(plane, box=_box(plane, lo, hi)))

                def inside(p):
                    return (
                        (lo[0] <= p[..., 0])
                        & (p[..., 0] <= hi[0])
                        & (lo[1] <= p[..., 1])
                        & (p[..., 1] <= hi[1])
                    )

                expected = full[inside(full[:, 0]) | inside(full[:, 1])]
                self.assertGreater(len(expected), 0)
                self.assertLess(len(expected), len(full))
                self.assertEqual(_as_set(boxed), _as_set(expected))

    def test_update_box(self):
        for plane in PLANES:
            with self.subTest(plane=plane):
                box = _box(plane, (1, 1), (3, 3))
                mesh = self.mesh(plane)
                mesh.update_box(box, verbose=False)
                self.assertEqual(mesh.get_box(), box)
                reference = self.mesh(plane, box=box)
                self.assertEqual(
                    _as_set(_segments(mesh)), _as_set(_segments(reference))
                )

    def test_default_box_is_the_mesh_size(self):
        mesh = self.mesh("xy")
        self.assertEqual(mesh.get_xlim(), (0, NX))
        self.assertEqual(mesh.get_ylim(), (0, NY))
        self.assertEqual(mesh.get_zlim(), (0, DZ))
        mesh.update_box(_box("xy", (1, 1), (2, 2)), verbose=False)
        self.assertEqual(mesh.get_xlim(), (1, 2))
        self.assertLess(len(mesh.get_all_edgesInBox()), N_SEGMENTS)
        # the segments are updated together with the box
        mesh.set_box_to_mesh_size()
        self.assertEqual(mesh.get_xlim(), (0, NX))
        self.assertEqual(len(mesh.get_all_edgesInBox()), N_SEGMENTS)

    def test_invalid_box(self):
        with self.assertRaises(ValueError):
            self.mesh("xy", box=((0, 0), (1, 1)))

    def test_time_name(self):
        # the points of the time directory are shifted along x
        reference = _segments(self.mesh("xy"))
        for time_name in ("0.1", "latestTime"):
            with self.subTest(time_name=time_name):
                mesh = self.mesh("xy", time_name=time_name)
                seg = _segments(mesh)
                self.assertEqual(len(seg), N_SEGMENTS)
                np.testing.assert_allclose(seg[..., 0].min(), SHIFT)
                np.testing.assert_allclose(seg[..., 0].max(), NX + SHIFT)
                self.assertEqual(_as_set(seg - [SHIFT, 0]), _as_set(reference))


if __name__ == "__main__":
    unittest.main()
