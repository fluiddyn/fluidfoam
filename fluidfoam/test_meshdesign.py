import unittest

import fluidfoam 
 

class SimpleTestCase(unittest.TestCase):
    def test_meshdesign(self):
        print('meshdesign TestCase')
        z, dz, gz = fluidfoam.getgz(1., 0.001, 20)
        z, dz, gz = fluidfoam.getgz(1., 0.1, 20)
        dz, dN = fluidfoam.getdzs(1., 0.1, 20)
        dz, dN = fluidfoam.getdzs(1., 10, 20)
            
