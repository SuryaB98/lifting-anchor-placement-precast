"""
Unit tests for Geometry & Center of Gravity module (§3.5.4).
"""

import unittest
from lifting_core.geometry import ElementGeometry, RectOpening

class TestGeometry(unittest.TestCase):

    def test_solid_panel_cog(self):
        geom = ElementGeometry(
            length_mm=4700.0,
            height_mm=3000.0,
            thickness_mm=180.0,
            density_kg_m3=2400.0
        )
        x_cog, y_cog, z_cog = geom.compute_cog()
        self.assertAlmostEqual(x_cog, 2350.0, places=1)
        self.assertAlmostEqual(y_cog, 1500.0, places=1)
        self.assertAlmostEqual(z_cog, 90.0, places=1)

        # Volume & Mass checks
        # 4.7 * 3.0 * 0.18 = 2.538 m3
        self.assertAlmostEqual(geom.solid_volume_m3, 2.538, places=3)
        # 2.538 * 2400 = 6091.2 kg -> 6.091 tonnes -> ~59.7 kN
        self.assertAlmostEqual(geom.net_mass_kg, 6091.2, places=1)

    def test_panel_with_openings_cog(self):
        openings = [
            RectOpening(id="door", x_mm=1150.0, width_mm=1100.0, sill_mm=0.0, height_mm=2100.0),
            RectOpening(id="window", x_mm=3050.0, width_mm=1200.0, sill_mm=950.0, height_mm=1000.0)
        ]
        geom = ElementGeometry(
            length_mm=4700.0,
            height_mm=3000.0,
            thickness_mm=180.0,
            density_kg_m3=2400.0,
            openings=openings
        )
        x_cog, y_cog, _ = geom.compute_cog()

        # Net CoG shifts off-center due to asymmetric door & window
        self.assertNotEqual(x_cog, 2350.0)
        self.assertTrue(2200.0 < x_cog < 2400.0)

        # Net volume is less than solid volume
        self.assertTrue(geom.net_volume_m3 < geom.solid_volume_m3)

    def test_anchor_clash_detection(self):
        openings = [
            RectOpening(id="door", x_mm=1150.0, width_mm=1100.0, sill_mm=0.0, height_mm=2100.0)
        ]
        geom = ElementGeometry(length_mm=4700.0, height_mm=3000.0, thickness_mm=180.0, openings=openings)

        # Clash inside door void
        has_clash, reason = geom.check_anchor_clash(1500.0, 1000.0)
        self.assertTrue(has_clash)
        self.assertIn("door", reason)

        # Valid anchor on top edge
        has_clash, reason = geom.check_anchor_clash(973.0, 0.0)
        self.assertFalse(has_clash)

if __name__ == "__main__":
    unittest.main()
