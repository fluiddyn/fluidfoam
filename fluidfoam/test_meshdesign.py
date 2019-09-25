import unittest

import fluidfoam


class SimpleTestCase(unittest.TestCase):
    def test_meshdesign(self):
        print('meshdesign TestCase')
        z, dummy, dummy = fluidfoam.getgz(1., 0.001, 20)
        z, dz, dummy = fluidfoam.getgz(1., 0.1, 20)
        dz, dummy = fluidfoam.getdzs(1., 0.1, 20)
        dz, dummy = fluidfoam.getdzs(1., 10, 20)

