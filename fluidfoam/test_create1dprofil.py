
import unittest

import fluidfoam

sols = ['output_samples/ascii/', 'output_samples/bin/',
       'output_samples/bingz/', 'output_samples/asciigz/']
timename = '0'

size = 64


class SimpleTestCase(unittest.TestCase):

    def test_functions(self):
        for sol in sols:
            fluidfoam.create1dprofil(sol, sol, timename, ['alpha', 'U'])
            filename = sol+'1d_profil/alpha.xy'
            fluidfoam.read1dprofil(filename)
#            fluidfoam.plot1dprofil(sol+"1d_profil/", ['alpha'])
            fluidfoam.plot1dprofil(sol+"1d_profil/", ['alpha', 'U1'])
