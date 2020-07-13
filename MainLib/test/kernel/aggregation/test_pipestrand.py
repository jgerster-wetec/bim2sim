﻿import unittest

from bim2sim.kernel import aggregation
from bim2sim.kernel.element import Port
from bim2sim.kernel.elements import Pipe
from bim2sim.kernel.units import ureg

from test.kernel.helper import SetupHelper


class TestPipeStrand(unittest.TestCase):

    helper = None

    @classmethod
    def setUpClass(cls):
        cls.helper = SetupHelper()

    def tearDown(self) -> None:
        self.helper.reset()

    def test_pipestrand1(self):
        """Test calculation of aggregated length and diameter"""
        graph, flags = self.helper.get_setup_simple_boiler()
        elements = flags['strand1']
        match_graph = graph.element_graph.subgraph(elements)

        matches, meta = aggregation.PipeStrand.find_matches(match_graph)
        self.assertEqual(len(matches), 1)
        agg = aggregation.PipeStrand("Test 1", matches[0], **meta[0])

        exp_length = sum([e.length for e in elements]) * ureg.meter
        self.assertAlmostEqual(agg.length, exp_length)

        self.assertAlmostEqual(agg.diameter, 40)

    def test_pipestrand2(self):
        """Test calculation of aggregated length and diameter"""

        graph, flags = self.helper.get_setup_simple_boiler()
        elements = flags['strand2']
        match_graph = graph.element_graph.subgraph(elements)

        matches, meta = aggregation.PipeStrand.find_matches(match_graph)
        self.assertEqual(len(matches), 1)
        agg = aggregation.PipeStrand("Test 2", matches[0], **meta[0])

        exp_length = sum([e.length for e in elements]) * ureg.meter
        self.assertAlmostEqual(agg.length, exp_length)

        self.assertAlmostEqual(agg.diameter, 15)

    def test_basics(self):
        graph, flags = self.helper.get_setup_simple_boiler()
        elements = flags['strand1']
        match = graph.element_graph.subgraph(elements)

        agg = aggregation.PipeStrand("Test", match)

        self.assertTrue(self.helper.elements_in_agg(agg))

    def test_detection(self):
        graph, flags = self.helper.get_setup_simple_boiler()

        matches, meta = aggregation.PipeStrand.find_matches(graph.element_graph)

        self.assertEqual(
            len(matches), 5,
            "There are 5 cases for PipeStrand but 'find_matches' returned %d" % len(matches)
        )


if __name__ == '__main__':
    unittest.main()
