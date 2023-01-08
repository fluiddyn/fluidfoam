import unittest
from fluidfoam import create1dprofilDFSEM
import os

sol = "output_samples/DFSEM/"

case3d = "3D/"
case1d = "1D/"

sol1d = os.path.join(sol, case1d)
sol3d = os.path.join(sol, case3d)

timename = "200"
boundary_name = "inlet/"
axis = "Y"



class SimpleTestCase(unittest.TestCase):
    def test_functions(self):
        create1dprofilDFSEM(sol1d, sol3d, boundary_name, "200", axis, 
                    "U","k","omega","turbulenceProperties:R","Y")

