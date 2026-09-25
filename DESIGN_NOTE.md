# Technical Design Note: Precast Lifting-Anchor Placement Agent

**Project:** BuildTwin AI Cockpit — Technical Assessment v1.0  
**Target Element:** WC001 Precast Solid RC Wall Panel  
**Author:** Software / AI Engineering Candidate  
**Date:** September 2026  

---

## 1. Executive Summary & Core Architectural Philosophy

Lifting design for precast concrete wall panels is a safety-critical engineering domain: an improperly positioned anchor or undersized capacity can result in structural failure, panel drop, or catastrophic site accidents. 

This proof-of-concept (POC) implements an **AI Agent system that enforces a strict Determinism Boundary**:
1. **100% Deterministic Safety Core**: Every arithmetic calculation (volume, mass, Center of Gravity with openings, dynamic load cases, formwork adhesion, capacity lookup at matched concrete strengths, edge distances, and panel thickness limits) is executed by unit-tested, pure Python code (`lifting_core/`).
2. **LLM Agent Orchestrator**: The AI Agent acts as an orchestrator (`agent/`), ingesting messy/conflicting inputs, executing typed deterministic tools, generating step-by-step auditable rule traces with engineering clause citations (§3.1–§3.6), and surfacing Request For Information (RFI) alerts.
3. **Fail-Closed Policy**: The system never guesses missing parameters or hallucinates safety numbers. If input sources conflict (e.g., Approval Design vs. IFC Export geometry) or parameters are unconfirmed (`turn_method: UNCONFIRMED`), the system sets status to `HOLD` or `ACCEPT_PROVISIONAL_WITH_HOLD` and refuses auto-release.

---

## 2. System Architecture & Determinism Boundary

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                         INPUT INGESTION & PARSER                            │
 │  - JSON Input Reader (Appendix A Schema)                                    │
 │  - Direct .ifc STEP Geometry & BREP Parser (Test Files/WC001.ifc)           │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                   LLM AGENT / ORCHESTRATION ENGINE (AI)                     │
 │  - Orchestrates deterministic tool executions                               │
 │  - Evaluates input conflicts & formulates RFIs                              │
 │  - Builds natural language justifications & rule trace (§3.5 Procedure)      │
 └──────┬───────────────────────────────┬───────────────────────────────┬──────┘
        │                               │                               │
        ▼                               ▼                               ▼
 ┌───────────────┐               ┌───────────────┐               ┌───────────────┐
 │  TOOL: CoG    │               │ TOOL: Forces  │               │ TOOL: Capacity│
 │  & Geometry   │               │ & Handling    │               │ & Placement   │
 └──────┬────────┘               └──────┬────────┘               └──────┬────────┘
        │                               │                               │
        └───────────────────────────────┼───────────────────────────────┘
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                   DETERMINISTIC ENGINEERING CORE (100% CODE)                │
 │  - CoG with arbitrary openings: X_cog, Y_cog, mass, self-weight G           │
 │  - Handling load cases: demould (with adhesion), turn, transport, erection  │
 │  - Anchor placement: a=0.207*L balance point, shifted for CoG plumb line    │
 │  - Edge distance, axis spacing, min wall thickness (axial vs transverse)     │
 │  - Spreader beam requirement: (t=180mm < min_wall_transverse=240mm)          │
 │  - Capacity check: F <= N_zul at matched concrete strength (15MPa vs 35MPa) │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                           OUTPUT & VISUALIZATION                            │
 │  1. Structured Output JSON (§7 schema) -> wc001_output.json                 │
 │  2. Interactive 2D Elevation Dashboard -> wc001_elevation.html              │
 └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Engineering Analysis & Governing Decisions for Element WC001

### 3.1 Center of Gravity & Plumb Lift Alignment
For element WC001 ($L=4700\text{ mm}, H=3000\text{ mm}, t=180\text{ mm}$):
- With 2 openings (Door: $1100\times2100\text{ mm}$, Window: $1200\times1000\text{ mm}$), net volume is $1.906\text{ m}^3$, net mass is $4.57\text{ tonnes}$, and self-weight $G = 44.86\text{ kN}$.
- Asymmetric openings shift the net Center of Gravity leftward to $X_{\text{CoG}} = 2344.5\text{ mm}, Y_{\text{CoG}} = 1603.8\text{ mm}$.
- To guarantee plumb lifting under crane picks ($n=2$ statically determinate anchors), the midpoint of the anchor coordinates $(x_1, x_2)$ must align with $X_{\text{CoG}}$. The agent shifts trial positions ($0.207 \cdot L = 972.9\text{ mm}$) to place anchors at $A_1 (x = 967.4\text{ mm})$ and $A_2 (x = 3721.6\text{ mm})$.

### 3.2 Concrete Strength Matching & Governing Load State
- **Demould State** (@15 MPa early age): Incorporates formwork adhesion $q_{\text{adh}} \cdot A_f = 14.1\text{ kN}$ with dynamic factor $\psi = 1.3$. Per-anchor demand $F_{\text{demould}} = 36.21\text{ kN}$. At 15 MPa, ARL-42 capacity $N_{\text{zul}} = 60.0\text{ kN} \implies \text{Utilisation} = 0.604$.
- **Road Transport State** (@35 MPa full strength): Dynamic factor $\psi = 2.0$. Per-anchor demand $F_{\text{transport}} = 44.86\text{ kN}$. At 35 MPa, ARL-42 capacity $N_{\text{zul}} = 80.0\text{ kN} \implies \text{Utilisation} = 0.561$.
- **Governing Case**: Demoulding governs maximum utilization ($0.604$), demonstrating why matching each handling state to its exact concrete strength column is essential.

### 3.3 Spreader Beam Compulsion (Figure 2 Rule)
- Panel thickness $t = 180\text{ mm}$.
- ARL-42 transverse minimum wall thickness requirement is $240\text{ mm}$.
- Because $180\text{ mm} < 240\text{ mm}$, direct angled slings ($\beta > 0^\circ$) are forbidden. **A spreader beam ($\beta = 0^\circ$) is mandatory** to maintain purely axial loading.

---

## 4. Conflict & Fail-Closed Behavior

When ingesting input data:
1. **Geometry Discrepancy**: The system compares `approval_design` ($4700\text{ mm}$, 2 openings) against `ifc_export` ($4300\text{ mm}$, 0 openings) or `.ifc` files. Discrepancies generate a critical RFI and set status to `HOLD`.
2. **Production Uncertainty**: `turn_method: UNCONFIRMED` generates an RFI and forces conservative free crane turn evaluation ($\psi = 1.4$).
3. **Human Signoff**: `requires_human_signoff` is set to `true` on all outputs (Rule 3.6 - Never auto-release).

---

## 5. LLM Access Architecture & Tool Calling Interface

### How the AI Agent Accesses LLMs
The agent accesses Large Language Models using standard **Function Calling / Tool Use APIs** (OpenAI GPT-4o, Anthropic Claude 3.5 Sonnet, Google Gemini, or local models via Ollama):

1. **Tool Schema Exposure (`agent/tools.py` & `agent/llm_client.py`)**:
   The agent exposes deterministic Python functions to the LLM via typed JSON schemas (`tool_compute_cog`, `tool_calculate_loads`, `tool_evaluate_anchor_placement`).
2. **Orchestration & Reasoning Boundary**:
   The LLM receives the input prompt alongside the tool schemas. The LLM determines the high-level workflow strategy, invokes the appropriate deterministic tools, interprets the tool results, formats the step-by-step rule trace with clause citations (§3.1–§3.6), and writes human-readable RFI explanations.
3. **Offline State-Machine Fallback**:
   To ensure 100% test reproducibility, zero-latency execution, and offline execution without requiring external API keys, `LiftingAnchorAgent` in `agent/orchestrator.py` incorporates an automated state-machine fallback that executes the exact tool orchestration sequence offline.

---

## 6. AI Usage Disclosure & Production Roadmap

### AI Usage Disclosure
AI tools (Claude / Gemini coding agent) were utilized during development for scaffold generation, test writing, and rendering SVG visual components.

### POC Limitations vs. Production Future State
- **Current POC**: Handles single 2D rectangular wall panels with rectangular cutouts; parses STEP/IFC geometry via regex/lightweight BREP traversal.
- **Production Enhancements**:
  1. **4-Point Lift & Balancing Beam**: Support complex 3D structures requiring load-balancing traverse beams ($n > 2$).
  2. **Full IFC Geometric Kernel**: Integrate full `ifcopenshell` mesh triangulation for arbitrary non-rectangular polygonal panels and embeds.
  3. **Revit C# Add-in / Cloud API Integration**: Expose Python agent as a REST microservice for native Revit desktop plugin consumption.
