"""
Agent Tools Module (§6 Determinism Boundary)
Typed, deterministic tool interfaces exposed to the AI Agent.
Every safety calculation (CoG, forces, capacity lookups, edge/wall checks) is executed
by code inside these tools — never by LLM prose generation.
"""

from typing import Dict, Any, List, Tuple
from lifting_core.geometry import ElementGeometry, RectOpening
from lifting_core.catalogue import get_anchor_spec, ANCHOR_CATALOGUE
from lifting_core.load_cases import LoadCaseEngine, HandlingStateCheck
from lifting_core.placement import PlacementEngine, PlacementEvaluation
from lifting_core.ingestion import InputNormalizer, NormalizedElementData

def tool_parse_input(data: Dict[str, Any]) -> NormalizedElementData:
    """Tool: Ingests and normalizes raw JSON data or file inputs, detecting conflicts."""
    return InputNormalizer.from_json_dict(data)

def tool_compute_cog(geometry: ElementGeometry) -> Dict[str, Any]:
    """Tool: Deterministically computes panel net volume, mass, self-weight G, and 2D/3D CoG."""
    x_cog, y_cog, z_cog = geometry.compute_cog()
    return {
        "x_mm": round(x_cog, 1),
        "y_mm": round(y_cog, 1),
        "z_mm": round(z_cog, 1),
        "solid_volume_m3": round(geometry.solid_volume_m3, 3),
        "net_volume_m3": round(geometry.net_volume_m3, 3),
        "net_mass_kg": round(geometry.net_mass_kg, 1),
        "net_mass_tonnes": round(geometry.net_mass_tonnes, 2),
        "self_weight_G_kN": round(geometry.self_weight_G_kN, 2)
    }

def tool_calculate_loads(
    self_weight_G_kN: float,
    face_area_m2: float,
    beta_deg: float = 0.0,
    turn_method: str = "UNCONFIRMED"
) -> List[Dict[str, Any]]:
    """Tool: Deterministically computes per-anchor forces across all handling states."""
    engine = LoadCaseEngine(self_weight_G_kN=self_weight_G_kN, face_area_m2=face_area_m2, n_anchors=2)
    checks = engine.compute_all_states(beta_deg=beta_deg, turn_method=turn_method)
    return [
        {
            "state_name": c.state_name,
            "psi_dyn": c.psi_dyn,
            "strength_mpa": c.strength_mpa,
            "f_per_anchor_kN": round(c.f_per_anchor_kN, 2),
            "v_transverse_kN": round(c.v_transverse_kN, 2),
            "extra_load_kN": round(c.extra_load_kN, 2),
            "notes": c.notes
        }
        for c in checks
    ]

def tool_evaluate_anchor_placement(
    geometry: ElementGeometry,
    anchor_type: str = "ARL-42",
    turn_method: str = "UNCONFIRMED"
) -> PlacementEvaluation:
    """Tool: Executes anchor trial placement, CoG plumb line alignment, capacity verification & rig decision."""
    engine = PlacementEngine(geometry=geometry, anchor_type=anchor_type)
    return engine.run_full_evaluation(turn_method=turn_method)
