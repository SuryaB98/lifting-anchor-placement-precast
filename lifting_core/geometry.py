"""
Geometry & Center of Gravity (CoG) Engine (§3.5.4)
Computes panel volume, mass, self-weight G, and exact 2D/3D Center of Gravity
accounting for arbitrary rectangular openings (doors, windows, cutouts).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple

@dataclass
class RectOpening:
    id: str
    x_mm: float       # X coordinate of left edge from panel origin
    width_mm: float   # Opening width
    sill_mm: float    # Sill height (Y coordinate of bottom edge)
    height_mm: float  # Opening height

    @property
    def area_m2(self) -> float:
        return (self.width_mm * self.height_mm) / 1e6

    @property
    def center_x_mm(self) -> float:
        return self.x_mm + (self.width_mm / 2.0)

    @property
    def center_y_mm(self) -> float:
        return self.sill_mm + (self.height_mm / 2.0)

    def contains_point(self, x: float, y: float, margin_mm: float = 0.0) -> bool:
        """Checks if a point (x,y) falls inside the opening plus an optional margin."""
        return (
            (self.x_mm - margin_mm) <= x <= (self.x_mm + self.width_mm + margin_mm) and
            (self.sill_mm - margin_mm) <= y <= (self.sill_mm + self.height_mm + margin_mm)
        )


@dataclass
class ElementGeometry:
    length_mm: float
    height_mm: float
    thickness_mm: float
    density_kg_m3: float = 2400.0
    openings: List[RectOpening] = field(default_factory=list)

    @property
    def solid_volume_m3(self) -> float:
        return (self.length_mm * self.height_mm * self.thickness_mm) / 1e9

    @property
    def face_area_m2(self) -> float:
        """Formwork cast face area A_f = L x H."""
        return (self.length_mm * self.height_mm) / 1e6

    @property
    def openings_volume_m3(self) -> float:
        return sum((op.area_m2 * (self.thickness_mm / 1000.0)) for op in self.openings)

    @property
    def net_volume_m3(self) -> float:
        v_net = self.solid_volume_m3 - self.openings_volume_m3
        if v_net <= 0:
            raise ValueError("Invalid geometry: Opening volumes exceed solid panel volume.")
        return v_net

    @property
    def net_mass_kg(self) -> float:
        return self.net_volume_m3 * self.density_kg_m3

    @property
    def net_mass_tonnes(self) -> float:
        return self.net_mass_kg / 1000.0

    @property
    def self_weight_G_kN(self) -> float:
        """Self-weight G in kN (G = mass * g / 1000)."""
        return (self.net_mass_kg * 9.80665) / 1000.0

    def compute_cog(self) -> Tuple[float, float, float]:
        """
        Computes net Center of Gravity (X_cog, Y_cog, Z_cog) in mm.
        Z_cog is centered along the thickness (t / 2).
        """
        v_solid = self.solid_volume_m3
        x_solid = self.length_mm / 2.0
        y_solid = self.height_mm / 2.0
        z_solid = self.thickness_mm / 2.0

        if not self.openings:
            return (x_solid, y_solid, z_solid)

        sum_x_op_vol = 0.0
        sum_y_op_vol = 0.0

        for op in self.openings:
            v_op = (op.area_m2 * self.thickness_mm) / 1000.0
            sum_x_op_vol += op.center_x_mm * v_op
            sum_y_op_vol += op.center_y_mm * v_op

        v_net = self.net_volume_m3
        x_cog = ((x_solid * v_solid) - sum_x_op_vol) / v_net
        y_cog = ((y_solid * v_solid) - sum_y_op_vol) / v_net

        return (x_cog, y_cog, z_solid)

    def check_anchor_clash(self, x_mm: float, y_mm: float, margin_mm: float = 100.0) -> Tuple[bool, str]:
        """
        Checks if an anchor at (x, y) clashes with panel boundaries or opening voids/trimmers.
        Returns (has_clash, reason).
        """
        if x_mm < 0 or x_mm > self.length_mm:
            return True, f"Anchor X={x_mm:.1f}mm is outside panel length [0, {self.length_mm}mm]."
        if y_mm < 0 or y_mm > self.height_mm:
            return True, f"Anchor Y={y_mm:.1f}mm is outside panel height [0, {self.height_mm}mm]."

        for op in self.openings:
            if op.contains_point(x_mm, y_mm, margin_mm=margin_mm):
                return True, f"Anchor at ({x_mm:.1f}, {y_mm:.1f}) clashes with opening '{op.id}' (margin {margin_mm}mm)."

        return False, "OK"
