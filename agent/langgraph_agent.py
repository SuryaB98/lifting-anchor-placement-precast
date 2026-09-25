"""
LangGraph Agentic Orchestrator (§6 & §10 Stretch Goals)
Implements a stateful, cyclic AI Agent workflow using LangGraph (StateGraph),
nodes, edges, and conditional routing for precast lifting anchor placement.
"""

from typing import Dict, Any, List, TypedDict, Annotated, Optional
import json

from langgraph.graph import StateGraph, END
from .tools import tool_parse_input, tool_compute_cog, tool_evaluate_anchor_placement
from lifting_core.ingestion import NormalizedElementData

class AgentState(TypedDict):
    input_data: Dict[str, Any]
    normalized_data: Optional[Dict[str, Any]]
    candidate_anchor: str
    cog_data: Optional[Dict[str, Any]]
    placement_eval: Optional[Dict[str, Any]]
    rfis: List[str]
    status: str
    rule_trace: List[Dict[str, Any]]
    requires_human_signoff: bool


def ingest_node(state: AgentState) -> AgentState:
    """Node 1: Ingests element data, parses IFC/JSON, and detects initial conflicts."""
    normalized: NormalizedElementData = tool_parse_input(state["input_data"])
    
    trace = list(state.get("rule_trace", []))
    trace.append({
        "step": 1,
        "decision": f"[LangGraph Node: ingest_node] Ingested element {normalized.element_id}. Enumerated handling states.",
        "rule": "§3.5.1 Enumerate handling states"
    })
    
    return {
        **state,
        "normalized_data": {
            "element_id": normalized.element_id,
            "element_type": normalized.element_type,
            "primary_geometry": normalized.primary_geometry,
            "turn_method": normalized.turn_method,
            "has_conflict": normalized.has_conflict
        },
        "rfis": list(normalized.rfis),
        "rule_trace": trace
    }


def compute_cog_node(state: AgentState) -> AgentState:
    """Node 2: Deterministically computes Center of Gravity, volume, mass, and self-weight G."""
    norm = state["normalized_data"]
    geom = norm["primary_geometry"]
    
    cog_info = tool_compute_cog(geom)
    
    trace = list(state["rule_trace"])
    trace.append({
        "step": 4,
        "decision": f"[LangGraph Node: compute_cog_node] Net CoG computed at X={cog_info['x_mm']}mm, Y={cog_info['y_mm']}mm. Self-weight G={cog_info['self_weight_G_kN']} kN.",
        "rule": "§3.5.4 Compute CoG with openings"
    })
    
    return {
        **state,
        "cog_data": cog_info,
        "rule_trace": trace
    }


def evaluate_placement_node(state: AgentState) -> AgentState:
    """Node 3: Executes trial placement, plumb alignment, edge/axis checks & rig evaluation."""
    norm = state["normalized_data"]
    geom = norm["primary_geometry"]
    candidate = state.get("candidate_anchor", "ARL-42")
    
    eval_result = tool_evaluate_anchor_placement(
        geometry=geom,
        anchor_type=candidate,
        turn_method=norm["turn_method"]
    )
    
    trace = list(state["rule_trace"])
    trace.append({
        "step": 9,
        "decision": f"[LangGraph Node: evaluate_placement_node] Anchor {candidate} evaluated. Max utilization={eval_result.max_utilization:.2f} (Governing: {eval_result.governing_state}). Spreader mandatory={eval_result.rig.spreader_required}.",
        "rule": "§3.5.9 Capacity check & §3.5.10 Rig decision"
    })
    
    # Transform evaluation object to serializable dict
    anchors_dict = [
        {"id": a.id, "type": a.type_name, "clutch": a.clutch, "x_mm": a.x_mm, "y_mm": a.y_mm}
        for a in eval_result.anchors
    ]
    checks_dict = [
        {"state": c.state_name, "strength_mpa": c.strength_mpa, "F_kN": c.f_demand_kN, "N_zul_kN": c.n_zul_capacity_kN, "util": c.utilization, "pass": c.is_pass}
        for c in eval_result.state_checks
    ]
    
    return {
        **state,
        "placement_eval": {
            "anchors": anchors_dict,
            "checks": checks_dict,
            "rig": {"spreader": eval_result.rig.spreader_required, "reason": eval_result.rig.reason},
            "max_utilization": eval_result.max_utilization,
            "is_geometrically_valid": eval_result.is_geometrically_valid,
            "warnings": eval_result.geometric_warnings
        },
        "rule_trace": trace
    }


def outcome_decision_node(state: AgentState) -> AgentState:
    """Node 4: Evaluates fail-closed conditions, consolidates RFIs, and enforces human sign-off."""
    norm = state["normalized_data"]
    placement = state["placement_eval"]
    rfis = list(state["rfis"])
    
    if not placement["is_geometrically_valid"]:
        rfis.extend(placement["warnings"])
        
    has_conflict = norm["has_conflict"]
    max_util = placement["max_utilization"]
    
    if has_conflict or max_util > 1.0 or not placement["is_geometrically_valid"]:
        status = "HOLD" if (has_conflict or max_util > 1.0) else "ACCEPT_PROVISIONAL_WITH_HOLD"
    else:
        status = "ACCEPT_PROVISIONAL"
        
    trace = list(state["rule_trace"])
    trace.append({
        "step": 11,
        "decision": f"[LangGraph Node: outcome_decision_node] Final Status: {status}. Total Active RFIs: {len(rfis)}. Human sign-off required.",
        "rule": "§3.5.11 Outcome decision & §3.6 Hard stops"
    })
    
    return {
        **state,
        "rfis": rfis,
        "status": status,
        "requires_human_signoff": True,
        "rule_trace": trace
    }


def should_iterate_or_end(state: AgentState) -> str:
    """Conditional Edge: Decides whether to iterate or finish graph execution."""
    placement = state.get("placement_eval")
    if not placement:
        return "evaluate_placement_node"
    
    # If initial anchor (e.g. ARL-30) overloaded (util > 1.0), could iterate to upsize to ARL-42
    return "outcome_decision_node"


def build_langgraph_agent():
    """Builds and compiles the LangGraph StateGraph workflow."""
    workflow = StateGraph(AgentState)
    
    workflow.add_node("ingest_node", ingest_node)
    workflow.add_node("compute_cog_node", compute_cog_node)
    workflow.add_node("evaluate_placement_node", evaluate_placement_node)
    workflow.add_node("outcome_decision_node", outcome_decision_node)
    
    workflow.set_entry_point("ingest_node")
    
    workflow.add_edge("ingest_node", "compute_cog_node")
    workflow.add_edge("compute_cog_node", "evaluate_placement_node")
    workflow.add_conditional_edges(
        "evaluate_placement_node",
        should_iterate_or_end,
        {
            "evaluate_placement_node": "evaluate_placement_node",
            "outcome_decision_node": "outcome_decision_node"
        }
    )
    workflow.add_edge("outcome_decision_node", END)
    
    return workflow.compile()


class LangGraphLiftingAgent:
    """Wrapper class running the compiled LangGraph workflow."""

    def __init__(self, candidate_anchor: str = "ARL-42"):
        self.candidate_anchor = candidate_anchor
        self.graph = build_langgraph_agent()

    def process_element(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        initial_state: AgentState = {
            "input_data": input_dict,
            "normalized_data": None,
            "candidate_anchor": self.candidate_anchor,
            "cog_data": None,
            "placement_eval": None,
            "rfis": [],
            "status": "PENDING",
            "rule_trace": [],
            "requires_human_signoff": True
        }
        
        final_state = self.graph.invoke(initial_state)
        
        cog = final_state["cog_data"]
        placement = final_state["placement_eval"]
        norm = final_state["normalized_data"]
        geom = norm["primary_geometry"]
        
        return {
            "element_id": norm["element_id"],
            "status": final_state["status"],
            "cog_mm": {
                "x": cog["x_mm"],
                "y": cog["y_mm"],
                "z": cog["z_mm"],
                "length_mm": geom.length_mm,
                "height_mm": geom.height_mm,
                "thickness_mm": geom.thickness_mm,
                "source": "approval_design",
                "self_weight_G_kN": cog["self_weight_G_kN"],
                "mass_tonnes": cog["net_mass_tonnes"]
            },
            "openings": [
                {"id": op.id, "x": op.x_mm, "width": op.width_mm, "sill": op.sill_mm, "height": op.height_mm}
                for op in geom.openings
            ],
            "rig": placement["rig"],
            "anchors": placement["anchors"],
            "checks": placement["checks"],
            "rfis": final_state["rfis"],
            "rule_trace": final_state["rule_trace"],
            "requires_human_signoff": final_state["requires_human_signoff"],
            "orchestrator_type": "LangGraph StateGraph"
        }
