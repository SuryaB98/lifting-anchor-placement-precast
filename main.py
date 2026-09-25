"""
Main CLI Runner (§8 Deliverables Item 1)
Executes the Lifting-Anchor Placement Agent pipeline on WC001 or any input element.
Produces structured JSON output (§7 schema) and interactive 2D elevation dashboard.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any

from agent.orchestrator import LiftingAnchorAgent
from visualization.renderer import ElevationRenderer
from lifting_core.ingestion import IFCFileParser, RectOpening, ElementGeometry

DEFAULT_WC001_DATA: Dict[str, Any] = {
    "element_id": "WC001",
    "type": "precast_rc_wall_panel",
    "description": "Internal load-bearing stability wall (HybriDfMA family).",
    "note_on_sources": "Geometry reaches you from two systems that DO NOT agree. Decide how your agent should behave.",
    "sources": {
        "approval_design": {
            "length_mm": 4700,
            "height_mm": 3000,
            "thickness_mm": 180,
            "openings_mm": [
                { "id": "door", "x": 1150, "width": 1100, "sill": 0, "height": 2100 },
                { "id": "window", "x": 3050, "width": 1200, "sill": 950, "height": 1000 }
            ]
        },
        "ifc_export": {
            "length_mm": 4300,
            "height_mm": 3000,
            "thickness_mm": 180,
            "openings_mm": []
        }
    },
    "concrete": {
        "class": "C32/40",
        "density_kg_per_m3": 2400,
        "first_lift_strength_mpa": 15
    },
    "reinforcement": {
        "main_curtain": "H16@200",
        "horizontal": "H8@200",
        "edge_u_bars": "H8@200",
        "opening_trimmers": "H12",
        "cover_mm": 30,
        "faces": 2
    },
    "production": {
        "cast_orientation": "flat",
        "mould": "tilting_table_or_battery",
        "turn_method": "UNCONFIRMED",
        "storage": "A-frame stillage, anchor-up"
    },
    "handling_states_required": ["demould", "turn", "storage", "transport", "erection"]
}


def main():
    parser = argparse.ArgumentParser(description="BuildTwin AI Lifting-Anchor Placement Agent (WC001)")
    parser.add_argument("--input", type=str, default="", help="Path to input JSON or .ifc file (default: embedded WC001 data)")
    parser.add_argument("--anchor", type=str, default="ARL-42", help="Candidate anchor type (default: ARL-42)")
    parser.add_argument("--llm", action="store_true", help="Force LLM mode (uses OPENAI_API_KEY or --api-key)")
    parser.add_argument("--no-llm", action="store_true", help="Force offline deterministic mode (ignores environment API keys)")
    parser.add_argument("--api-key", type=str, default="", help="Optional OpenAI/LLM API key for live function calling")
    parser.add_argument("--use-langgraph", action="store_true", help="Execute agent workflow using LangGraph StateGraph")
    parser.add_argument("--output-json", type=str, default="wc001_output.json", help="Path to save structured JSON output")
    parser.add_argument("--output-html", type=str, default="wc001_elevation.html", help="Path to save 2D HTML elevation view")

    args = parser.parse_args()

    input_data = DEFAULT_WC001_DATA

    if args.input:
        input_path = Path(args.input)
        if input_path.suffix.lower() == ".ifc":
            print(f"[IFC] Loading geometry directly from IFC file: {input_path}")
            length, height, thickness, openings = IFCFileParser.parse_ifc_file(str(input_path))
            input_data["sources"]["ifc_export"] = {
                "length_mm": length,
                "height_mm": height,
                "thickness_mm": thickness,
                "openings_mm": [
                    {
                        "id": op.id,
                        "x": op.x_mm,
                        "width": op.width_mm,
                        "sill": op.sill_mm,
                        "height": op.height_mm
                    }
                    for op in openings
                ]
            }
        elif input_path.suffix.lower() == ".json":
            print(f"[JSON] Loading input payload from JSON file: {input_path}")
            input_data = json.loads(input_path.read_text(encoding="utf-8"))

    # Determine API key handling for LLM mode vs offline mode
    import os
    if args.no_llm:
        effective_api_key = None
    elif args.llm:
        effective_api_key = args.api_key or os.getenv("OPENAI_API_KEY")
        if not effective_api_key:
            print("[WARNING] --llm specified but no API key found. Set OPENAI_API_KEY environment variable or pass --api-key.")
    else:
        effective_api_key = args.api_key or os.getenv("OPENAI_API_KEY")

    if args.use_langgraph:
        print(f"[LANGGRAPH AGENT] Initializing LangGraph StateGraph Orchestrator...")
        from agent.langgraph_agent import LangGraphLiftingAgent
        agent = LangGraphLiftingAgent(candidate_anchor=args.anchor)
        output = agent.process_element(input_data)
    else:
        print(f"[AGENT] Initializing Lifting-Anchor AI Agent (Candidate Anchor: {args.anchor})...")
        from agent.llm_client import LLMAgentAdapter
        llm_adapter = LLMAgentAdapter(api_key=effective_api_key)
        output = llm_adapter.run(input_data)

    # Save outputs
    json_path = Path(args.output_json)
    json_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"[OUTPUT] Structured JSON written to: {json_path.resolve()}")

    html_path = Path(args.output_html)
    ElevationRenderer.render_html_dashboard(output, str(html_path))
    print(f"[VISUALIZATION] Interactive 2D elevation dashboard written to: {html_path.resolve()}")

    print("\n" + "="*70)
    print(f"ELEMENT ID: {output['element_id']}")
    print(f"FINAL STATUS: {output['status']}")
    print(f"NET CoG: X={output['cog_mm']['x']} mm, Y={output['cog_mm']['y']} mm (Mass: {output['cog_mm']['mass_tonnes']} t, G: {output['cog_mm']['self_weight_G_kN']} kN)")
    print(f"SPREADER RIG MANDATORY: {output['rig']['spreader']} ({output['rig']['reason']})")
    print(f"PLACED ANCHORS: A1 at X={output['anchors'][0]['x_mm']} mm, A2 at X={output['anchors'][1]['x_mm']} mm")
    print("HANDLING LOAD CHECKS:")
    for chk in output["checks"]:
        pass_str = "PASS" if chk["pass"] else "FAIL"
        print(f"  - {chk['state']:<12} @{chk['strength_mpa']} MPa: Demand={chk['F_kN']:>5.1f} kN | Capacity={chk['N_zul_kN']:>5.1f} kN | Util={chk['util']:>4.2f} | [{pass_str}]")
    print(f"ACTIVE RFIs ({len(output['rfis'])}):")
    for rfi in output["rfis"]:
        print(f"  [RFI] {rfi}")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
