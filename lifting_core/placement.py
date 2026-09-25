"""
Placement Engine (§3.4, §3.5)
Executes ordered, deterministic anchor placement procedure:
1. Computes 0.207L trial positions.
2. Shifts anchors to align midpoint with net CoG (plumb line condition).
3. Checks and enforces edge distance, axis spacing, and min wall thickness.
4. Determines rig requirements (spreader beam vs direct slings).
5. Computes utilization and pass/fail status per handling state.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
from .catalogue import get_anchor_spec, AnchorSpec
from .geometry import ElementGeometry
from .load_cases import LoadCaseEngine, HandlingStateCheck

@dataclass
class AnchorPosition:
    id: str
    type_name: str
    clutch: str
    x_mm: float
    y_mm: float
    edge_distance_left_mm: float
    edge_distance_right_mm: float

@dataclass
class StateCheckResult:
    state_name: str
    strength_mpa: float
    f_demand_kN: float
    n_zul_capacity_kN: float
    utilization: float
    is_pass: bool
    notes: str

@dataclass
class RigDecision:
    spreader_required: bool
    sling_angle_deg: float
    reason: str

@dataclass
class PlacementEvaluation:
    anchor_spec: AnchorSpec
    anchors: List[AnchorPosition]
    rig: RigDecision
    state_checks: List[StateCheckResult]
    max_utilization: float
    governing_state: str
    is_geometrically_valid: bool
    geometric_warnings: List[str]

class PlacementEngine:
    def __init__(self, geometry: ElementGeometry, anchor_type: str = "ARL-42"):
        self.geometry = geometry
        self.anchor_spec = get_anchor_spec(anchor_type)

    def evaluate_rig_requirement(self, proposed_beta_deg: float = 15.0) -> RigDecision:
        """
        Determines if a spreader beam is required.
        If panel thickness < min_wall_transverse_mm, direct angled slings are prohibited,
        forcing a spreader beam (beta = 0°).
        """
        t_panel = self.geometry.thickness_mm
        t_transverse_min = self.anchor_spec.min_wall_transverse_mm
        t_axial_min = self.anchor_spec.min_wall_axial_mm

        if t_panel < t_axial_min:
            return RigDecision(
                spreader_required=True,
                sling_angle_deg=0.0,
                reason=f"Panel thickness {t_panel:.0f}mm is thinner than anchor axial min wall {t_axial_min:.0f}mm."
            )

        if t_panel < t_transverse_min:
            return RigDecision(
                spreader_required=True,
                sling_angle_deg=0.0,
                reason=f"Panel thickness {t_panel:.0f}mm < {self.anchor_spec.name} transverse min wall {t_transverse_min:.0f}mm (Figure 2 constraint: spreader mandatory)."
            )

        return RigDecision(
            spreader_required=False,
            sling_angle_deg=proposed_beta_deg,
            reason=f"Direct slings allowable at beta={proposed_beta_deg:.0f} deg (panel {t_panel:.0f}mm >= {t_transverse_min:.0f}mm)."
        )

    def calculate_anchor_positions(self) -> Tuple[List[AnchorPosition], List[str]]:
        """
        Places n=2 anchors using 0.207L trial position, shifted to align with net X_CoG.
        Checks edge distances, axis spacing, and clash with openings.
        """
        L = self.geometry.length_mm
        x_cog, _, _ = self.geometry.compute_cog()
        warnings = []

        # Step 5: Trial position a = 0.207 * L
        a_trial = 0.207 * L
        s_target = L - (2.0 * a_trial)  # Target spacing between anchors

        # Step 6: Shift about real CoG for plumb lift
        x1 = x_cog - (s_target / 2.0)
        x2 = x_cog + (s_target / 2.0)

        # Step 7: Enforce edge distance
        min_edge = self.anchor_spec.min_edge_mm
        min_axis = self.anchor_spec.min_axis_mm

        if x1 < min_edge or (L - x2) < min_edge:
            warnings.append(f"Initial positions ({x1:.0f}, {x2:.0f}) violates min edge distance {min_edge:.0f}mm. Adjusting spacing.")
            # Clamp to min edge while keeping midpoint at x_cog
            max_s_left = 2.0 * (x_cog - min_edge)
            max_s_right = 2.0 * (L - min_edge - x_cog)
            s_adj = min(s_target, max_s_left, max_s_right)

            x1 = x_cog - (s_adj / 2.0)
            x2 = x_cog + (s_adj / 2.0)

        # Axis spacing check
        spacing = x2 - x1
        if spacing < min_axis:
            warnings.append(f"Anchor spacing {spacing:.0f}mm is less than catalogue min axis spacing {min_axis:.0f}mm.")

        # Clash check
        clash1, r1 = self.geometry.check_anchor_clash(x1, 0.0)
        if clash1:
            warnings.append(f"Anchor 1 clash: {r1}")

        clash2, r2 = self.geometry.check_anchor_clash(x2, 0.0)
        if clash2:
            warnings.append(f"Anchor 2 clash: {r2}")

        a1 = AnchorPosition(
            id="A1",
            type_name=self.anchor_spec.name,
            clutch=self.anchor_spec.clutch,
            x_mm=round(x1, 1),
            y_mm=0.0,
            edge_distance_left_mm=round(x1, 1),
            edge_distance_right_mm=round(L - x1, 1)
        )

        a2 = AnchorPosition(
            id="A2",
            type_name=self.anchor_spec.name,
            clutch=self.anchor_spec.clutch,
            x_mm=round(x2, 1),
            y_mm=0.0,
            edge_distance_left_mm=round(x2, 1),
            edge_distance_right_mm=round(L - x2, 1)
        )

        return [a1, a2], warnings

    def run_full_evaluation(self, turn_method: str = "UNCONFIRMED") -> PlacementEvaluation:
        """Runs the complete engineering placement & utilization check workflow."""
        anchors, warnings = self.calculate_anchor_positions()
        rig = self.evaluate_rig_requirement(proposed_beta_deg=15.0)

        # Compute load cases
        load_engine = LoadCaseEngine(
            self_weight_G_kN=self.geometry.self_weight_G_kN,
            face_area_m2=self.geometry.face_area_m2,
            n_anchors=2
        )

        state_checks_data = load_engine.compute_all_states(
            beta_deg=rig.sling_angle_deg,
            turn_method=turn_method
        )

        state_results = []
        max_util = 0.0
        gov_state = ""

        for check in state_checks_data:
            if check.state_name == "storage":
                state_results.append(
                    StateCheckResult(
                        state_name="storage",
                        strength_mpa=15.0,
                        f_demand_kN=0.0,
                        n_zul_capacity_kN=self.anchor_spec.get_axial_capacity(15.0),
                        utilization=0.0,
                        is_pass=True,
                        notes="Unloaded A-frame storage"
                    )
                )
                continue

            capacity_kN = self.anchor_spec.get_axial_capacity(check.strength_mpa)
            util = check.f_per_anchor_kN / capacity_kN if capacity_kN > 0 else 999.0
            is_pass = util <= 1.0

            if util > max_util:
                max_util = util
                gov_state = check.state_name

            state_results.append(
                StateCheckResult(
                    state_name=check.state_name,
                    strength_mpa=check.strength_mpa,
                    f_demand_kN=round(check.f_per_anchor_kN, 2),
                    n_zul_capacity_kN=capacity_kN,
                    utilization=round(util, 3),
                    is_pass=is_pass,
                    notes=check.notes
                )
            )

        return PlacementEvaluation(
            anchor_spec=self.anchor_spec,
            anchors=anchors,
            rig=rig,
            state_checks=state_results,
            max_utilization=round(max_util, 3),
            governing_state=gov_state,
            is_geometrically_valid=len(warnings) == 0,
            geometric_warnings=warnings
        )
