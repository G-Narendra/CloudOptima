"""
CloudOptima — Multi-Agent Cloud Architecture Optimizer

A production-grade Streamlit dashboard with live agent streaming,
professional dark theme, and polished results display.

Run: streamlit run dashboard.py
"""

from __future__ import annotations
import asyncio
import json

import streamlit as st

st.set_page_config(
    page_title="CloudOptima",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Sentry error tracking (safe to call even without DSN)
from src.core.sentry import init_sentry, add_breadcrumb
init_sentry()

from src.core.orchestrator import Orchestrator
from src.core.models import AgentType, SessionStatus
from src.core.azure_pricing import REGION_PRICING
from src.config import settings
from src.core.compliance_rules import get_frameworks_for_region
from src.core.sanitize import sanitize_text, detect_suspicious_input
from src.core.health import HealthRegistry, HealthStatus
from src.core.llm_cache import get_cache

# ─── Register Health Checks ──────────────────────────────────────────────

registry = HealthRegistry.get_instance()


def _orchestrator_health() -> HealthStatus:
    return HealthStatus(
        name="orchestrator", status="ok",
        details="Orchestrator module loaded",
    )


def _cache_health() -> HealthStatus:
    stats = get_cache().get_stats()
    status = "ok" if stats["size"] < stats["max_size"] * 0.9 else "degraded"
    return HealthStatus(
        name="cache",
        status=status,
        details=f"{stats['size']}/{stats['max_size']} entries, {stats['hit_rate_percent']}% hit rate",
    )


registry.register("orchestrator", _orchestrator_health)
registry.register("cache", _cache_health)

# ─── Constants ──────────────────────────────────────────────────────────────

REGIONS = {
    "india": ":flag-india: India Central",
    "eu": ":flag-eu: Europe West",
    "us": ":flag-us: US East",
    "uae": ":flag-uae: UAE North",
}

COMPLIANCE_OPTIONS = {
    "HIPAA": "US healthcare — protected health information (PHI)",
    "GDPR": "EU — personal data of European citizens",
    "DPDP": "India — Digital Personal Data Protection Act 2023",
    "PDPL": "UAE — Federal Decree-Law No. 45 of 2021",
}

SCALE_OPTIONS = {
    "small": "Small — dev/test, < 1K users",
    "medium": "Medium — production, 1K–50K users",
    "large": "Large — production, 50K–500K users",
    "enterprise": "Enterprise — > 500K users, HA required",
}

AGENT_CONFIG = {
    "architect": {
        "icon": ":material/apartment:",
        "label": "Architect",
        "color": "#6C5CE7",
        "desc": "Designing compute, storage, network, and data tiers",
    },
    "cost": {
        "icon": ":material/currency_rupee:",
        "label": "Cost Analyst",
        "color": "#F59E0B",
        "desc": "Estimating pricing and optimizing spend",
    },
    "security": {
        "icon": ":material/lock:",
        "label": "Security Engineer",
        "color": "#EF4444",
        "desc": "Scanning for vulnerabilities and risks",
    },
    "compliance": {
        "icon": ":material/gavel:",
        "label": "Compliance Officer",
        "color": "#3B82F6",
        "desc": "Checking regulatory requirements via RAG",
    },
    "judge": {
        "icon": ":material/balance:",
        "label": "Judge",
        "color": "#10B981",
        "desc": "Resolving conflicts between specialists",
    },
}

# ─── Prompt Assembly ────────────────────────────────────────────────────────


def assemble_prompt(
    project_description: str,
    workload_type: str = "",
    region: str = "",
    compliance: list[str] | None = None,
    scale: str = "",
    budget: str = "",
    key_services: str = "",
    additional_context: str = "",
) -> str:
    """Assemble a structured prompt from form fields, safe for LLM consumption.

    All text inputs are sanitized before assembly.
    """
    # Sanitize all text inputs
    pd = sanitize_text(project_description)
    wt = sanitize_text(workload_type)
    bg = sanitize_text(budget)
    ks = sanitize_text(key_services)
    ac = sanitize_text(additional_context)

    parts = [f"I need infrastructure for: {pd}"]
    if wt:
        parts.append(f"\nWorkload type: {wt}")
    if region:
        parts.append(f"\nTarget deployment region: {region}")
    if compliance:
        parts.append(f"\nCompliance requirements: {', '.join(compliance)}")
    if scale:
        parts.append(f"\nExpected scale: {SCALE_OPTIONS.get(scale, scale)}")
    if bg:
        parts.append(f"\nMonthly budget: {bg}")
    if ks:
        parts.append(f"\nPreferred services: {ks}")
    if ac:
        parts.append(f"\nAdditional context: {ac}")
    return "\n".join(parts)


# ─── Sidebar ────────────────────────────────────────────────────────────────


def render_sidebar():
    with st.sidebar:
        st.markdown(
            "<div style='text-align:center; padding: 1rem 0;'>"
            "<h2 style='margin: 0; color: #E8E8F0; font-size: 1.5rem;'>"
            "CloudOptima</h2>"
            "<p style='color: #888; font-size: 0.8rem; margin: 0;'>"
            "Multi-Agent Cloud Architect"
            "</p></div>",
            unsafe_allow_html=True,
        )

        st.markdown("---")

        with st.expander(":material/language: Region pricing", expanded=False):
            for name, pricing in REGION_PRICING.items():
                d4 = pricing.vm_pricing.get("Standard_D4_v5")
                price = f"${d4.price_per_hour:.3f}/hr" if d4 else "N/A"
                st.markdown(f"**{pricing.display_name}**")
                st.caption(f"D4_v5: {price}")

        st.markdown("**:material/tune: Demo controls**")
        if "demo_mode" not in st.session_state:
            st.session_state.demo_mode = settings.demo_mode
        st.session_state.demo_mode = st.checkbox(
            "Use mock data (faster for demos)",
            value=st.session_state.demo_mode,
            help="Enable for quick demos without live API calls",
        )
        settings.demo_mode = st.session_state.demo_mode

        st.markdown("**:material/analytics: Previous Session**")
        if "last_result" in st.session_state:
            r = st.session_state.last_result
            total_s = r['total_time_ms'] / 1000
            st.markdown(
                f"<div style='background: var(--secondary-background-color); "
                f"border-radius: 10px; padding: 0.8rem; margin: 0.5rem 0;'>"
                f"<div style='display: flex; justify-content: space-between; margin-bottom: 0.5rem;'>"
                f"<span style='color: #888; font-size: 0.8rem;'>Total Time</span>"
                f"<span style='font-weight: 600;'>{total_s:.1f}s</span></div>"
                f"<div style='display: flex; justify-content: space-between; margin-bottom: 0.3rem;'>"
                f"<span style='color: #888; font-size: 0.8rem;'>Conflicts</span>"
                f"<span>{len(r['conflicts'])}</span></div>"
                f"<div style='display: flex; justify-content: space-between;'>"
                f"<span style='color: #888; font-size: 0.8rem;'>Artifacts</span>"
                f"<span>{len(r['artifacts'])}</span></div>"
                f"<div style='margin-top: 0.5rem; padding-top: 0.5rem; "
                f"border-top: 1px solid rgba(255,255,255,0.05); font-size: 0.75rem; color: #666;'>"
                f"Region: {r.get('region', 'N/A')}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.caption("No sessions yet. Run an analysis to see results.")

        # Health check indicator (silent, bottom of sidebar)
        st.markdown("---")
        health = registry.check_to_dict()
        h_color = {"healthy": "#10B981", "degraded": "#F59E0B", "unhealthy": "#EF4444"}.get(health["status"], "#888")
        st.markdown(
            f"<div style='display: flex; align-items: center; gap: 0.4rem; "
            f"font-size: 0.7rem; color: #666;'>"
            f"<span style='display: inline-block; width: 8px; height: 8px; "
            f"border-radius: 50%; background: {h_color};'></span>"
            f"System: {health['status']} | v{health['version']} | "
            f"Uptime: {health['uptime_seconds']:.0f}s"
            f"</div>",
            unsafe_allow_html=True,
        )


# ─── Guided Form ────────────────────────────────────────────────────────────


def render_guided_form():
    """Return form fields dict when submitted."""
    with st.container(border=True):
        cols = st.columns([1, 4])
        with cols[0]:
            st.markdown("#### :material/rocket_launch:")
        with cols[1]:
            st.markdown("#### Describe your infrastructure")
            st.caption(
                "Our five AI specialists will analyze your needs and produce "
                "a comprehensive cloud architecture with cost estimates, "
                "security audit, and compliance review."
            )

        with st.form("requirements_form", clear_on_submit=False, border=False):
            st.markdown("**:material/apartment: Project**")
            project_description = st.text_area(
                "What are you building?",
                placeholder="e.g., A HIPAA-compliant patient data pipeline serving 50K patients across India",
                height=90,
                label_visibility="collapsed",
            )
            workload_type = st.text_input(
                "Workload type",
                placeholder="e.g., Real-time data pipeline, e-commerce backend",
                label_visibility="visible",
            )

            st.markdown("**:material/location_on: Deployment & compliance**")
            col_r, col_c = st.columns(2)
            with col_r:
                region = st.selectbox(
                    "Azure region",
                    options=[""] + list(REGIONS.keys()),
                    format_func=lambda x: REGIONS.get(x, "Select region..."),
                )
            with col_c:
                compliance = st.multiselect(
                    "Compliance",
                    options=list(COMPLIANCE_OPTIONS.keys()),
                    format_func=lambda x: COMPLIANCE_OPTIONS[x].split("—")[0].strip(),
                    placeholder="Select frameworks",
                )

            st.markdown("**:material/trending_up: Scale & budget**")
            col_s, col_b = st.columns(2)
            with col_s:
                scale = st.selectbox(
                    "Scale",
                    options=[""] + list(SCALE_OPTIONS.keys()),
                    format_func=lambda x: SCALE_OPTIONS.get(x, "Select scale..."),
                )
            with col_b:
                budget = st.text_input(
                    "Monthly budget",
                    placeholder="e.g., $500–$1,000",
                )

            st.markdown("**:material/build: Services & context**")
            key_services = st.text_input(
                "Preferred Azure services",
                placeholder="e.g., AKS, Azure SQL, Cosmos DB, Functions",
                label_visibility="collapsed",
            )
            additional_context = st.text_area(
                "Anything else?",
                placeholder="e.g., Need multi-region DR, prefer serverless, 3-month migration deadline",
                height=60,
                label_visibility="collapsed",
            )

            submitted = st.form_submit_button(
                ":material/play_arrow: Generate architecture",
                type="primary",
                width="stretch",
            )

    return {
        "project_description": project_description if submitted else "",
        "workload_type": workload_type if submitted else "",
        "region": region if submitted else "",
        "compliance": compliance if submitted else [],
        "scale": scale if submitted else "",
        "budget": budget if submitted else "",
        "key_services": key_services if submitted else "",
        "additional_context": additional_context if submitted else "",
        "submitted": submitted,
    }


# ─── Live Agent Streaming ──────────────────────────────────────────────────

# Global orchestrator instance (reused across reruns)
_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    """Get or create the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


async def run_session_with_progress(prompt: str, region: str) -> dict:
    """Run a session with real-time per-agent progress updates using Orchestrator callbacks.

    Uses Orchestrator.set_callbacks() for live streaming — no separate
    OrchestratorService wrapper needed. This eliminates code duplication
    while enabling real-time dashboard updates.
    """
    status_containers = {}
    agent_status_text = {}

    st.markdown("### :material/smart_toy: Agent analysis in progress")
    st.caption("Each specialist analyzes your requirements then the Judge resolves any conflicts")

    # Progress bar
    progress_bar = st.progress(0, text="Initializing agents...")
    specialist_keys = [k for k in AGENT_CONFIG if k != "judge"]

    for agent_key, config in AGENT_CONFIG.items():
        if agent_key == "judge":
            continue
        cols = st.columns([1, 11])
        with cols[0]:
            status_containers[agent_key] = st.empty()
            status_containers[agent_key].markdown(
                f":material/sync_alt:", help=f"Waiting for {config['label']}"
            )
        with cols[1]:
            with st.container(border=True):
                st.markdown(f"**{config['label']}**")
                st.caption(config["desc"])
                agent_status_text[agent_key] = st.empty()
                agent_status_text[agent_key].markdown(
                    f"<div style='display: flex; align-items: center; gap: 0.5rem;'>"
                    f"<span style='color: #555; font-size: 0.85rem;'>⏳ Queued</span>"
                    f"<span style='color: #444; font-size: 0.75rem;'>— awaiting turn</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # Judge container
    st.markdown("---")
    judge_container = st.container(border=True)
    with judge_container:
        col1, col2 = st.columns([10, 2])
        with col1:
            st.markdown("**:material/balance: Judge's Verdict**")
            st.caption("Resolving conflicts between specialists...")
        with col2:
            pass
        judge_status = st.empty()
        judge_status.markdown(
            "<span style='color: #555; font-size: 0.85rem;'>⏳ Waiting for all agents...</span>",
            unsafe_allow_html=True,
        )

    done_set: set = set()
    orchestrator = get_orchestrator()

    def on_agent_done(agent_key: str, info: dict):
        nonlocal done_set
        config = AGENT_CONFIG[agent_key]
        duration_s = info["duration_ms"] / 1000
        status = info["status"]
        is_ok = status == "completed"
        icon = ":material/check_circle:" if is_ok else ":material/error:"

        status_containers[agent_key].markdown(
            f"<span style='color: {config['color']}; font-size: 1.2rem;'>{icon}</span>",
            unsafe_allow_html=True,
        )
        agent_status_text[agent_key].markdown(
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<span style='color: {config['color']}; font-weight: 500;'>"
            f"{'✅ Done' if is_ok else '❌ Failed'}</span>"
            f"<span style='color: #999; font-size: 0.85rem;'>{duration_s:.1f}s</span></div>",
            unsafe_allow_html=True,
        )

        done_set.add(agent_key)
        progress = len(done_set) / len(specialist_keys)
        progress_bar.progress(
            progress,
            text=f"{config['label']} — {duration_s:.1f}s ({len(done_set)}/{len(specialist_keys)})",
        )

        st.toast(f":material/check_circle: {config['label']} completed in {duration_s:.1f}s")

    def on_judge_done(conflict_count: int):
        judge_status.markdown(
            f"<span style='color: #10B981; font-weight: 500;'>"
            f":material/check_circle: Arbitrated — {conflict_count} conflict{'s' if conflict_count != 1 else ''} resolved"
            f"</span>",
            unsafe_allow_html=True,
        )
        progress_bar.progress(1.0, text="✅ All agents complete")
        st.toast(f":material/balance: Judge resolved {conflict_count} conflict{'s' if conflict_count != 1 else ''}")

    # Register callbacks on the orchestrator
    orchestrator.set_callbacks(
        on_agent_done=on_agent_done,
        on_judge_done=on_judge_done,
    )

    try:
        # Create session and add requirement
        session = orchestrator.create_session()
        orchestrator.add_requirement(session.id, prompt, region)

        # Run agents (callbacks fire automatically)
        turns = await orchestrator.run_all_agents(session.id)

        # Run judge (callback fires automatically)
        arb = await orchestrator.run_judge(session.id)

        # Generate artifacts
        artifacts = orchestrator.generate_artifacts(session.id)
        orchestrator.complete_session(session.id, approved=False)

        # Build and return result dict
        result = orchestrator.build_result_dict(session.id)

        # Add Sentry breadcrumb for session completion
        add_breadcrumb(
            message=f"session.completed: {session.id}",
            category="session",
            level="info",
            data={
                "total_time_ms": result["total_time_ms"],
                "conflicts": len(result["conflicts"]),
                "artifacts": len(result["artifacts"]),
            },
        )

        return result

    finally:
        # Always clean up callbacks so they don't leak across reruns
        orchestrator.clear_callbacks()


# ─── Results Display ────────────────────────────────────────────────────────


def render_results(result: dict):
    """Render polished results with cards, tabs, and visual hierarchy."""
    st.session_state.last_result = result

    # Celebration on first run only
    if "runs" not in st.session_state:
        st.session_state.runs = 0
    if st.session_state.runs == 0:
        st.balloons()
    st.session_state.runs += 1

    total_s = result["total_time_ms"] / 1000

    # Summary banner
    st.markdown(
        f"<div style='background: linear-gradient(135deg, #6C5CE7, #a29bfe); "
        f"border-radius: 12px; padding: 1.5rem 2rem; margin: 1.5rem 0;'>"
        f"<h2 style='color: white; margin: 0;'>:material/check_circle: Analysis complete</h2>"
        f"<p style='color: rgba(255,255,255,0.8); margin: 0.3rem 0 0 0;'>"
        f"Session {result['session_id']} — {total_s:.1f}s — {len(result['conflicts'])} conflicts resolved"
        f"</p></div>",
        unsafe_allow_html=True,
    )

    kpi_cols = st.columns(4, gap="medium")
    kpi_data = [
        ("Total time", f"{total_s:.1f}s"),
        ("Conflicts", str(len(result["conflicts"]))),
        ("Artifacts", str(len(result["artifacts"]))),
        ("Status", "Approved" if result.get("arbitration") else "Pending"),
    ]
    for col, (label, value) in zip(kpi_cols, kpi_data):
        with col:
            st.markdown(
                f"<div style='background: var(--secondary-background-color); "
                f"border-radius: 10px; padding: 0.8rem; text-align: center; "
                f"border: 1px solid rgba(255,255,255,0.05);'>"
                f"<div style='color: #888; font-size: 0.7rem; text-transform: uppercase; "
                f"letter-spacing: 1px;'>{label}</div>"
                f"<div style='font-size: 1.5rem; font-weight: 700; margin-top: 0.2rem;'>{value}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # Agent analysis tabs
    # Timing breakdown for all agents
    timing_data = result.get("agent_timing", {})
    if timing_data:
        st.markdown("### :material/timer: Latency breakdown")
        timing_cols = st.columns(4)
        for col, (atype, atiming) in zip(timing_cols, timing_data.items()):
            ds = atiming.get("duration_ms", 0) / 1000
            cfg = AGENT_CONFIG.get(atype, {})
            with col:
                st.markdown(
                    f"<div style='background: var(--secondary-background-color); "
                    f"border-radius: 8px; padding: 0.6rem; text-align: center;"
                    f"border-top: 3px solid {cfg.get('color', '#888')};'>"
                    f"<div style='font-size: 0.7rem; color: #888;'>{cfg.get('label', atype)}</div>"
                    f"<div style='font-size: 1.1rem; font-weight: 600;'>{ds:.1f}s</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    st.markdown("### :material/smart_toy: Agent analysis")
    agent_tabs = st.tabs([
        ":material/apartment: Architect",
        ":material/currency_rupee: Cost Analyst",
        ":material/lock: Security Engineer",
        ":material/gavel: Compliance Officer",
    ])

    for tab, agent_type in zip(agent_tabs, ["architect", "cost", "security", "compliance"]):
        with tab:
            output = result["agent_outputs"].get(agent_type, {})
            timing = result["agent_timing"].get(agent_type, {})
            duration_s = timing.get("duration_ms", 0) / 1000

            # Summary card
            summary = _get_summary(agent_type, output)
            st.markdown(
                f"<div style='background: var(--secondary-background-color); "
                f"border-radius: 10px; padding: 1rem; margin: 0.5rem 0; "
                f"border-left: 4px solid {AGENT_CONFIG[agent_type]['color']};'>"
                f"<div style='display: flex; justify-content: space-between;'>"
                f"<span style='font-weight: 600;'>{AGENT_CONFIG[agent_type]['label']}</span>"
                f"<span style='color: #888;'>{duration_s:.1f}s</span>"
                f"</div>"
                f"<div style='margin-top: 0.5rem;'>{summary}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

            with st.expander("Show full JSON"):
                st.code(json.dumps(output, indent=2, default=str)[:3000], language="json")

    # Judge's Verdict
    if result["arbitration"]:
        st.markdown("### :material/balance: Judge's Verdict")
        arb = result["arbitration"]
        st.markdown(
            f"<div style='background: linear-gradient(135deg, #065F46, #10B981); "
            f"border-radius: 10px; padding: 1.2rem; margin: 0.5rem 0;"
            f"border-left: 4px solid #10B981;'>"
            f"<div style='color: rgba(255,255,255,0.6); font-size: 0.75rem; text-transform: uppercase; "
            f"letter-spacing: 1px;'>Final recommendation</div>"
            f"<div style='color: white; font-weight: 500; margin-top: 0.4rem; line-height: 1.5;'>"
            f"{arb['final_recommendation'][:500]}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        if arb.get("overruled") or arb.get("resolved_in_favor_of"):
            col1, col2 = st.columns(2)
            with col1:
                st.info(f":material/block: Overruled: {arb['overruled'] or 'None'}")
            with col2:
                st.success(
                    f":material/check: In favor of: {arb['resolved_in_favor_of'] or 'Consensus'}")

    # Conflicts
    if result["conflicts"]:
        st.markdown("### :material/search: Detected conflicts")
        for i, conflict in enumerate(result["conflicts"]):
            # Fix: 'architect_vs_cost' → 'Architect vs Cost'
            parts = conflict["dimension"].split("_")
            display_name = f"{parts[0].title()} vs {parts[2].title()}" if len(parts) >= 3 else conflict["dimension"].title()
            st.markdown(
                f"<div style='background: var(--secondary-background-color); "
                f"border-radius: 8px; padding: 0.8rem; margin: 0.5rem 0; "
                f"border-left: 4px solid #F59E0B;'>"
                f"<div style='display: flex; justify-content: space-between;'>"
                f"<span style='font-weight: 600;'>{display_name}</span>"
                f"<span style='color: #888; font-size: 0.8rem;'>#{i + 1}</span>"
                f"</div>"
                f"<div style='margin-top: 0.3rem; color: #ccc;'>{conflict['summary'][:200]}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # Artifacts
    if result["artifacts"]:
        st.markdown("### :material/inventory: Artifacts")
        artifact_icons = {
            "iac": ":material/inventory:",
            "cost_forecast": ":material/currency_rupee:",
            "compliance_report": ":material/description:",
            "rationale": ":material/psychology:",
        }
        artifact_labels = {
            "iac": "IaC Templates",
            "cost_forecast": "Cost Forecast",
            "compliance_report": "Compliance Report",
            "rationale": "Arbitration Rationale",
        }
        tabs = st.tabs([
            f"{artifact_icons.get(a['type'], ':material/article:')} {artifact_labels.get(a['type'], a['type'].title())}"
            for a in result["artifacts"]
        ])
        for tab, artifact in zip(tabs, result["artifacts"]):
            with tab:
                content = artifact["content"]
                fmt = artifact["format"].lower()
                
                # Show human-readable description + download option
                if artifact["type"] == "cost_forecast":
                    st.markdown("**Cost forecast summary** — Detailed monthly cost breakdown with optimization recommendations.")
                    try:
                        parsed = json.loads(content)
                        st.json(parsed)
                    except (json.JSONDecodeError, TypeError):
                        st.code(content, language="json")
                elif artifact["type"] == "compliance_report":
                    st.markdown("**Compliance assessment report** — Regulatory findings per applicable framework.")
                    st.markdown(content)
                elif artifact["type"] == "rationale":
                    st.markdown(content)
                if artifact["type"] == "iac":
                    st.markdown(f"**Infrastructure-as-Code template** — `{fmt.upper()}` configuration for the approved architecture.")
                    lang = "bicep" if fmt == "bicep" else "hcl"
                    st.code(content[:3000], language=lang)


def _get_summary(agent_type: str, output: dict) -> str:
    """Show agent output in a clean code block.
    
    Shows the raw JSON output directly so users can see the structured data.
    Truncates to show key sections without overwhelming the UI.
    """
    if not output:
        return "<code>No output available</code>"
    
    # Handle error responses
    if "_error" in output or "error" in output:
        err = output.get("_error", output.get("error", "Unknown error"))
        return f"<code style='color: #EF4444;'>Error: {err}</code>"
    
    # Show raw output as formatted JSON (this is what users prefer)
    text = output.get("raw", "")
    if text:
        # Strip code fences for cleaner display
        clean = text.replace('```json', '').replace('```', '').strip()
        # Show first 1500 chars in a code block
        display = clean[:1500]
        if len(clean) > 1500:
            display += "\n... (truncated, see full JSON below)"
        return f"<pre style='font-size: 0.75rem; line-height: 1.4; color: #ccc; max-height: 300px; overflow-y: auto; white-space: pre-wrap;'>{display}</pre>"
    
    # Structured output - show as JSON
    try:
        formatted = json.dumps(output, indent=2, default=str)[:1500]
        return f"<pre style='font-size: 0.75rem; line-height: 1.4; color: #ccc; max-height: 300px; overflow-y: auto; white-space: pre-wrap;'>{formatted}</pre>"
    except Exception:
        return str(output)[:1500]


# ─── Main ───────────────────────────────────────────────────────────────────


def main():
    # Hero header
    st.markdown(
        "<div style='text-align: center; padding: 1.5rem 0 0.5rem 0;'>"
        "<div style='margin: 0.5rem 0;'>"
        "<h1 style='margin: 0; font-size: 2.5rem; "
        "background: linear-gradient(135deg, #6C5CE7, #a29bfe); "
        "-webkit-background-clip: text; -webkit-text-fill-color: transparent; "
        "background-clip: text;'>"
        "CloudOptima</h1></div>"
        "<p style='color: #888; max-width: 600px; margin: 0.3rem auto 0 auto;'>"
        "Describe your infrastructure needs below. Five AI specialists will "
        "analyze, debate, and deliver a complete cloud architecture with "
        "cost estimates, security audits, and compliance reviews.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.divider()
    render_sidebar()

    # Check for suspicious input before rendering form
    # (Form is rendered above, actual validation happens on submit)
    form_data = render_guided_form()

    if form_data.get("submitted"):
        pd = form_data.get("project_description", "")
        region = form_data.get("region", "")

        if not pd:
            st.error(":material/error: Tell us what you're building first.")
            st.stop()
        if not region:
            st.error(":material/error: Select a target Azure region.")
            st.stop()

        # Validate for suspicious input
        if detect_suspicious_input(pd):
            st.warning(
                ":material/warning: Your project description contains patterns "
                "that look like code injection. Input has been sanitized."
            )

        prompt = assemble_prompt(
            project_description=form_data.get("project_description", ""),
            workload_type=form_data.get("workload_type", ""),
            region=form_data.get("region", ""),
            compliance=form_data.get("compliance", []),
            scale=form_data.get("scale", ""),
            budget=form_data.get("budget", ""),
            key_services=form_data.get("key_services", ""),
            additional_context=form_data.get("additional_context", ""),
        )

        with st.container():
            result = asyncio.run(run_session_with_progress(prompt, region))
            render_results(result)


if __name__ == "__main__":
    main()
