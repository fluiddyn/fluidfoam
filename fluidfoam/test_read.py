
import unittest

# readof functions
import fluidfoam

sol = 'output_samples/'
timenames = ['0.bin', '0.ascii', '0.bingz', '0.asciigz']

# round error (differences bin and ascii)
places = 5

alpha_samples = {0: 1.01583, 6: 1.01875179}

u_samples = {(0, 0): -9.16739310e-01, (1, 0): 1.08239e-01,
             (0, 9): -2.67453e-01, (1, 9): 9.52311e-01,
             (2, 9): 1.02557, (2, 48): 8.95483e-01}
size = 64


class SimpleTestCase(unittest.TestCase):

    def _test_functions(self, readscalar, readsymmtensor, readtensor,
                        readvector, readmesh, readarray):
        for timename in timenames:
            alpha1 = readscalar(sol, timename, 'alpha', (2, size//2))
            sigma1 = readsymmtensor(sol, timename, 'sigma', (2, size//2))
            taus1 = readtensor(sol, timename, 'Taus', (2, size//2))
            alpha = readscalar(sol, timename, 'alpha')
            sigma = readsymmtensor(sol, timename, 'sigma')
            taus = readtensor(sol, timename, 'Taus')
            u2 = readvector(sol, timename, 'U', (2, size//2))
            u1 = readarray(sol, timename, 'U')
            u = readvector(sol, timename, 'U')
            x, y, z = readmesh(sol + timename)
            xx, yy, zz = readmesh(sol + timename, (2, size//2))

            self.assertEqual(size, len(alpha))
            self.assertEqual(size, alpha1.size)
            self.assertEqual(3*size, u.size)
            self.assertEqual(3*size, u1.size)
            self.assertEqual(3*size, u2.size)
            self.assertEqual(6*size, sigma.size)
            self.assertEqual(6*size, sigma1.size)
            self.assertEqual(9*size, taus.size)
            self.assertEqual(9*size, taus1.size)

            for i, v in u_samples.items():
                self.assertAlmostEqual(u1[i], v, places=places)
            for i, v in alpha_samples.items():
                self.assertAlmostEqual(v, alpha[i], places=places)

    def test_read_functions(self):
        self._test_functions(fluidfoam.readscalar, fluidfoam.readsymmtensor,
                             fluidfoam.readtensor, fluidfoam.readvector,
                             fluidfoam.readmesh, fluidfoam.readarray)
        self._test_functions(fluidfoam.readfield, fluidfoam.readfield,
                             fluidfoam.readfield, fluidfoam.readfield,
                             fluidfoam.readmesh, fluidfoam.readfield)
