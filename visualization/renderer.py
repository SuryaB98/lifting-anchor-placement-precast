"""
Visualization Renderer Module (§4.5 & F6 Requirement)
Generates SVG vector graphics and standalone interactive HTML elevation dashboards for WC001.
Renders panel outline, opening voids, CoG symbol, anchor positions, dimension lines,
spreader beam rig, handling utilization tables, and active RFIs.
"""

from typing import Dict, Any, List
from pathlib import Path

class ElevationRenderer:
    """Renders dynamic 2D SVG vector graphic and interactive HTML dashboard."""

    @staticmethod
    def generate_svg(agent_result: Dict[str, Any], width_px: int = 920, height_px: int = 630) -> str:
        cog = agent_result.get("cog_mm", {})
        x_cog = cog.get("x", 2350.0)
        y_cog = cog.get("y", 1500.0)
        
        # Dynamic geometry parameters
        panel_l = float(cog.get("length_mm", 4700.0))
        panel_h = float(cog.get("height_mm", 3000.0))
        panel_t = float(cog.get("thickness_mm", 180.0))
        
        anchors = agent_result.get("anchors", [])
        a1_x = anchors[0]["x_mm"] if len(anchors) > 0 else (0.207 * panel_l)
        a2_x = anchors[1]["x_mm"] if len(anchors) > 1 else (panel_l - 0.207 * panel_l)
        anchor_type = anchors[0].get("type", "ARL-42") if len(anchors) > 0 else "ARL-42"
        clutch_type = anchors[0].get("clutch", "RU-42") if len(anchors) > 0 else "RU-42"

        # Scale parameters (panel_l mm -> 520px canvas width)
        scale = 520.0 / panel_l if panel_l > 0 else 0.11

        panel_x0 = 120.0
        panel_y0 = 215.0
        panel_w = panel_l * scale
        panel_h_px = panel_h * scale

        # Transform function mm -> px
        def to_px_x(x_mm: float) -> float:
            return panel_x0 + (x_mm * scale)

        def to_px_y(y_mm: float) -> float:
            return panel_y0 + panel_h_px - (y_mm * scale)

        cog_px_x = to_px_x(x_cog)
        cog_px_y = to_px_y(y_cog)

        a1_px_x = to_px_x(a1_x)
        a2_px_x = to_px_x(a2_x)
        anchor_y_px = panel_y0  # Anchors cast into top edge

        spreader_y = 113.0
        hook_x = (a1_px_x + a2_px_x) / 2.0
        hook_y = 40.0

        # Dynamic SVG Openings
        openings_svg = ""
        openings_data = agent_result.get("openings", [
            {"id": "Door", "x": 1150, "width": 1100, "sill": 0, "height": 2100},
            {"id": "Window", "x": 3050, "width": 1200, "sill": 950, "height": 1000}
        ])
        for op in openings_data:
            op_x = float(op.get("x", op.get("x_mm", 0)))
            op_w = float(op.get("width", op.get("width_mm", 0)))
            op_sill = float(op.get("sill", op.get("sill_mm", 0)))
            op_h = float(op.get("height", op.get("height_mm", 0)))
            op_id = op.get("id", "opening")
            
            px_x = to_px_x(op_x)
            px_y = to_px_y(op_sill + op_h)
            px_w = op_w * scale
            px_h = op_h * scale
            
            openings_svg += f"""
    <rect x="{px_x}" y="{px_y}" width="{px_w}" height="{px_h}" fill="#e4e7eb" stroke="#52606d" stroke-width="1.2" stroke-dasharray="4 3"/>
    <text x="{px_x + px_w/2}" y="{px_y + px_h/2}" font-size="10" fill="#52606d" text-anchor="middle">{op_id} ({op_w:.0f}x{op_h:.0f})</text>"""

        # Dynamic RFIs SVG list
        rfis_data = agent_result.get("rfis", [])
        rfis_svg = ""
        y_rfi_start = 445
        for i, rfi_text in enumerate(rfis_data[:3], 1):
            short_rfi = (rfi_text[:35] + "...") if len(rfi_text) > 35 else rfi_text
            rfis_svg += f"""<text x="675" y="{y_rfi_start + (i-1)*18}" font-size="9" fill="#c0392b">{i}. {short_rfi}</text>"""

        rig_info = agent_result.get("rig", {})
        spreader_mandatory = rig_info.get("spreader", True)
        spreader_text = "Spreader Mandatory" if spreader_mandatory else "Direct Slings"
        rig_reason = rig_info.get("reason", f"t={panel_t:.0f}mm constraint")

        svg_content = f"""<svg viewBox="0 0 920 630" xmlns="http://www.w3.org/2000/svg" font-family="system-ui, -apple-system, sans-serif">
    <!-- Background -->
    <rect x="0" y="0" width="920" height="630" fill="#ffffff"/>
    <style>
        .title {{ font-size: 16px; font-weight: bold; fill: #1b4965; }}
        .dim-text {{ font-size: 11px; fill: #52606d; text-anchor: middle; }}
        .anchor-lbl {{ font-size: 11px; fill: #c0392b; font-weight: bold; text-anchor: middle; }}
        .badge-hold {{ fill: #c0392b; font-weight: bold; }}
        .badge-ok {{ fill: #2f6b3f; font-weight: bold; }}
    </style>

    <!-- Crane Hook & Cable -->
    <line x1="{hook_x}" y1="{hook_y}" x2="{hook_x}" y2="70" stroke="#1f2933" stroke-width="2"/>
    <path d="M {hook_x-6} 70 a6 8 0 1 0 12 0" fill="none" stroke="#1f2933" stroke-width="2"/>
    <text x="{hook_x+12}" y="52" font-size="11" fill="#52606d">crane hook</text>

    <!-- Spreader Beam -->
    <rect x="{a1_px_x-14}" y="{spreader_y}" width="{a2_px_x - a1_px_x + 28}" height="14" rx="3" fill="#2c6fbb"/>
    <line x1="{hook_x}" y1="70" x2="{hook_x}" y2="{spreader_y}" stroke="#1f2933" stroke-width="2"/>
    <text x="{hook_x}" y="{spreader_y+8}" font-size="10" fill="#ffffff" text-anchor="middle" dominant-baseline="middle">spreader beam — slings vertical (&beta; = 0&deg;)</text>

    <!-- Vertical Slings from Spreader Beam to Anchors -->
    <line x1="{a1_px_x}" y1="{spreader_y+14}" x2="{a1_px_x}" y2="{anchor_y_px}" stroke="#2c6fbb" stroke-width="2" stroke-dasharray="4 2"/>
    <line x1="{a2_px_x}" y1="{spreader_y+14}" x2="{a2_px_x}" y2="{anchor_y_px}" stroke="#2c6fbb" stroke-width="2" stroke-dasharray="4 2"/>

    <!-- Panel Outline -->
    <rect x="{panel_x0}" y="{panel_y0}" width="{panel_w}" height="{panel_h_px}" fill="#f5f7fa" stroke="#1f2933" stroke-width="2"/>

    <!-- Openings -->
    {openings_svg}

    <!-- Anchors -->
    <!-- Anchor 1 -->
    <circle cx="{a1_px_x}" cy="{anchor_y_px}" r="6" fill="#c0392b"/>
    <line x1="{a1_px_x}" y1="{anchor_y_px}" x2="{a1_px_x}" y2="{anchor_y_px+30}" stroke="#c0392b" stroke-width="2"/>
    <text x="{a1_px_x}" y="{anchor_y_px-12}" class="anchor-lbl">A1 ({anchor_type})</text>

    <!-- Anchor 2 -->
    <circle cx="{a2_px_x}" cy="{anchor_y_px}" r="6" fill="#c0392b"/>
    <line x1="{a2_px_x}" y1="{anchor_y_px}" x2="{a2_px_x}" y2="{anchor_y_px+30}" stroke="#c0392b" stroke-width="2"/>
    <text x="{a2_px_x}" y="{anchor_y_px-12}" class="anchor-lbl">A2 ({anchor_type})</text>

    <!-- CoG Symbol & Plumb Line -->
    <line x1="{cog_px_x}" y1="{anchor_y_px}" x2="{cog_px_x}" y2="{panel_y0 + panel_h_px + 30}" stroke="#1f2933" stroke-width="1" stroke-dasharray="3 3"/>
    <circle cx="{cog_px_x}" cy="{cog_px_y}" r="9" fill="#ffffff" stroke="#1f2933" stroke-width="1.5"/>
    <path d="M {cog_px_x-9} {cog_px_y} A 9 9 0 0 1 {cog_px_x} {cog_px_y-9} L {cog_px_x} {cog_px_y} Z" fill="#1f2933"/>
    <path d="M {cog_px_x+9} {cog_px_y} A 9 9 0 0 1 {cog_px_x} {cog_px_y+9} L {cog_px_x} {cog_px_y} Z" fill="#1f2933"/>
    <text x="{cog_px_x+14}" y="{cog_px_y+4}" font-size="11" fill="#1f2933" font-weight="bold">Net CoG ({x_cog:.0f}, {y_cog:.0f})</text>

    <!-- Dimensions -->
    <!-- Edge Distance A1 -->
    <line x1="{panel_x0}" y1="{panel_y0-25}" x2="{a1_px_x}" y2="{panel_y0-25}" stroke="#9aa5b1" stroke-width="1"/>
    <text x="{(panel_x0 + a1_px_x)/2}" y="{panel_y0-30}" class="dim-text">a1 = {a1_x:.0f} mm</text>

    <!-- Spacing s -->
    <line x1="{a1_px_x}" y1="{panel_y0-25}" x2="{a2_px_x}" y2="{panel_y0-25}" stroke="#c0392b" stroke-width="1.2"/>
    <text x="{(a1_px_x + a2_px_x)/2}" y="{panel_y0-30}" font-size="11" fill="#c0392b" text-anchor="middle" font-weight="bold">s = {a2_x - a1_x:.0f} mm (Plumb Spacing)</text>

    <!-- Edge Distance A2 -->
    <line x1="{a2_px_x}" y1="{panel_y0-25}" x2="{panel_x0 + panel_w}" y2="{panel_y0-25}" stroke="#9aa5b1" stroke-width="1"/>
    <text x="{(a2_px_x + panel_x0 + panel_w)/2}" y="{panel_y0-30}" class="dim-text">a2 = {panel_l - a2_x:.0f} mm</text>

    <!-- Panel Overall Length & Height -->
    <line x1="{panel_x0}" y1="{panel_y0 + panel_h_px + 25}" x2="{panel_x0 + panel_w}" y2="{panel_y0 + panel_h_px + 25}" stroke="#1f2933" stroke-width="1"/>
    <text x="{panel_x0 + panel_w/2}" y="{panel_y0 + panel_h_px + 40}" font-size="12" fill="#1f2933" text-anchor="middle" font-weight="bold">L = {panel_l:.0f} mm | H = {panel_h:.0f} mm | t = {panel_t:.0f} mm (Solid Precast Panel)</text>

    <!-- Status & Data Card -->
    <rect x="660" y="215" width="240" height="330" rx="6" fill="#f8fafc" stroke="#cbd2d9" stroke-width="1"/>
    <text x="675" y="240" font-size="13" fill="#1b4965" font-weight="bold">Element Data: {agent_result.get('element_id', 'WC001')}</text>
    <text x="675" y="265" font-size="11" fill="#52606d">Status:</text>
    <text x="880" y="265" font-size="11" class="{ 'badge-hold' if 'HOLD' in agent_result.get('status','') else 'badge-ok' }" text-anchor="end">{agent_result.get('status')}</text>
    
    <line x1="675" y1="275" x2="885" y2="275" stroke="#e4e7eb"/>
    <text x="675" y="295" font-size="10.5" fill="#52606d">Self-Weight G:</text>
    <text x="885" y="295" font-size="10.5" fill="#1f2933" text-anchor="end">{cog.get('self_weight_G_kN', 0):.1f} kN ({cog.get('mass_tonnes', 0):.2f} t)</text>

    <text x="675" y="320" font-size="10.5" fill="#52606d">Anchor Type:</text>
    <text x="885" y="320" font-size="10.5" fill="#1f2933" text-anchor="end">{anchor_type} ({clutch_type})</text>

    <text x="675" y="345" font-size="10.5" fill="#52606d">Rig Requirement:</text>
    <text x="885" y="345" font-size="10.5" class="{ 'badge-hold' if spreader_mandatory else 'badge-ok' }" text-anchor="end" font-weight="bold">{spreader_text}</text>

    <text x="675" y="370" font-size="10.5" fill="#52606d">Reason:</text>
    <text x="675" y="388" font-size="9.5" fill="#52606d" width="200">{rig_reason[:40]}</text>

    <line x1="675" y1="405" x2="885" y2="405" stroke="#e4e7eb"/>
    <text x="675" y="425" font-size="11" fill="#1b4965" font-weight="bold">Active RFIs ({len(rfis_data)}):</text>
    {rfis_svg}

    <text x="675" y="520" font-size="9.5" fill="#7b8794">BuildTwin AI Cockpit v1.0</text>
</svg>"""
        return svg_content
        return svg_content

    @staticmethod
    def render_html_dashboard(agent_result: Dict[str, Any], output_filepath: str) -> None:
        svg_code = ElevationRenderer.generate_svg(agent_result)

        checks = agent_result.get("checks", [])
        rfis = agent_result.get("rfis", [])
        rule_trace = agent_result.get("rule_trace", [])

        checks_rows = ""
        for c in checks:
            pass_cls = "pass" if c.get("pass", True) else "fail"
            pass_lbl = "PASS" if c.get("pass", True) else "FAIL"
            checks_rows += f"""<tr>
                <td><strong>{c.get('state')}</strong></td>
                <td>@{c.get('strength_mpa')} MPa</td>
                <td>{c.get('F_kN')} kN</td>
                <td>{c.get('N_zul_kN')} kN</td>
                <td><strong>{c.get('util'):.2f}</strong></td>
                <td><span class="badge {pass_cls}">{pass_lbl}</span></td>
            </tr>"""

        rfis_html = ""
        for rfi in rfis:
            rfis_html += f"<li>⚠️ {rfi}</li>"

        def _format_decision(text: str) -> str:
            import html, re
            t = html.escape(text)
            # Format bold text **word** -> <strong>word</strong>
            t = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', t)
            # Format headers ### text -> <h4>text</h4>
            t = re.sub(r'###\s*(.*?)(?:<br>|\n|$)', r'<h4 style="margin: 10px 0 4px 0; color: #1b4965;">\1</h4>', t)
            # Format linebreaks
            t = t.replace('\n', '<br>')
            return t

        trace_html = ""
        for tr in rule_trace:
            step_num = tr.get('step')
            rule_name = tr.get('rule', '')
            raw_decision = tr.get('decision', '')
            formatted_decision = _format_decision(raw_decision)

            if step_num == 12 or "LIVE LLM SYNTHESIS" in raw_decision or "LLM" in rule_name:
                trace_html += f"""<div class="trace-item" style="border-left: 4px solid #0284c7; background: #f0f9ff; padding: 12px; margin-bottom: 12px; border-radius: 4px;">
                    <span class="rule-tag" style="background: #0284c7; color: white;">{rule_name}</span>
                    <p style="margin-top: 6px; margin-bottom: 6px;"><strong>Step {step_num}:</strong> [Live LLM Audit Reasoning]</p>
                    <div style="font-size: 13px; line-height: 1.6; color: #1e293b;">{formatted_decision}</div>
                </div>"""
            else:
                trace_html += f"""<div class="trace-item">
                    <span class="rule-tag">{rule_name}</span>
                    <p><strong>Step {step_num}:</strong> {formatted_decision}</p>
                </div>"""

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>BuildTwin — Precast Lifting Anchor Verification — Element {agent_result.get('element_id')}</title>
    <style>
        :root {{
            --primary: #1b4965;
            --accent: #2c6fbb;
            --bg-soft: #f8fafc;
            --border: #cbd2d9;
            --red: #c0392b;
            --green: #2f6b3f;
            --amber: #9c6a13;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            margin: 0; padding: 24px;
            background: #f1f5f9; color: #1e293b;
        }}
        .container {{
            max-width: 1050px; margin: 0 auto; background: white;
            padding: 30px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        }}
        .header {{
            border-bottom: 3px solid var(--primary); padding-bottom: 16px; margin-bottom: 24px;
            display: flex; justify-content: space-between; align-items: center;
        }}
        h1 {{ margin: 0; font-size: 24px; color: var(--primary); }}
        .subtitle {{ font-size: 14px; color: #64748b; margin-top: 4px; }}
        .status-badge {{
            padding: 6px 14px; border-radius: 20px; font-weight: bold; font-size: 13px; text-transform: uppercase;
        }}
        .status-badge.hold {{ background: #fef2f2; color: var(--red); border: 1px solid #fca5a5; }}
        .status-badge.ok {{ background: #f0fdf4; color: var(--green); border: 1px solid #86efac; }}

        .card {{ background: var(--bg-soft); border: 1px solid var(--border); border-radius: 6px; padding: 18px; margin-bottom: 24px; }}
        .card h3 {{ margin-top: 0; color: var(--primary); font-size: 16px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }}

        .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
        th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
        th {{ background: #e2e8f0; color: #334155; font-weight: 600; }}
        .badge {{ padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }}
        .badge.pass {{ background: #dcfce7; color: #166534; }}
        .badge.fail {{ background: #fee2e2; color: #991b1b; }}

        .rfi-list {{ list-style: none; padding: 0; margin: 0; }}
        .rfi-list li {{ background: #fffbebf5; border: 1px solid #fde68a; color: var(--amber); padding: 10px 14px; border-radius: 4px; margin-bottom: 8px; font-size: 13px; }}

        .trace-item {{ border-left: 3px solid var(--accent); padding-left: 12px; margin-bottom: 12px; }}
        .trace-item p {{ margin: 4px 0 0 0; font-size: 13px; }}
        .rule-tag {{ font-size: 11px; background: #e0f2fe; color: #0369a1; padding: 2px 6px; border-radius: 3px; font-weight: 600; }}
        .svg-box {{ text-anchor: center; background: white; border: 1px solid var(--border); border-radius: 6px; padding: 10px; text-align: center; margin-bottom: 24px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>Precast Lifting-Anchor Verification — {agent_result.get('element_id')}</h1>
                <div class="subtitle">BuildTwin AI Cockpit · Deterministic Safety Verification & Audit Report</div>
            </div>
            <div class="status-badge { 'hold' if 'HOLD' in agent_result.get('status','') else 'ok' }">
                {agent_result.get('status')}
            </div>
        </div>

        <!-- 2D SVG Visualizer -->
        <div class="svg-box">
            {svg_code}
        </div>

        <!-- Active RFIs Callout -->
        <div class="card" style="border-left: 4px solid var(--amber);">
            <h3>Request For Information (RFIs) & Fail-Closed Alerts</h3>
            <ul class="rfi-list">
                {rfis_html}
            </ul>
        </div>

        <div class="grid2">
            <!-- Handling State Capacity Verification Table -->
            <div class="card">
                <h3>Handling State Load Checks (§3.2)</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Handling State</th>
                            <th>Concrete</th>
                            <th>Demand F</th>
                            <th>Capacity N_zul</th>
                            <th>Utilisation</th>
                            <th>Result</th>
                        </tr>
                    </thead>
                    <tbody>
                        {checks_rows}
                    </tbody>
                </table>
            </div>

            <!-- Rig & Anchor Summary -->
            <div class="card">
                <h3>Rig & Placement Decisions (§3.4, §3.5)</h3>
                <p><strong>Candidate Anchor:</strong> ARL-42 (Admissible load 80 kN @ 35 MPa)</p>
                <p><strong>Matching Clutch:</strong> RU-42</p>
                <p><strong>Rig Requirement:</strong> <span style="color: var(--red); font-weight: bold;">Spreader Beam Mandatory</span></p>
                <p><strong>Reason:</strong> {agent_result.get('rig', {}).get('reason')}</p>
                <p><strong>Sign-off Requirement:</strong> Human Engineer Countersign Required (Rule 3.6)</p>
            </div>
        </div>

        <!-- Deterministic Rule Trace -->
        <div class="card">
            <h3>Auditable Rule Trace (§3.5 Procedure)</h3>
            {trace_html}
        </div>
    </div>
</body>
</html>"""

        Path(output_filepath).write_text(html_content, encoding="utf-8")
