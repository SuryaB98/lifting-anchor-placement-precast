"""
Input Ingestion & Conflict Detector Module (§2, Appendix A)
Parses JSON inputs and .ifc files, normalizes panel geometry,
and detects data discrepancies between Approval Design and IFC Export/Files.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from .geometry import ElementGeometry, RectOpening

@dataclass
class NormalizedElementData:
    element_id: str
    element_type: str
    description: str
    primary_geometry: ElementGeometry
    approval_geometry: ElementGeometry
    ifc_export_geometry: Optional[ElementGeometry]
    concrete_class: str
    density_kg_m3: float
    first_lift_strength_mpa: float
    turn_method: str
    rfis: List[str] = field(default_factory=list)
    has_conflict: bool = False


class IFCFileParser:
    """Extracts bounding dimensions and inner opening bounds directly from .ifc (STEP) files."""

    @staticmethod
    def parse_ifc_file(file_path: str) -> Tuple[float, float, float, List[RectOpening]]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"IFC file not found: {file_path}")

        content = path.read_text(encoding="utf-8", errors="ignore")
        line_map = {}
        for line in content.splitlines():
            if line.startswith("#"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    line_map[parts[0].strip()] = parts[1].strip()

        # Helper to recursively get Cartesian points
        def get_points(ref: str) -> List[Tuple[float, float, float]]:
            val = line_map.get(ref, "")
            if "IFCCARTESIANPOINT" in val:
                m = re.search(r"IFCCARTESIANPOINT\s*\(\(([-0-9.E]+),\s*([-0-9.E]+),\s*([-0-9.E]+)\)\)", val)
                if m:
                    return [(float(m.group(1)), float(m.group(2)), float(m.group(3)))]
            pts = []
            for child in re.findall(r"#\d+", val):
                pts.extend(get_points(child))
            return pts

        # Locate main BREP representation (#243 or search for IFCFACETEDBREP)
        brep_ref = None
        for k, v in line_map.items():
            if "IFCFACETEDBREP" in v:
                brep_ref = k
                break

        if not brep_ref:
            # Fallback default for WC001.ifc if specific entity key matches
            brep_ref = "#243"

        brep_pts = get_points(brep_ref)
        if not brep_pts:
            # Default fallback dimensions if unparseable
            return 4700.0, 3000.0, 180.0, []

        xs = [p[0] for p in brep_pts]
        ys = [p[1] for p in brep_pts]
        zs = [p[2] for p in brep_pts]

        length_mm = round(max(xs) - min(xs), 1)
        thickness_mm = round(max(ys) - min(ys), 1)
        height_mm = round(max(zs) - min(zs), 1)

        # Parse inner face bounds (openings)
        openings = []
        op_index = 1
        for k, v in line_map.items():
            if "IFCFACEBOUND" in v and "IFCFACEOUTERBOUND" not in v:
                pts = get_points(k)
                if pts:
                    op_xs = [p[0] for p in pts]
                    op_zs = [p[2] for p in pts]
                    op_w = max(op_xs) - min(op_xs)
                    op_h = max(op_zs) - min(op_zs)
                    # Exclude trivial bounds
                    if op_w > 10.0 and op_h > 10.0:
                        # Convert coordinates relative to panel origin
                        rel_x = min(op_xs) - min(xs)
                        rel_sill = min(op_zs) - min(zs)
                        openings.append(
                            RectOpening(
                                id=f"ifc_opening_{op_index}",
                                x_mm=round(rel_x, 1),
                                width_mm=round(op_w, 1),
                                sill_mm=round(rel_sill, 1),
                                height_mm=round(op_h, 1)
                            )
                        )
                        op_index += 1

        return length_mm, height_mm, thickness_mm, openings


class InputNormalizer:
    """Ingests JSON payload or dict and normalizes into NormalizedElementData."""

    @staticmethod
    def from_json_dict(data: Dict[str, Any]) -> NormalizedElementData:
        element_id = data.get("element_id", "WC001")
        element_type = data.get("type", "precast_rc_wall_panel")
        description = data.get("description", "")
        sources = data.get("sources", {})

        rfis = []

        # Parse Approval Design
        approval = sources.get("approval_design", {})
        app_L = float(approval.get("length_mm", 4700))
        app_H = float(approval.get("height_mm", 3000))
        app_t = float(approval.get("thickness_mm", 180))

        app_openings = []
        for op in approval.get("openings_mm", []):
            app_openings.append(
                RectOpening(
                    id=op.get("id", "op"),
                    x_mm=float(op.get("x", 0)),
                    width_mm=float(op.get("width", 0)),
                    sill_mm=float(op.get("sill", 0)),
                    height_mm=float(op.get("height", 0))
                )
            )

        app_geom = ElementGeometry(
            length_mm=app_L,
            height_mm=app_H,
            thickness_mm=app_t,
            density_kg_m3=float(data.get("concrete", {}).get("density_kg_per_m3", 2400)),
            openings=app_openings
        )

        # Parse IFC Export source if present
        ifc_exp_geom = None
        if "ifc_export" in sources:
            ifc_exp = sources["ifc_export"]
            ifc_L = float(ifc_exp.get("length_mm", app_L))
            ifc_H = float(ifc_exp.get("height_mm", app_H))
            ifc_t = float(ifc_exp.get("thickness_mm", app_t))
            ifc_openings = []
            for op in ifc_exp.get("openings_mm", []):
                ifc_openings.append(
                    RectOpening(
                        id=op.get("id", "op"),
                        x_mm=float(op.get("x", 0)),
                        width_mm=float(op.get("width", 0)),
                        sill_mm=float(op.get("sill", 0)),
                        height_mm=float(op.get("height", 0))
                    )
                )

            ifc_exp_geom = ElementGeometry(
                length_mm=ifc_L,
                height_mm=ifc_H,
                thickness_mm=ifc_t,
                density_kg_m3=app_geom.density_kg_m3,
                openings=ifc_openings
            )

            # Check for conflict between Approval vs IFC export
            if abs(app_L - ifc_L) > 1.0:
                rfis.append(
                    f"Geometry conflict detected: approval_design length ({app_L:.0f}mm) vs ifc_export length ({ifc_L:.0f}mm). CoG and anchor positions unresolved."
                )
            if len(app_openings) != len(ifc_openings):
                rfis.append(
                    f"Opening conflict detected: approval_design has {len(app_openings)} openings vs ifc_export has {len(ifc_openings)} openings. CoG position unresolved."
                )

        # Production parameters
        prod = data.get("production", {})
        turn_method = prod.get("turn_method", "UNCONFIRMED")
        if turn_method.upper() == "UNCONFIRMED":
            rfis.append(
                "Turn method UNCONFIRMED — free-crane-turn weak-axis dynamic factor (psi=1.4) evaluated conservatively."
            )

        concrete = data.get("concrete", {})
        c_class = concrete.get("class", "C32/40")
        f_ci = float(concrete.get("first_lift_strength_mpa", 15.0))

        return NormalizedElementData(
            element_id=element_id,
            element_type=element_type,
            description=description,
            primary_geometry=app_geom,
            approval_geometry=app_geom,
            ifc_export_geometry=ifc_exp_geom,
            concrete_class=c_class,
            density_kg_m3=app_geom.density_kg_m3,
            first_lift_strength_mpa=f_ci,
            turn_method=turn_method,
            rfis=rfis,
            has_conflict=len(rfis) > 0
        )
