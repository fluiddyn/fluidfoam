
import unittest

# readof functions
import fluidfoam

sols = ['output_samples/ascii/', 'output_samples/bin/',
        'output_samples/bingz/', 'output_samples/asciigz/']
timename = '0'

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
        for sol in sols:
            alpha = readscalar(sol, 'latestTime', 'alpha')
            alpha = readscalar(sol, timename, 'alpha')
            sigma = readsymmtensor(sol, timename, 'sigma')
            dummy = readsymmtensor(sol, timename, 'sigmauniform')
            taus = readtensor(sol, timename, 'Taus')
            readtensor(sol, timename, 'Taus', boundary='top')
            u1 = readarray(sol, timename, 'U')

            u = readvector(sol, 'latestTime', 'U')
            dummy, dummy, dummy = readmesh(sol)
            x, y, dummy = readmesh(sol + timename)

            self.assertEqual(size, len(alpha))
            self.assertEqual(3*size, u.size)
            self.assertEqual(3*size, u1.size)
            self.assertEqual(6*size, sigma.size)
            self.assertEqual(9*size, taus.size)

            for i, v in u_samples.items():
                self.assertAlmostEqual(u1[i], v, places=places)
            for i, v in alpha_samples.items():
                self.assertAlmostEqual(v, alpha[i], places=places)
        alphashort1 = readscalar('output_samples/ascii/', '0', 'alpha10')
        dummy = readscalar('output_samples/ascii/', '0', 'T')
        alphauniform = readscalar('output_samples/ascii/', '0', 'alphauniform')
        readvector('output_samples/ascii/', '0', 'Uuniform')
        alphauniform = readscalar('output_samples/bin/', '0', 'alphauniform')
        x, y, z = readmesh('output_samples/ascii/', boundary='bottom')
        x, y, z = readmesh('output_samples/bin/', boundary='bottom')
        x, y, z = readmesh('output_samples/bin/3d/')
        x, y, z = readmesh('output_samples/bin/3d/', boundary='bottom')
        self.assertEqual(10, len(alphashort1))
        self.assertEqual(1, len(alphauniform))

    def test_read_functions(self):
        self._test_functions(fluidfoam.readscalar, fluidfoam.readsymmtensor,
                             fluidfoam.readtensor, fluidfoam.readvector,
                             fluidfoam.readmesh, fluidfoam.readarray)
        self._test_functions(fluidfoam.readfield, fluidfoam.readfield,
                             fluidfoam.readfield, fluidfoam.readfield,
                             fluidfoam.readmesh, fluidfoam.readfield)
