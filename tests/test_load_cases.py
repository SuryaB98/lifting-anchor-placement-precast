"""
Unit tests for Load Cases module (§3.1, §3.2).
"""

import unittest
from lifting_core.load_cases import LoadCaseEngine

class TestLoadCases(unittest.TestCase):

    def test_demould_load_includes_adhesion(self):
        # 72.6 kN self-weight, 14.1 m2 face area
        engine = LoadCaseEngine(self_weight_G_kN=72.6, face_area_m2=14.1, n_anchors=2)
        checks = engine.compute_all_states(beta_deg=0.0, q_adh_kN_m2=1.0, turn_method="UNCONFIRMED")

        demould = [c for c in checks if c.state_name == "demould"][0]
        self.assertEqual(demould.strength_mpa, 15.0)
        self.assertEqual(demould.extra_load_kN, 14.1)

        # Expected F_demould = (72.6 * 1.3 + 14.1) * 1.0 / 2 = (94.38 + 14.1) / 2 = 54.24 kN
        self.assertAlmostEqual(demould.f_per_anchor_kN, 54.24, places=1)

    def test_transport_load_uses_psi_2(self):
        engine = LoadCaseEngine(self_weight_G_kN=72.6, face_area_m2=14.1, n_anchors=2)
        checks = engine.compute_all_states(beta_deg=0.0, turn_method="UNCONFIRMED")

        transport = [c for c in checks if c.state_name == "transport"][0]
        self.assertEqual(transport.strength_mpa, 35.0)
        self.assertEqual(transport.psi_dyn, 2.0)

        # Expected F_transport = (72.6 * 2.0) / 2 = 72.6 kN
        self.assertAlmostEqual(transport.f_per_anchor_kN, 72.6, places=1)

if __name__ == "__main__":
    unittest.main()
