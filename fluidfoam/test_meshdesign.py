import unittest

import fluidfoam


h, gz, N = 6., 2., 30

class SimpleTestCase(unittest.TestCase):
    def test_meshdesign(self):
        print("meshdesign TestCase")
        dummy, dummy, dummy = fluidfoam.getgz(1.0, 0.001, 20)
        dummy, dummy, dummy = fluidfoam.getgz(1.0, 0.1, 20)
        dummy, dummy = fluidfoam.getdzs(1.0, 0.1, 20)
        dummy, dummy = fluidfoam.getdzs(1.0, 10, 20)
        dz, dummy = fluidfoam.meshdesign.getdzs(h,gz,N)
        gztest = fluidfoam.meshdesign.getgz(h,dz,N)[2]
        print(gz,gztest)
        self.assertEqual(gz, round(gztest,5))
        
