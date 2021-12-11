import unittest
import numpy as np

from fluidfoam import OpenFoamSimu

case = "output_samples"
simu = "box"
timeStep = "4"

class SimpleTestCase(unittest.TestCase):
    def test_read_simu(self):
        mySimu = OpenFoamSimu(path=case, simu=simu, timeStep=timeStep, structured=True)
        keys = mySimu.keys()
        self.assertEqual(np.mean(mySimu.U), 0.03630165464270426)
