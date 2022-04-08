import unittest
import numpy as np

from fluidfoam import MeshVisu


simus = [
    "output_samples/box",
    "output_samples/pipeline",
    "output_samples/darrieus",
    "output_samples/ascii",
    "output_samples/bin"]
    

class SimpleTestCase(unittest.TestCase):
    def test_read_mesh(self):
        for simu in simus:
            myMesh = MeshVisu(path=simu)
            
    def test_update_mesh(self):
        myMesh = MeshVisu(path="output_samples/pipeline")
        myMesh.update_box(((0, 0, -1), (0.05, 0.05, 1)))
        
    def test_xz_plane(self):
        myMesh = MeshVisu(path = "output_samples/darrieus",
                          box = ((0, 0, -1), (0.05, 0.05, 1)),
                          time_name = '0.1',
                          plane = 'xz')
                    
    def test_latestTime(self):
        myMesh = MeshVisu(path = "output_samples/box",
                          time_name = 'latestTime')
        
