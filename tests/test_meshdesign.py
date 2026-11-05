import unittest

import numpy as np

from fluidfoam import getdzs, getgz


class UniformMeshTestCase(unittest.TestCase):
    """Uniform mesh: dz1 == h / N must give gz = 1."""

    def test_uniform(self):
        z, dz, gz = getgz(1.0, 0.05, 20)
        self.assertEqual(gz, 1.0)
        self.assertAlmostEqual(dz.sum(), 1.0)
        np.testing.assert_allclose(dz, 0.05)


class GradedMeshTestCase(unittest.TestCase):
    """Properties that any geometric grading must satisfy."""

    def test_geometric_sequence(self):
        h, dz1, N = 1.0, 0.001, 20
        z, dz, gz = getgz(h, dz1, N)
        # total size
        self.assertAlmostEqual(dz.sum(), h, places=10)
        # first cell
        self.assertAlmostEqual(dz[0], dz1, places=12)
        # geometric progression: constant ratio between consecutive cells
        ratio = dz[1:] / dz[:-1]
        np.testing.assert_allclose(ratio, ratio[0], rtol=1e-10)
        # grading factor = last / first
        self.assertAlmostEqual(gz, dz[-1] / dz[0], places=10)
        # cell faces from 0 to h
        self.assertAlmostEqual(z[0], 0.0, places=12)
        self.assertAlmostEqual(z[-1], h, places=10)
        self.assertEqual(z.shape[0], N + 1)

    def test_reciprocity(self):
        """getdzs and getgz must be reciprocal (within the accuracy of
        the polynomial-root inversion, ~1e-10 here)."""
        h, gz, N = 6.0, 2.0, 30
        dz1, dzN = getdzs(h, gz, N)
        self.assertAlmostEqual(gz, dzN / dz1, places=10)
        z, dz, gz_back = getgz(h, dz1, N)
        self.assertAlmostEqual(gz, gz_back, places=5)


class ReferenceValuesTestCase(unittest.TestCase):
    """Documented reference values, computed analytically.

    For h = 1, N = 2 and first cell dz1 = 0.25:
    dz0 + dz1 = 0.25 + 0.25 * r = 1  =>  r = 3
    grading gz = r ** (N - 1) = 3
    """

    def test_reference_two_cells(self):
        z, dz, gz = getgz(1.0, 0.25, 2)
        self.assertAlmostEqual(gz, 3.0)
        np.testing.assert_allclose(dz, [0.25, 0.75])
        np.testing.assert_allclose(z, [0.0, 0.25, 1.0])

    def test_reference_three_cells(self):
        # dz: 0.1, 0.2, 0.4  (r = 2, h = 0.7, gz = 4)
        z, dz, gz = getgz(0.7, 0.1, 3)
        self.assertAlmostEqual(gz, 4.0)
        np.testing.assert_allclose(dz, [0.1, 0.2, 0.4])
        self.assertAlmostEqual(dz.sum(), 0.7)
        np.testing.assert_allclose(z, [0.0, 0.1, 0.3, 0.7])

    def test_getdzs_uniform(self):
        dz1, dzN = getdzs(1.0, 1.0, 10)
        self.assertAlmostEqual(dz1, 0.1)
        self.assertAlmostEqual(dzN, 0.1)


class ErrorHandlingTestCase(unittest.TestCase):
    """Infeasible parameters must raise, not return garbage."""

    def test_infeasible_raises(self):
        # dz1 > h: the first cell alone exceeds the domain, no geometric
        # grading can exist
        with self.assertRaises(ValueError):
            getgz(1.0, 1.5, 10)

    def test_uniform_bugfix(self):
        """getdzs with gz == 1 (int or float) must give the uniform mesh.

        The previous implementation returned h/(N-1)-ish values for
        integer gz == 1; this documents the corrected behaviour.
        """
        dz1, dzN = getdzs(1.0, 1, 20)
        self.assertAlmostEqual(dz1, 0.05)
        self.assertAlmostEqual(dzN, 0.05)
        dz1, dzN = getdzs(1.0, 1.0, 20)
        self.assertAlmostEqual(dz1, 0.05)
        self.assertAlmostEqual(dzN, 0.05)


if __name__ == "__main__":
    unittest.main()
