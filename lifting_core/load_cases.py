"""
Load Cases Engine (§3.1, §3.2)
Calculates per-anchor force for every handling state (Demould, Turn, Transport, Erection)
matching each state to its exact concrete strength column (15 MPa early-age vs 35 MPa full strength).
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import math

@dataclass
class HandlingStateCheck:
    state_name: str
    psi_dyn: float
    strength_mpa: float
    extra_load_kN: float
    f_per_anchor_kN: float
    z_angle_factor: float
    v_transverse_kN: float
    notes: str

class LoadCaseEngine:
    def __init__(self, self_weight_G_kN: float, face_area_m2: float, n_anchors: int = 2):
        self.G_kN = self_weight_G_kN
        self.A_f_m2 = face_area_m2
        self.n = n_anchors

    def compute_all_states(
        self,
        beta_deg: float = 0.0,
        q_adh_kN_m2: float = 1.0,
        xi_adh: float = 1.0,
        turn_method: str = "UNCONFIRMED"
    ) -> List[HandlingStateCheck]:
        """
        Computes the per-anchor load demand for all required handling states.
        beta_deg: sling angle from vertical in degrees (default 0.0 for spreader beam).
        """
        beta_rad = math.radians(beta_deg)
        z = 1.0 / math.cos(beta_rad) if math.cos(beta_rad) > 0 else 1.0
        tan_beta = math.tan(beta_rad)

        results = []

        # 1. Demould / Striking (@15 MPa)
        adhesion_force_kN = q_adh_kN_m2 * self.A_f_m2 * xi_adh
        psi_demould = 1.3
        f_demould = ((self.G_kN * psi_demould) + adhesion_force_kN) * z / self.n
        v_demould = f_demould * tan_beta
        results.append(
            HandlingStateCheck(
                state_name="demould",
                psi_dyn=psi_demould,
                strength_mpa=15.0,
                extra_load_kN=adhesion_force_kN,
                f_per_anchor_kN=f_demould,
                z_angle_factor=z,
                v_transverse_kN=v_demould,
                notes=f"Early age stripping (@15 MPa) with formwork adhesion {adhesion_force_kN:.1f} kN"
            )
        )

        # 2. Turn (@15 MPa)
        if turn_method.upper() == "TILTING_TABLE":
            psi_turn = 1.1
            turn_note = "Tilting table turn (@15 MPa)"
        else:  # FREE_CRANE_TURN or UNCONFIRMED
            psi_turn = 1.4
            turn_note = f"Turn method {turn_method}: free crane turn assumed conservatively (@15 MPa)"

        f_turn = (self.G_kN * psi_turn) * z / self.n
        v_turn = f_turn * tan_beta
        results.append(
            HandlingStateCheck(
                state_name="turn",
                psi_dyn=psi_turn,
                strength_mpa=15.0,
                extra_load_kN=0.0,
                f_per_anchor_kN=f_turn,
                z_angle_factor=z,
                v_transverse_kN=v_turn,
                notes=turn_note
            )
        )

        # 3. Storage (@15 MPa / Unloaded)
        results.append(
            HandlingStateCheck(
                state_name="storage",
                psi_dyn=0.0,
                strength_mpa=15.0,
                extra_load_kN=0.0,
                f_per_anchor_kN=0.0,
                z_angle_factor=1.0,
                v_transverse_kN=0.0,
                notes="A-frame storage (anchors unloaded)"
            )
        )

        # 4. Road Transport (@35 MPa)
        psi_transport = 2.0
        f_transport = (self.G_kN * psi_transport) * z / self.n
        v_transport = f_transport * tan_beta
        results.append(
            HandlingStateCheck(
                state_name="transport",
                psi_dyn=psi_transport,
                strength_mpa=35.0,
                extra_load_kN=0.0,
                f_per_anchor_kN=f_transport,
                z_angle_factor=z,
                v_transverse_kN=v_transport,
                notes="Road transport (@35 MPa full strength, psi=2.0)"
            )
        )

        # 5. Erection (@35 MPa)
        psi_erection = 1.4
        f_erection = (self.G_kN * psi_erection) * z / self.n
        v_erection = f_erection * tan_beta
        results.append(
            HandlingStateCheck(
                state_name="erection",
                psi_dyn=psi_erection,
                strength_mpa=35.0,
                extra_load_kN=0.0,
                f_per_anchor_kN=f_erection,
                z_angle_factor=z,
                v_transverse_kN=v_erection,
                notes="Site erection (@35 MPa full strength, psi=1.4)"
            )
        )

        return results
