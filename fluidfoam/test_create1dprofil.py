
import unittest

import fluidfoam

sol = 'output_samples/'
timenames = ['0.bin', '0.ascii', '0.bingz', '0.asciigz']

size = 64


class SimpleTestCase(unittest.TestCase):

    def test_functions(self):
        for timename in timenames:
            fluidfoam.create1dprofil(sol, sol, timename, ['alpha', 'U'])
            filename = "output_samples/1d_profil/alpha.xy"
            fluidfoam.read1dprofil(filename)
#            fluidfoam.plot1dprofil(sol+"1d_profil/", ['alpha'])
            fluidfoam.plot1dprofil(sol+"1d_profil/", ['alpha', 'U1'])

