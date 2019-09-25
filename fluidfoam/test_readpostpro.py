import unittest

import fluidfoam

case = 'output_samples/ascii'
probes_name = 'probes'


class SimpleTestCase(unittest.TestCase):
    def test_read_forces(self):
        forces = fluidfoam.readforce(case)
        #self.assertEqual(1, len(postpro.forcedirs))
        print('create force object')

    def test_read_probes(self):
        time_vect, tab = fluidfoam.readprobes(case)
        self.assertEqual(10, len(time_vect))
