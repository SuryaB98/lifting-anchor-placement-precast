"""
Unit tests for Anchor Placement & Rig Decision module (§3.4, §3.5).
"""

import unittest
from lifting_core.geometry import ElementGeometry, RectOpening
from lifting_core.placement import PlacementEngine

class TestPlacement(unittest.TestCase):

    def test_spreader_beam_enforced_for_thin_wall(self):
        # 180mm panel thickness < 240mm ARL-42 transverse min wall
        geom = ElementGeometry(length_mm=4700.0, height_mm=3000.0, thickness_mm=180.0)
        engine = PlacementEngine(geometry=geom, anchor_type="ARL-42")

        rig = engine.evaluate_rig_requirement(proposed_beta_deg=15.0)
        self.assertTrue(rig.spreader_required)
        self.assertEqual(rig.sling_angle_deg, 0.0)
        self.assertIn("240mm", rig.reason)

    def test_anchor_positions_align_with_cog(self):
        geom = ElementGeometry(length_mm=4700.0, height_mm=3000.0, thickness_mm=180.0)
        engine = PlacementEngine(geometry=geom, anchor_type="ARL-42")

        anchors, warnings = engine.calculate_anchor_positions()
        a1, a2 = anchors[0], anchors[1]

        # Midpoint must equal X_CoG (2350mm for solid panel)
        midpoint = (a1.x_mm + a2.x_mm) / 2.0
        self.assertAlmostEqual(midpoint, 2350.0, places=1)
        self.assertEqual(len(warnings), 0)

if __name__ == "__main__":
    unittest.main()
