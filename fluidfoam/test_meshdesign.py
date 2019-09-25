import unittest

import fluidfoam


class SimpleTestCase(unittest.TestCase):
    def test_meshdesign(self):
        print('meshdesign TestCase')
        dummy, dummy, dummy = fluidfoam.getgz(1., 0.001, 20)
        dummy, dummy, dummy = fluidfoam.getgz(1., 0.1, 20)
        dummy, dummy = fluidfoam.getdzs(1., 0.1, 20)
        dummy, dummy = fluidfoam.getdzs(1., 10, 20)

