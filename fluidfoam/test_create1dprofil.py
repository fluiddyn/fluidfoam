
import unittest

import fluidfoam

sol = 'output_samples/'
timenames = ['0.bin', '0.ascii', '0.bingz', '0.asciigz']

size = 64


class SimpleTestCase(unittest.TestCase):

    def test_functions(self):
        for timename in timenames:
#            alpha1 = readscalar(sol, timename, 'alpha', (2, size//2))
            fluidfoam.create1dprofil(sol, sol, timename, ['alpha', 'U'])

