"""The AI Architect Panel - CLI Interface.

Run with: python -m src.cli.main run "prompt" --region india
"""

from __future__ import annotations
import asyncio
import json
import logging
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from src.core.orchestrator import Orchestrator

console = Console()
app = typer.Typer(name="ai-architect-panel")
orchestrator = Orchestrator()

logging.basicConfig(level=logging.WARNING)


def print_header():
    console.print()
    console.print(Panel(
        "[bold cyan]The AI Architect Panel[/bold cyan]\n"
        "[dim]Multi-Agent Cloud Infrastructure Design System[/dim]\n"
        "[dim]Powered by NVIDIA NIMs[/dim]",
        box=box.HEAVY,
    ))
    console.print()


@app.command()
def run(
    prompt: str = typer.Argument(..., help="Describe your infrastructure need"),
    region: str = typer.Option("", "--region", "-r", help="Target Azure region"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full agent outputs"),
):
    """Run a full session with The AI Architect Panel."""
    print_header()

    console.print(f"[bold]Input:[/bold] {prompt}")
    if region:
        console.print(f"[bold]Region:[/bold] {region}")
    console.print()

    session = orchestrator.create_session()
    orchestrator.add_requirement(session.id, prompt, region)
    console.print(f"[dim]Session ID: {session.id}[/dim]")
    console.print()

    # Run agents
    async def run_agents():
        turns = await orchestrator.run_all_agents(session.id)
        return turns

    turns = asyncio.run(run_agents())

    # Display agent outputs
    agent_colors = {
        "architect": "green",
        "cost": "yellow",
        "security": "red",
        "compliance": "blue",
    }

    for turn in turns:
        color = agent_colors.get(turn.agent_type.value, "white")
        agent_name = turn.agent_type.value.upper()

        if turn.status == "completed":
            try:
                parsed = json.loads(turn.output_text)
                if verbose:
                    console.print(Panel(
                        json.dumps(parsed, indent=2)[:2000],
                        title=f"[bold {color}]{agent_name} Agent[/bold {color}]",
                        box=box.ROUNDED,
                    ))
                else:
                    summary = _get_agent_summary(turn.agent_type.value, parsed)
                    console.print(Panel(
                        summary,
                        title=f"[bold {color}]{agent_name} Agent[/bold {color}]",
                        box=box.ROUNDED,
                    ))
            except (json.JSONDecodeError, AttributeError):
                console.print(Panel(
                    turn.output_text[:500],
                    title=f"[bold {color}]{agent_name} Agent[/bold {color}]",
                    box=box.ROUNDED,
                ))
        else:
            console.print(f"[bold red]{agent_name} Agent FAILED:[/bold red] {turn.error}")    # Run Judge
    with console.status("[bold magenta]Judge Agent arbitrating conflicts...[/bold magenta]"):
        async def run_judge():
            return await orchestrator.run_judge(session.id)
        arb = asyncio.run(run_judge())

    console.print(Panel(
        arb.final_recommendation[:1000],
        title="[bold magenta]JUDGE - Final Recommendation[/bold magenta]",
        box=box.HEAVY,
    ))
    console.print()

    # Show plain language summary
    plain_key = f"{session.id}_plain"
    if plain_key in orchestrator.arbitrations:
        plain_arb = orchestrator.arbitrations[plain_key]
        console.print(Panel(
            plain_arb.rationale[:1000],
            title="[bold cyan]In Plain Language[/bold cyan]",
            box=box.DOUBLE,
        ))
        console.print()

    # Generate artifacts
    artifacts = orchestrator.generate_artifacts(session.id)

    # Show conflicts
    conflicts = orchestrator.conflicts.get(session.id, [])
    if conflicts:
        conflict_table = Table(title="Detected Conflicts", box=box.ROUNDED)
        conflict_table.add_column("Dimension", style="yellow")
        conflict_table.add_column("Agents", style="cyan")
        conflict_table.add_column("Resolution", style="green")

        try:
            arb_data = json.loads(arb.rationale) if arb.rationale else {}
            summaries = arb_data.get("arbitration", {}).get("conflict_summaries", [])
        except (json.JSONDecodeError, AttributeError):
            summaries = []

        for i, c in enumerate(conflicts):
            resolution = summaries[i].get("resolution", "Arbitrated") if i < len(summaries) else "Arbitrated"
            conflict_table.add_row(
                c.dimension.value.replace("_", " vs ").title().replace(" Vs ", " vs "),
                f"{c.agent_a_type.value.title()} vs {c.agent_b_type.value.title()}",
                resolution,
            )
        console.print(conflict_table)
        console.print()

    # Artifact summary
    artifact_table = Table(title="Generated Artifacts", box=box.SIMPLE)
    artifact_table.add_column("Type", style="cyan")
    artifact_table.add_column("Format", style="green")
    artifact_table.add_column("Status", style="yellow")
    for a in artifacts:
        artifact_table.add_row(a.artifact_type.title(), a.format.upper(), "Generated")
    console.print(artifact_table)
    console.print()

    # Calculate timing from agent turns
    total_time_ms = sum(t.duration_ms or 0 for t in orchestrator.turns.get(session.id, []))
    timing_lines = []
    for t in orchestrator.turns.get(session.id, []):
        if t.duration_ms:
            timing_lines.append(f"  {t.agent_type.value.title():12} {t.duration_ms // 1000}.{t.duration_ms % 1000 // 100:01d}s")
    timing_display = "\n".join(timing_lines) if timing_lines else ""

    console.print(Panel(
        "[bold green]Session Complete![/bold green]\n\n"
        f"Session ID: {session.id}\n"
        f"Conflicts detected: {len(conflicts)}\n"
        f"Artifacts generated: {len(artifacts)}\n"
        f"Total time: {total_time_ms // 1000}.{total_time_ms % 1000 // 100:01d}s\n"
        + (f"\n[dim]Per-agent timing:\n{timing_display}[/dim]\n" if timing_display else "")
        + "\n"
        "[dim]Human approval is required before deploying any generated IaC.[/dim]",
        box=box.HEAVY,
    ))


def _get_agent_summary(agent_type: str, parsed: dict) -> str:
    """Extract a concise summary from parsed agent output."""
    if agent_type == "architect":
        arch = parsed.get("architecture", {})
        return (
            f"Compute: {arch.get('compute', {}).get('recommendation', 'N/A')[:80]}\n"
            f"Storage: {arch.get('storage', {}).get('recommendation', 'N/A')[:80]}\n"
            f"Network: {arch.get('networking', {}).get('recommendation', 'N/A')[:80]}\n"
            f"Data:    {arch.get('data', {}).get('recommendation', 'N/A')[:80]}"
        )
    elif agent_type == "cost":
        analysis = parsed.get("analysis", {})
        cost = analysis.get("estimated_monthly_cost", "N/A")
        opts = analysis.get("cost_optimization_opportunities", [])
        savings = "\n".join(f"  - {o.get('area', '')}: save {o.get('potential_savings', '')}" for o in opts[:2])
        return f"Estimated cost: {cost}\nTop savings:\n{savings}"
    elif agent_type == "security":
        assessment = parsed.get("security_assessment", {})
        risk = assessment.get("overall_risk_rating", "N/A")
        findings = assessment.get("findings", [])
        gaps = [f.get("control", "") for f in findings if f.get("status") in ("CRITICAL GAP", "CONFIGURATION NEEDED")]
        gap_text = "\n".join(f"  - {g}" for g in gaps[:3])
        return f"Risk rating: {risk}\nAction items:\n{gap_text}"
    elif agent_type == "compliance":
        assessment = parsed.get("compliance_assessment", {})
        frameworks = ", ".join(assessment.get("applicable_frameworks", []))
        findings = assessment.get("findings", [])
        violations = [f.get("control", "") for f in findings if f.get("status") == "POTENTIAL VIOLATION"]
        vio_text = "\n".join(f"  - {v}" for v in violations[:3])
        return f"Frameworks: {frameworks}\nPotential violations:\n{vio_text}"
    return "Analysis complete."


@app.command()
def interactive():
    """Interactive mode - describe infrastructure needs conversationally."""
    print_header()
    console.print("[bold cyan]Interactive Mode[/bold cyan]")
    console.print("Describe your infrastructure need. Type 'exit' to quit.\n")

    while True:
        try:
            user_input = console.input("[bold green]> [/bold green]")
            if user_input.lower() in ("exit", "quit", "q"):
                break
            if not user_input.strip():
                continue

            region = ""
            parts = user_input.split("--region" if "--region" in user_input else "-r")
            if len(parts) > 1:
                user_input = parts[0].strip()
                region_parts = parts[1].strip().split()
                if region_parts:
                    region = region_parts[0]

            run(prompt=user_input, region=region, verbose=False)
        except (EOFError, KeyboardInterrupt):
            break


@app.command()
def list():
    """List all sessions."""
    sessions = orchestrator.list_sessions()
    if not sessions:
        console.print("[yellow]No sessions yet.[/yellow]")
        return

    table = Table(title="Sessions", box=box.ROUNDED)
    table.add_column("Session ID", style="cyan", no_wrap=True)
    table.add_column("Status", style="green")
    table.add_column("Region", style="yellow")
    table.add_column("Conflicts", style="red")
    table.add_column("Artifacts", style="blue")
    table.add_column("Duration", style="dim")

    for s in sessions:
        n_conflicts = len(orchestrator.conflicts.get(s.id, []))
        n_artifacts = len(orchestrator.artifacts.get(s.id, []))
        duration = f"{s.duration_seconds:.1f}s" if s.duration_seconds else "N/A"
        table.add_row(
            s.id,
            s.status.value,
            s.region or "N/A",
            str(n_conflicts),
            str(n_artifacts),
            duration,
        )
    console.print(table)


def run_cli(args: list[str]):
    """Entry point called from run.py with remaining args."""
    if not args:
        sys.argv = ["ai-architect-panel", "--help"]
    else:
        sys.argv = ["ai-architect-panel"] + args
    app()


if __name__ == "__main__":
    app()
