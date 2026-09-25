"""
Anchor Catalogue (§3.3)
Defines anchor specifications, admissible capacities (N_zul, V_zul), edge/spacing limits,
min wall thickness requirements, and clutch mappings.
"""

from dataclasses import dataclass
from typing import Dict, Optional

@dataclass(frozen=True)
class AnchorSpec:
    name: str
    n_zul_15: float  # kN @ 15 MPa
    n_zul_25: float  # kN @ 25 MPa
    n_zul_35: float  # kN @ >= 35 MPa
    v_zul_transverse: float  # kN transverse capacity
    min_edge_mm: float
    min_axis_mm: float
    min_wall_axial_mm: float
    min_wall_transverse_mm: float
    clutch: str

    def get_axial_capacity(self, strength_mpa: float) -> float:
        """
        Returns admissible axial capacity N_zul (kN) based on specified concrete strength.
        Matches exact strength column: @15, @25, or @35+ MPa.
        """
        if strength_mpa < 15.0:
            raise ValueError(f"Concrete strength {strength_mpa} MPa is below minimum 15 MPa requirement.")
        elif strength_mpa < 25.0:
            return self.n_zul_15
        elif strength_mpa < 35.0:
            return self.n_zul_25
        else:
            return self.n_zul_35


ANCHOR_CATALOGUE: Dict[str, AnchorSpec] = {
    "ARL-30": AnchorSpec(
        name="ARL-30",
        n_zul_15=35.0,
        n_zul_25=45.0,
        n_zul_35=50.0,
        v_zul_transverse=25.0,
        min_edge_mm=350.0,
        min_axis_mm=700.0,
        min_wall_axial_mm=140.0,
        min_wall_transverse_mm=200.0,
        clutch="RU-30"
    ),
    "ARL-42": AnchorSpec(
        name="ARL-42",
        n_zul_15=60.0,
        n_zul_25=75.0,
        n_zul_35=80.0,
        v_zul_transverse=40.0,
        min_edge_mm=500.0,
        min_axis_mm=1000.0,
        min_wall_axial_mm=160.0,
        min_wall_transverse_mm=240.0,
        clutch="RU-42"
    ),
    "ARL-52": AnchorSpec(
        name="ARL-52",
        n_zul_15=90.0,
        n_zul_25=115.0,
        n_zul_35=125.0,
        v_zul_transverse=60.0,
        min_edge_mm=650.0,
        min_axis_mm=1300.0,
        min_wall_axial_mm=200.0,
        min_wall_transverse_mm=300.0,
        clutch="RU-52"
    ),
    "CFS-WAL-30": AnchorSpec(
        name="CFS-WAL-30",
        n_zul_15=30.0,
        n_zul_25=37.0,
        n_zul_35=39.0,
        v_zul_transverse=20.0,
        min_edge_mm=300.0,
        min_axis_mm=600.0,
        min_wall_axial_mm=150.0,
        min_wall_transverse_mm=220.0,
        clutch="WAL"
    ),
    "HAL-TPA-5.0": AnchorSpec(
        name="HAL-TPA-5.0",
        n_zul_15=40.0,
        n_zul_25=48.0,
        n_zul_35=50.0,
        v_zul_transverse=35.0,
        min_edge_mm=400.0,
        min_axis_mm=800.0,
        min_wall_axial_mm=150.0,
        min_wall_transverse_mm=210.0,
        clutch="TPA"
    )
}

def get_anchor_spec(anchor_type: str) -> AnchorSpec:
    if anchor_type not in ANCHOR_CATALOGUE:
        raise KeyError(f"Unknown anchor type '{anchor_type}'. Available: {list(ANCHOR_CATALOGUE.keys())}")
    return ANCHOR_CATALOGUE[anchor_type]
