"""
Unit tests for Ingestion & Data Conflict Detection module (§2, Appendix A).
"""

import unittest
from lifting_core.ingestion import InputNormalizer

class TestIngestion(unittest.TestCase):

    def test_conflict_detection_between_approval_and_ifc(self):
        sample_data = {
            "element_id": "WC001",
            "sources": {
                "approval_design": {
                    "length_mm": 4700,
                    "height_mm": 3000,
                    "thickness_mm": 180,
                    "openings_mm": [
                        { "id": "door", "x": 1150, "width": 1100, "sill": 0, "height": 2100 }
                    ]
                },
                "ifc_export": {
                    "length_mm": 4300,
                    "height_mm": 3000,
                    "thickness_mm": 180,
                    "openings_mm": []
                }
            },
            "production": {
                "turn_method": "UNCONFIRMED"
            }
        }

        normalized = InputNormalizer.from_json_dict(sample_data)

        self.assertTrue(normalized.has_conflict)
        self.assertTrue(len(normalized.rfis) >= 2)
        # Check specific RFIs
        rfi_text = " ".join(normalized.rfis)
        self.assertIn("Geometry conflict", rfi_text)
        self.assertIn("UNCONFIRMED", rfi_text)

if __name__ == "__main__":
    unittest.main()
