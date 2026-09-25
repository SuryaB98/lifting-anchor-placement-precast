# BuildTwin — Precast Lifting-Anchor Placement AI Agent

Proof-of-concept AI agent that ingests precast concrete elements (specifically element `WC001`), applies a deterministic set of structural engineering safety rules, selects and places lifting anchors, determines rig requirements, and generates an auditable check report with an interactive 2D elevation dashboard.

---

## Quick Start (One Command Execution)

Run the full pipeline using embedded WC001 assessment data (offline deterministic mode):

```bash
python main.py
```

Or process an IFC file directly:

```bash
python main.py --input "Test Files/WC001.ifc"
```

---

## Running Modes & CLI Flags

The agent can be executed in offline deterministic mode or with live LLM function calling (OpenAI / Anthropic / Gemini).

### PowerShell / CLI Examples:

* **Force Offline Deterministic Mode** (ignores any set API keys):
  ```powershell
  python main.py --input "Test Files/WC001.ifc" --no-llm
  ```

* **Force Live LLM Synthesis Mode** (uses `$env:OPENAI_API_KEY` or `--api-key`):
  ```powershell
  python main.py --input "Test Files/WC001.ifc" --llm
  ```

* **Explicit API Key Execution:**
  ```powershell
  python main.py --input "Test Files/WC001.ifc" --llm --api-key "sk-proj-xxx"
  ```

* **Execute via LangGraph StateGraph:**
  ```powershell
  python main.py --input "Test Files/WC001.ifc" --use-langgraph
  ```

---

## Output Deliverables

Running `main.py` produces two output files:
1. `wc001_output.json`: Structured JSON result adhering strictly to the Section 7 schema.
2. `wc001_elevation.html`: Standalone interactive 2D SVG/HTML elevation dashboard depicting:
   - Precast panel dimensions ($4700 \times 3000 \times 180 \text{ mm}$).
   - Door ($1100\times2100 \text{ mm}$) and Window ($1200\times1000 \text{ mm}$) opening voids.
   - Calculated net Center of Gravity ($X_{\text{CoG}}, Y_{\text{CoG}}$) marked with standard CoG symbol.
   - Placed anchors ($A_1, A_2$) at $X_1 = 967.4 \text{ mm}$ and $X_2 = 3721.6 \text{ mm}$ (plumb line alignment).
   - Spreader beam rig requirement and active Request For Information (RFI) alerts.
   - **Auditable Rule Trace**: Steps 1–11 (deterministic safety checks) and **Step 12 (Live LLM Audit Reasoning)** when `--llm` is active.

---

## Input Resolution & Discrepancy Behavior

* **Direct IFC Input (`--input "Test Files/WC001.ifc"`)**: Parses 3D geometry directly from the `.ifc` file ($4700 \text{ mm}$ length, 2 openings), matching approval design and resolving geometry conflict RFIs (leaving **1 RFI** for unconfirmed turn method).
* **Default Benchmark Input (`python main.py`)**: Demonstrates multi-source discrepancy detection (§2) where `approval_design` ($4700 \text{ mm}$) conflicts with `ifc_export` ($4300 \text{ mm}$), generating **3 ACTIVE RFIs** and failing closed (`HOLD`).

---

## Project Architecture & Determinism Boundary

```
lifting-anchor-placement-precast/
├── lifting_core/            # 100% Deterministic Safety Core (Python)
│   ├── catalogue.py         # Anchor technical specifications & capacity matrices (§3.3)
│   ├── geometry.py          # CoG & panel volume with arbitrary openings (§3.5.4)
│   ├── load_cases.py        # Forces per state, dynamic factors, adhesion (§3.1, §3.2)
│   ├── placement.py         # Anchor positioning, CoG plumb line, edge/wall checks (§3.4, §3.5)
│   └── ingestion.py         # JSON normalizer & IFC parser with conflict detection (§2, App A)
├── agent/                   # AI Agent Orchestration Layer
│   ├── tools.py             # Typed deterministic tool wrappers (§6 boundary)
│   ├── llm_client.py        # Live LLM API Function Calling Adapter (OpenAI / Anthropic / Gemini)
│   ├── langgraph_agent.py   # LangGraph StateGraph Orchestration Implementation
│   └── orchestrator.py      # AI Agent controller, rule tracer (§3.5), RFI builder
├── visualization/           # 2D Visualizer
│   └── renderer.py          # Dynamic SVG & HTML elevation dashboard generator (§4.5, F6)
├── tests/                   # Comprehensive Unit Test Suite
│   ├── test_catalogue.py
│   ├── test_geometry.py
│   ├── test_load_cases.py
│   ├── test_placement.py
│   └── test_ingestion.py
├── main.py                  # CLI Application Runner
├── DESIGN_NOTE.md           # Engineering & AI Architecture Design Note (<= 2 pages)
└── README.md                # Project documentation
```

---

## Key Safety & Engineering Rules Implemented

1. **Determinism Boundary**: All safety arithmetic (CoG, load cases, capacity lookups, edge/axis spacing, min wall checks) is executed in pure Python code (`lifting_core/`). The LLM Agent orchestrates execution and generates auditable explanations with rule citations (§3.1–§3.6).
2. **CoG Plumb Line Alignment**: Anchor spacing is shifted so the anchor midpoint aligns horizontally with net $X_{\text{CoG}}$, ensuring the element hangs plumb under crane lift.
3. **Concrete Strength Matching**: Each handling state is evaluated at its exact concrete strength column (Demould & Turn @ 15 MPa early age vs Road Transport & Erection @ 35 MPa full strength). Demoulding governs maximum utilization ($0.604$).
4. **Spreader Beam Compulsion**: Because panel thickness ($180\text{ mm}$) is less than the ARL-42 transverse minimum wall thickness ($240\text{ mm}$), direct angled slings ($\beta > 0^\circ$) are forbidden, forcing a **spreader beam ($\beta = 0^\circ$)**.
5. **Fail-Closed Behavior**: Geometry mismatches (Approval $4700\text{ mm}$ vs IFC Export $4300\text{ mm}$) or unconfirmed production parameters (`turn_method: UNCONFIRMED`) automatically trigger a `HOLD` status with active RFIs. Auto-release is disabled (`requires_human_signoff = true`).

---

## Running Unit Tests

Execute the complete test suite:

```bash
pytest tests/
```

Or using standard Python `unittest`:

```bash
python -m unittest discover tests
```

---

## Options & CLI Parameters

```bash
python main.py --help
```

- `--input`: Path to input JSON or `.ifc` file.
- `--anchor`: Candidate anchor type (default: `ARL-42`, available: `ARL-30`, `ARL-42`, `ARL-52`, `CFS-WAL-30`, `HAL-TPA-5.0`).
- `--llm`: Force LLM mode using OpenAI / Anthropic API keys.
- `--no-llm`: Force offline deterministic execution (ignore API keys).
- `--api-key`: Optional LLM API key.
- `--use-langgraph`: Execute workflow using LangGraph StateGraph.
- `--output-json`: Filepath for JSON output (default: `wc001_output.json`).
- `--output-html`: Filepath for HTML elevation report (default: `wc001_elevation.html`).
