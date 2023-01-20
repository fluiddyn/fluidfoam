import unittest

import fluidfoam

case = "output_samples/ascii"
probes_name = "probes"


class SimpleTestCase(unittest.TestCase):
    def test_read_forces(self):
        dummy = fluidfoam.readforce(case)
        dummy = fluidfoam.readforce(case, time_name="latestTime")
        dummy = fluidfoam.readforce(case, time_name="mergeTime")
        # self.assertEqual(1, len(postpro.forcedirs))
        print("create force object")

    def test_read_probes(self):
        probes_loc, time_vect, dummy = fluidfoam.readprobes(case)
        self.assertEqual(10, len(time_vect))
        probes_loc, time_vect, dummy = fluidfoam.readprobes(case, time_name="latestTime")
        self.assertEqual(6, len(time_vect))
        probes_loc, time_vect, dummy = fluidfoam.readprobes(case, time_name="mergeTime")
        self.assertEqual(13, len(time_vect))
        probes_loc, time_vect, dummy = fluidfoam.readprobes(case, time_name="0", name="p")
