"""
Unit tests for Anchor Catalogue module (§3.3).
"""

import unittest
from lifting_core.catalogue import get_anchor_spec, ANCHOR_CATALOGUE, AnchorSpec

class TestCatalogue(unittest.TestCase):

    def test_arl42_capacity_by_strength(self):
        arl42 = get_anchor_spec("ARL-42")
        self.assertEqual(arl42.get_axial_capacity(15.0), 60.0)
        self.assertEqual(arl42.get_axial_capacity(20.0), 60.0)
        self.assertEqual(arl42.get_axial_capacity(25.0), 75.0)
        self.assertEqual(arl42.get_axial_capacity(30.0), 75.0)
        self.assertEqual(arl42.get_axial_capacity(35.0), 80.0)
        self.assertEqual(arl42.get_axial_capacity(40.0), 80.0)

    def test_arl42_clutch_and_wall_limits(self):
        arl42 = get_anchor_spec("ARL-42")
        self.assertEqual(arl42.clutch, "RU-42")
        self.assertEqual(arl42.min_edge_mm, 500.0)
        self.assertEqual(arl42.min_axis_mm, 1000.0)
        self.assertEqual(arl42.min_wall_axial_mm, 160.0)
        self.assertEqual(arl42.min_wall_transverse_mm, 240.0)

    def test_invalid_strength_raises_error(self):
        arl42 = get_anchor_spec("ARL-42")
        with self.assertRaises(ValueError):
            arl42.get_axial_capacity(10.0)

    def test_unknown_anchor_type(self):
        with self.assertRaises(KeyError):
            get_anchor_spec("NON_EXISTENT_ANCHOR")

if __name__ == "__main__":
    unittest.main()
