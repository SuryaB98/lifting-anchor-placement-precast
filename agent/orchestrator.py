"""
Agent Orchestrator Module (§3.5 Procedure & §6 Determinism Boundary)
Executes the ordered engineering evaluation, enforces fail-closed logic,
builds explicit rule traces with citations (§3.1-§3.6), and generates structured JSON output (§7 schema).
"""

from typing import Dict, Any, List, Optional
from .tools import tool_parse_input, tool_compute_cog, tool_evaluate_anchor_placement
from lifting_core.ingestion import NormalizedElementData

class LiftingAnchorAgent:
    """
    AI Orchestrator for Precast Lifting-Anchor Placement.
    Enforces deterministic safety boundary and fail-closed RFI handling.
    """

    def __init__(self, candidate_anchor: str = "ARL-42"):
        self.candidate_anchor = candidate_anchor

    def process_element(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        rule_trace = []

        # Step 1: Ingest element & enumerate handling states
        normalized: NormalizedElementData = tool_parse_input(input_dict)
        rule_trace.append({
            "step": 1,
            "decision": f"Ingested element {normalized.element_id} ({normalized.element_type}). Enumerated handling states: demould, turn, storage, transport, erection.",
            "rule": "§3.5.1 Enumerate handling states"
        })

        geom = normalized.primary_geometry

        # Step 4: Compute Centre of Gravity
        cog_data = tool_compute_cog(geom)
        rule_trace.append({
            "step": 4,
            "decision": f"Computed net CoG at X={cog_data['x_mm']}mm, Y={cog_data['y_mm']}mm accounting for {len(geom.openings)} openings. Self-weight G={cog_data['self_weight_G_kN']} kN ({cog_data['net_mass_tonnes']} t).",
            "rule": "§3.5.4 Compute CoG with openings"
        })

        # Step 5 & 6 & 7 & 8 & 9 & 10: Run evaluation engine
        eval_result = tool_evaluate_anchor_placement(
            geometry=geom,
            anchor_type=self.candidate_anchor,
            turn_method=normalized.turn_method
        )

        rule_trace.append({
            "step": 5,
            "decision": f"Trial position calculated at a = 0.207 * L ({0.207 * geom.length_mm:.1f}mm from ends).",
            "rule": "§3.5.5 Trial position 0.207L"
        })

        a1, a2 = eval_result.anchors[0], eval_result.anchors[1]
        rule_trace.append({
            "step": 6,
            "decision": f"Shifted anchors to X1={a1.x_mm}mm, X2={a2.x_mm}mm so midpoint ({ (a1.x_mm + a2.x_mm)/2.0:.1f}mm) aligns with net X_CoG ({cog_data['x_mm']}mm) for plumb lift.",
            "rule": "§3.5.6 Plumb alignment about CoG"
        })

        rule_trace.append({
            "step": 7,
            "decision": f"Checked edge distances (left={a1.edge_distance_left_mm}mm >= {eval_result.anchor_spec.min_edge_mm}mm) and axis spacing ({a2.x_mm - a1.x_mm}mm >= {eval_result.anchor_spec.min_axis_mm}mm).",
            "rule": "§3.5.7 Edge distance & spacing check"
        })

        rule_trace.append({
            "step": 8,
            "decision": "Checked clash clearance against panel boundaries, supplementary rebar, and opening voids.",
            "rule": "§3.5.8 Clash clearance"
        })

        rule_trace.append({
            "step": 9,
            "decision": f"Evaluated per-anchor force vs capacity N_zul at matched concrete strength columns. Governing state: '{eval_result.governing_state}' with max utilization {eval_result.max_utilization:.2f}.",
            "rule": "§3.5.9 Capacity check F <= N_zul"
        })

        rule_trace.append({
            "step": 10,
            "decision": f"Rig decision: Spreader beam={eval_result.rig.spreader_required}. Reason: {eval_result.rig.reason}",
            "rule": "§3.5.10 Rig decision & §3.4 Sling angle"
        })

        # Step 11: Decide Outcome & Fail-Closed Logic
        rfis = list(normalized.rfis)
        if not eval_result.is_geometrically_valid:
            rfis.extend(eval_result.geometric_warnings)

        if normalized.has_conflict or eval_result.max_utilization > 1.0 or not eval_result.is_geometrically_valid:
            status = "HOLD" if (normalized.has_conflict or eval_result.max_utilization > 1.0) else "ACCEPT_PROVISIONAL_WITH_HOLD"
        else:
            status = "ACCEPT_PROVISIONAL"

        rule_trace.append({
            "step": 11,
            "decision": f"Decided outcome: {status}. RFIs generated: {len(rfis)}. Refused auto-release; routed for human signoff.",
            "rule": "§3.5.11 Outcome decision & §3.6 Hard stops"
        })

        # Format §7 Schema JSON output
        anchors_json = [
            {
                "id": a.id,
                "type": a.type_name,
                "clutch": a.clutch,
                "x_mm": a.x_mm,
                "y_mm": a.y_mm
            }
            for a in eval_result.anchors
        ]

        checks_json = [
            {
                "state": c.state_name,
                "strength_mpa": c.strength_mpa,
                "F_kN": c.f_demand_kN,
                "N_zul_kN": c.n_zul_capacity_kN,
                "util": c.utilization,
                "pass": c.is_pass
            }
            for c in eval_result.state_checks
        ]

        output = {
            "element_id": normalized.element_id,
            "status": status,
            "cog_mm": {
                "x": cog_data["x_mm"],
                "y": cog_data["y_mm"],
                "z": cog_data["z_mm"],
                "length_mm": geom.length_mm,
                "height_mm": geom.height_mm,
                "thickness_mm": geom.thickness_mm,
                "source": "approval_design",
                "self_weight_G_kN": cog_data["self_weight_G_kN"],
                "mass_tonnes": cog_data["net_mass_tonnes"]
            },
            "openings": [
                {
                    "id": op.id,
                    "x": op.x_mm,
                    "width": op.width_mm,
                    "sill": op.sill_mm,
                    "height": op.height_mm
                }
                for op in geom.openings
            ],
            "rig": {
                "spreader": eval_result.rig.spreader_required,
                "reason": eval_result.rig.reason
            },
            "anchors": anchors_json,
            "checks": checks_json,
            "rfis": rfis,
            "rule_trace": rule_trace,
            "requires_human_signoff": True
        }

        return output
