
import unittest

# readof functions
import fluidfoam

sol = 'output_samples/'
timenames = ['0.bin', '0.ascii', '0.bingz', '0.asciigz']

# round error (differences bin and ascii)
places = 5

alpha_samples = {0: 1.01583, 6: 1.01875179}

u_samples = {(0, 0): -9.16739310e-01, (1, 0): 5.48321220e-01,
             (2, 0): 8.80816212e-01}

size = 64


class SimpleTestCase(unittest.TestCase):

    def _test_functions(self, readscalar, readsymmtensor, readtensor,
                        readvector, readmesh):
        for timename in timenames:
            alpha = readscalar(sol, timename, 'alpha')
            sigma = readsymmtensor(sol, timename, 'sigma')
            taus = readtensor(sol, timename, 'Taus')
            u = readvector(sol, timename, 'U')
            x, y, z = readmesh(sol + timename)
            xx, yy, zz = readmesh(sol + timename, (2, size//2))

            self.assertEqual(size, len(alpha))
            self.assertEqual(3*size, u.size)

            for i, v in alpha_samples.items():
                self.assertAlmostEqual(v, alpha[i], places=places)

    def test_read_functions(self):
        self._test_functions(fluidfoam.readscalar, fluidfoam.readsymmtensor,
                             fluidfoam.readtensor, fluidfoam.readvector,
                             fluidfoam.readmesh)
