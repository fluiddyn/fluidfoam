import unittest
import numpy as np
import fluidfoam
import matplotlib
matplotlib.use('Agg')

sols = ['output_samples/ascii/', 'output_samples/bin/',
        'output_samples/bingz/', 'output_samples/asciigz/']
timename = '0'

size = 64


class SimpleTestCase(unittest.TestCase):

    def test_functions(self):
        for sol in sols:
            fluidfoam.create1dprofil(sol, sol, timename, 'Y', ['alpha', 'U'])
            fluidfoam.create1dprofil(sol, sol, timename, 'Y', ['alphauniform', 'Uuniform'])
            filename = sol+'1d_profil/alpha.xy'
            z, field, size = fluidfoam.read1dprofil(filename)
            fluidfoam.create1dprofil_spe(sol, z, field, 'epsilon', 'scalar')
            vecfield = np.zeros((3, size))
            fluidfoam.create1dprofil_spe(sol, z, 0.2*vecfield, 'zerodeuxU', 'vector')
            fluidfoam.plot1dprofil(sol+"1d_profil/", ['alpha', 'U1'])
