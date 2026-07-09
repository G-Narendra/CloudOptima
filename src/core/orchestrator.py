"""Session orchestrator - manages the end-to-end agent workflow with callback hooks.

The Orchestrator supports optional callback hooks (on_agent_done, on_judge_done,
on_conflict_detected) that enable real-time streaming to the dashboard without
the need for a separate OrchestratorService wrapper class.
"""

from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Callable

from src.core.models import (
    Session, SessionStatus, Requirement, AgentTurn, AgentType,
    Conflict, ConflictDimension, ArbitrationDecision, Artifact,
)
from src.core.agent_base import BaseAgent
from src.core.observability import get_tracer, get_audit_logger, TraceEvent, TraceEventType
from src.core.agent_schemas import validate_agent_output, extract_conflicts_from_validated

logger = logging.getLogger(__name__)


class Orchestrator:
    """Manages the multi-agent session lifecycle with full observability.

    Supports optional callback hooks for real-time progress streaming:
        on_agent_done(agent_key: str, info: dict)  — called after each agent
        on_judge_done(conflict_count: int)           — called after judge
        on_conflict_detected(conflict: Conflict)     — called per conflict

    This eliminates the need for a separate OrchestratorService wrapper class,
    removing code duplication while enabling real-time dashboard updates.
    """

    def __init__(self):
        self.sessions: dict[str, Session] = {}
        self.turns: dict[str, list[AgentTurn]] = {}
        self.conflicts: dict[str, list[Conflict]] = {}
        self.arbitrations: dict[str, ArbitrationDecision] = {}
        self.artifacts: dict[str, list[Artifact]] = {}

        # Callback hooks for real-time streaming
        self._on_agent_done: Optional[Callable] = None
        self._on_judge_done: Optional[Callable] = None
        self._on_conflict_detected: Optional[Callable] = None

        # Initialize agents
        self.agents = {
            AgentType.ARCHITECT: BaseAgent(AgentType.ARCHITECT),
            AgentType.COST: BaseAgent(AgentType.COST),
            AgentType.SECURITY: BaseAgent(AgentType.SECURITY),
            AgentType.COMPLIANCE: BaseAgent(AgentType.COMPLIANCE),
            AgentType.JUDGE: BaseAgent(AgentType.JUDGE),
        }

        # Observability
        self.tracer = get_tracer()
        self.audit = get_audit_logger()

    # ─── Callback Registration ─────────────────────────────────────────────

    def set_callbacks(
        self,
        on_agent_done: Optional[Callable] = None,
        on_judge_done: Optional[Callable] = None,
        on_conflict_detected: Optional[Callable] = None,
    ):
        """Register callback hooks for real-time progress streaming.

        Args:
            on_agent_done: Called after each specialist agent completes.
                           Signature: fn(agent_key: str, info: dict)
            on_judge_done: Called after Judge arbitration completes.
                           Signature: fn(conflict_count: int)
            on_conflict_detected: Called for each conflict found.
                                  Signature: fn(conflict: Conflict)
        """
        self._on_agent_done = on_agent_done
        self._on_judge_done = on_judge_done
        self._on_conflict_detected = on_conflict_detected

    def clear_callbacks(self):
        """Remove all registered callback hooks."""
        self._on_agent_done = None
        self._on_judge_done = None
        self._on_conflict_detected = None

    # ─── Session Management ────────────────────────────────────────────────

    def create_session(self, user_id: str = "demo_user") -> Session:
        session = Session(user_id=user_id)
        session.status = SessionStatus.PENDING
        self.sessions[session.id] = session
        self.turns[session.id] = []
        self.conflicts[session.id] = []
        self.artifacts[session.id] = []

        self.tracer.record(TraceEvent(
            event_type=TraceEventType.SESSION_START,
            session_id=session.id,
            metadata={"user_id": user_id},
        ))
        logger.info(f"Created session: {session.id}")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        return self.sessions.get(session_id)

    def list_sessions(self) -> list[Session]:
        return list(self.sessions.values())

    def add_requirement(self, session_id: str, raw_text: str, region: str = "") -> Requirement:
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        req = Requirement(
            raw_text=raw_text,
            target_region=region,
            workload_description=raw_text,
        )
        session.requirement = req
        session.region = region
        session.status = SessionStatus.REQUIREMENT_EXTRACTED
        session.updated_at = datetime.now(timezone.utc)
        return req

    # ─── Agent Execution ───────────────────────────────────────────────────

    async def run_all_agents(self, session_id: str) -> list[AgentTurn]:
        """Run all specialist agents in sequence (architect → cost → security → compliance).

        Calls on_agent_done callback after each agent completes (if registered).
        Detects conflicts between agent pairs after all agents finish.
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.status = SessionStatus.AGENTS_RUNNING
        session.updated_at = datetime.now(timezone.utc)

        user_input = session.requirement.raw_text if session.requirement else "No requirement provided."
        region_context = f"Target deployment region: {session.region}" if session.region else ""

        # Run 4 specialist agents
        specialist_types = [
            (AgentType.ARCHITECT, "architect"),
            (AgentType.COST, "cost"),
            (AgentType.SECURITY, "security"),
            (AgentType.COMPLIANCE, "compliance"),
        ]

        turns = []
        for agent_type, agent_key in specialist_types:
            agent = self.agents[agent_type]
            context_input = f"{user_input}\n\n{region_context}" if region_context else user_input

            # Inject RAG-retrieved compliance rules for the Compliance agent
            extra_context = None
            if agent_type == AgentType.COMPLIANCE and session.region:
                try:
                    from src.core.compliance_rules import get_rules_for_region
                    rules = get_rules_for_region(session.region)
                    if rules:
                        rules_text = "\n\n---\nRETRIEVED COMPLIANCE RULES (RAG):\n"
                        for r in rules:
                            rules_text += (
                                f"- [{r.governing_framework}] {r.constraint_type}: "
                                f"{r.constraint_text}\n"
                                f"  Source: {r.source_citation}\n"
                            )
                        rules_text += "\nUse the above rules to inform your compliance assessment. "
                        rules_text += "Only cite regulations that are provided above or in your known knowledge base.\n---"
                        extra_context = [{"role": "system", "content": rules_text}]
                except Exception as e:
                    logger.warning(f"RAG compliance lookup failed: {e}")

            span_id = self.tracer.start_span(
                TraceEventType.AGENT_START, session_id,
                agent_type=agent_type.value,
                input_summary=user_input[:100],
            )

            turn = await agent.run(session_id, context_input, context=extra_context)
            self.turns[session_id].append(turn)
            turns.append(turn)

            self.tracer.end_span(span_id, output_summary=turn.output_text[:100] if turn.output_text else "",
                                 error=turn.error)
            self.audit.log_decision(
                session_id, "agent_completed", agent_type.value,
                f"Agent {agent_type.value} completed with status {turn.status}",
                evidence={"turn_id": turn.id, "duration_ms": turn.duration_ms},
            )
            logger.info(f"Agent {agent_type} completed: turn_id={turn.id}, status={turn.status}")

            # Fire callback for real-time dashboard updates
            if self._on_agent_done:
                try:
                    self._on_agent_done(agent_key, {
                        "duration_ms": turn.duration_ms or 0,
                        "status": turn.status,
                    })
                except Exception as cb_err:
                    logger.warning(f"on_agent_done callback failed: {cb_err}")

        session.status = SessionStatus.AGENTS_COMPLETE
        session.updated_at = datetime.now(timezone.utc)

        # Detect conflicts between agents
        self._detect_conflicts(session_id, turns)

        return turns

    def _detect_conflicts(self, session_id: str, turns: list[AgentTurn]):
        """Parse agent outputs via Pydantic validation and detect conflicts.

        Uses the structured Pydantic schemas from agent_schemas.py to extract
        conflict items in a type-safe manner. Fires on_conflict_detected callback
        for each conflict found.
        """
        turn_map = {t.agent_type: t for t in turns}

        # Parse each agent's output through Pydantic validation
        validated_outputs = {}
        for agent_type, turn in turn_map.items():
            try:
                validated = validate_agent_output(turn.output_text, agent_type)
                validated_outputs[agent_type] = validated
            except Exception as e:
                logger.warning(f"Failed to validate {agent_type} output: {e}")
                validated_outputs[agent_type] = {}

        agent_pairs = [
            (AgentType.ARCHITECT, AgentType.COST, ConflictDimension.ARCHITECT_VS_COST),
            (AgentType.ARCHITECT, AgentType.SECURITY, ConflictDimension.ARCHITECT_VS_SECURITY),
            (AgentType.ARCHITECT, AgentType.COMPLIANCE, ConflictDimension.ARCHITECT_VS_COMPLIANCE),
            (AgentType.COST, AgentType.COMPLIANCE, ConflictDimension.COST_VS_COMPLIANCE),
            (AgentType.COST, AgentType.SECURITY, ConflictDimension.COST_VS_SECURITY),
            (AgentType.SECURITY, AgentType.COMPLIANCE, ConflictDimension.SECURITY_VS_COMPLIANCE),
        ]

        total_conflicts = 0
        for agent_a_type, agent_b_type, dim in agent_pairs:
            if agent_a_type not in turn_map or agent_b_type not in turn_map:
                continue

            a_conflicts = extract_conflicts_from_validated(
                validated_outputs.get(agent_a_type, {}), agent_a_type
            )
            b_conflicts = extract_conflicts_from_validated(
                validated_outputs.get(agent_b_type, {}), agent_b_type
            )

            all_conflict_items = a_conflicts + b_conflicts
            if not all_conflict_items:
                continue

            conflict = Conflict(
                session_id=session_id,
                dimension=dim,
                agent_a_turn_id=turn_map[agent_a_type].id,
                agent_b_turn_id=turn_map[agent_b_type].id,
                agent_a_type=agent_a_type,
                agent_b_type=agent_b_type,
                summary=f"Conflict between {agent_a_type.value} and {agent_b_type.value}: {len(all_conflict_items)} disagreement(s) detected",
                agent_a_position=json.dumps(all_conflict_items[:3], default=str),
                agent_b_position=json.dumps(all_conflict_items[:3], default=str),
            )
            self.conflicts[session_id].append(conflict)

            self.tracer.record(TraceEvent(
                event_type=TraceEventType.CONFLICT_DETECTED,
                session_id=session_id,
                agent_type=f"{agent_a_type.value}_vs_{agent_b_type.value}",
                metadata={
                    "dimension": dim.value,
                    "conflict_count": len(all_conflict_items),
                    "conflict_id": conflict.id,
                },
            ))
            total_conflicts += 1
            logger.info(f"Conflict detected: {dim.value} ({len(all_conflict_items)} items)")

            # Fire conflict callback
            if self._on_conflict_detected:
                try:
                    self._on_conflict_detected(conflict)
                except Exception as cb_err:
                    logger.warning(f"on_conflict_detected callback failed: {cb_err}")

        if total_conflicts == 0:
            logger.info("No conflicts detected between agents")

    async def run_judge(self, session_id: str) -> ArbitrationDecision:
        """Run the Judge agent to arbitrate detected conflicts.

        Fires on_judge_done callback after arbitration (if registered).
        Records trace + audit events.
        """
        session = self.sessions.get(session_id)
        if not session:
            self.tracer.record(TraceEvent(
                event_type=TraceEventType.ERROR,
                session_id=session_id,
                error="Session not found",
            ))
            raise ValueError(f"Session {session_id} not found")

        session.status = SessionStatus.ARBITRATING
        session.updated_at = datetime.now(timezone.utc)

        span_id = self.tracer.start_span(
            TraceEventType.ARBITRATION_START, session_id,
            agent_type="judge",
            conflict_count=len(self.conflicts.get(session_id, [])),
        )

        turns = self.turns.get(session_id, [])
        conflicts = self.conflicts.get(session_id, [])

        context = []
        for turn in turns:
            if turn.status == "completed":
                context.append({
                    "role": "user",
                    "content": f"[{turn.agent_type.value.upper()} AGENT OUTPUT]:\n{turn.output_text[:2000]}"
                })

        if conflicts:
            conflict_summary = json.dumps([
                {
                    "dimension": c.dimension.value,
                    "agents": [c.agent_a_type.value, c.agent_b_type.value],
                    "summary": c.summary,
                }
                for c in conflicts
            ], indent=2)
            context.append({
                "role": "user",
                "content": f"DETECTED CONFLICTS TO RESOLVE:\n{conflict_summary}"
            })
        else:
            context.append({
                "role": "user",
                "content": "No conflicts were detected. Confirm the design is consistent and produce the final verdict."
            })

        judge = self.agents[AgentType.JUDGE]
        user_input = session.requirement.raw_text if session.requirement else "Review the above agent outputs."

        turn = await judge.run(session_id, user_input, context)
        self.turns[session_id].append(turn)

        parsed = judge.parse_json_output(turn.output_text)
        arbitration_data = parsed.get("arbitration", {})
        final_verdict = arbitration_data.get("final_verdict", {})

        overruled = None
        resolved_in_favor = None
        conflict_summaries = arbitration_data.get("conflict_summaries", [])
        if conflict_summaries:
            first = conflict_summaries[0]
            if first.get("overruled_agent"):
                overruled = first["overruled_agent"]
            if first.get("resolved_in_favor_of"):
                resolved_in_favor = first["resolved_in_favor_of"]

        # Safely convert approved_architecture to string (LLM may return dict)
        approved_arch = final_verdict.get("approved_architecture", turn.output_text[:1000])
        if isinstance(approved_arch, dict):
            approved_arch = json.dumps(approved_arch, indent=2)
        elif not isinstance(approved_arch, str):
            approved_arch = str(approved_arch)

        arb = ArbitrationDecision(
            session_id=session_id,
            conflict_ids=[c.id for c in conflicts],
            final_recommendation=approved_arch,
            rationale=turn.output_text,
            resolved_in_favor_of=resolved_in_favor,
            overruled=overruled,
        )

        plain_language = final_verdict.get("plain_language_summary", "")
        if isinstance(plain_language, dict):
            plain_language = json.dumps(plain_language, indent=2)
        if plain_language:
            plain_arch = final_verdict.get("approved_architecture", "")
            if isinstance(plain_arch, dict):
                plain_arch = json.dumps(plain_arch, indent=2)
            elif not isinstance(plain_arch, str):
                plain_arch = str(plain_arch)

            arb_plain = ArbitrationDecision(
                session_id=session_id,
                conflict_ids=[c.id for c in conflicts],
                final_recommendation=plain_arch,
                rationale=plain_language,
                is_plain_language=True,
            )
            self.arbitrations[f"{session_id}_plain"] = arb_plain

        self.arbitrations[session_id] = arb

        self.tracer.end_span(span_id, output_summary=arb.final_recommendation[:100])

        self.audit.log_decision(
            session_id, "arbitration_complete", "judge",
            f"Arbitrated {len(conflicts)} conflicts. Overruled: {overruled or 'N/A'}, Favored: {resolved_in_favor or 'N/A'}",
            evidence={
                "conflict_ids": [c.id for c in conflicts],
                "overruled": overruled,
                "resolved_in_favor_of": resolved_in_favor,
            },
        )

        session.status = SessionStatus.ARBITRATION_COMPLETE
        session.updated_at = datetime.now(timezone.utc)

        logger.info(f"Arbitration complete for {session_id}: {len(conflicts)} conflicts resolved")

        # Fire judge callback
        if self._on_judge_done:
            try:
                self._on_judge_done(len(conflicts))
            except Exception as cb_err:
                logger.warning(f"on_judge_done callback failed: {cb_err}")

        return arb

    # ─── Artifact Generation ───────────────────────────────────────────────

    def _record_artifact_trace(self, session_id: str, artifact: Artifact):
        """Record a trace event for a generated artifact."""
        self.tracer.record(TraceEvent(
            event_type=TraceEventType.ARTIFACT_GENERATED,
            session_id=session_id,
            metadata={
                "artifact_type": artifact.artifact_type,
                "format": artifact.format,
                "artifact_id": artifact.id,
            },
        ))

    def generate_artifacts(self, session_id: str) -> list[Artifact]:
        """Generate all 5 output artifacts from the arbitrated session."""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        arb = self.arbitrations.get(session_id)
        if not arb:
            raise ValueError(f"No arbitration found for {session_id}")

        turns = self.turns.get(session_id, [])
        architect_turn = next((t for t in turns if t.agent_type == AgentType.ARCHITECT and t.status == "completed"), None)
        cost_turn = next((t for t in turns if t.agent_type == AgentType.COST and t.status == "completed"), None)

        artifacts = []

        # 1. IaC (Bicep + Terraform)
        iac_content = self._generate_iac(arb, architect_turn)
        for fmt in ["bicep", "terraform"]:
            artifact = Artifact(
                session_id=session_id,
                artifact_type="iac",
                format=fmt,
                content=iac_content[fmt],
            )
            artifacts.append(artifact)
            self._record_artifact_trace(session_id, artifact)

        # 2. Cost Forecast
        cost_content = cost_turn.output_text if cost_turn else "Cost analysis unavailable"
        cost_artifact = Artifact(
            session_id=session_id,
            artifact_type="cost_forecast",
            format="json",
            content=cost_content,
        )
        artifacts.append(cost_artifact)
        self._record_artifact_trace(session_id, cost_artifact)

        # 3. Compliance Report
        compliance_turn = next((t for t in turns if t.agent_type == AgentType.COMPLIANCE and t.status == "completed"), None)
        compliance_content = compliance_turn.output_text if compliance_turn else "Compliance assessment unavailable"
        compliance_artifact = Artifact(
            session_id=session_id,
            artifact_type="compliance_report",
            format="markdown",
            content=self._format_compliance_report(compliance_content),
        )
        artifacts.append(compliance_artifact)
        self._record_artifact_trace(session_id, compliance_artifact)

        # 4. Arbitration Rationale
        rationale_artifact = Artifact(
            session_id=session_id,
            artifact_type="rationale",
            format="markdown",
            content=self._format_rationale(arb),
        )
        artifacts.append(rationale_artifact)
        self._record_artifact_trace(session_id, rationale_artifact)

        self.artifacts[session_id] = artifacts

        self.audit.log_decision(
            session_id, "artifacts_generated", "system",
            f"Generated {len(artifacts)} artifacts",
            evidence={
                "artifact_types": [a.artifact_type for a in artifacts],
                "artifact_formats": [a.format for a in artifacts],
            },
        )

        session.status = SessionStatus.ARTIFACTS_GENERATED
        session.updated_at = datetime.now(timezone.utc)

        return artifacts

    def _generate_iac(self, arb: ArbitrationDecision, architect_turn: Optional[AgentTurn]) -> dict:
        """Generate Bicep and Terraform templates from the arbitrated architecture."""
        architecture_json = "{}"
        if architect_turn and architect_turn.status == "completed":
            try:
                parsed = BaseAgent(AgentType.ARCHITECT).parse_json_output(architect_turn.output_text)
                architecture_json = json.dumps(parsed.get("architecture", {}), indent=2)
            except Exception:
                architecture_json = '{"note": "Architecture details unavailable"}'

        bicep = f"""// The AI Architect Panel - Generated Bicep Template
// Session: {arb.session_id}
// WARNING: This is a template. Review and customize before deployment.
// Human approval is required before applying to any subscription.

// {arb.final_recommendation[:500]}

param location string = resourceGroup().location
param tags object = {{
    project: 'ai-architect-panel'
    session: '{arb.session_id}'
}}

// Resource group for the architecture
resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {{
    name: 'rg-architect-panel-${{uniqueString(resourceGroup().id)}}'
    location: location
    tags: tags
}}

// Note: Full resource definitions would be generated here based on
// the arbitrated architecture output.
// Compute: AKS cluster / App Service
// Storage: Blob Storage / Files
// Network: VNet + Hub-Spoke
// Data: Azure SQL / Cosmos DB

output architectureJson string = '{architecture_json}'
"""

        terraform = f"""# The AI Architect Panel - Generated Terraform Configuration
# Session: {arb.session_id}
# WARNING: This is a template. Review and customize before deployment.
# Human approval is required before applying to any subscription.

# {arb.final_recommendation[:500]}

terraform {{
  required_providers {{
    azurerm = {{
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }}
  }}
}}

provider "azurerm" {{
  features {{}}
}}

locals {{
  project_name = "ai-architect-panel"
  session_id   = "{arb.session_id}"
  tags = {{
    Project = "ai-architect-panel"
    Session = "{arb.session_id}"
  }}
}}

# Note: Full resource definitions would be generated here based on
# the arbitrated architecture output.
# Compute: AKS cluster / App Service
# Storage: Blob Storage / Files
# Network: VNet + Hub-Spoke
# Data: Azure SQL / Cosmos DB

output "architecture_json" {{
  value = jsonencode({architecture_json})
}}
"""

        return {"bicep": bicep, "terraform": terraform}

    def _format_compliance_report(self, compliance_json: str) -> str:
        """Format compliance assessment as a readable markdown report."""
        try:
            data = json.loads(compliance_json)
            assessment = data.get("compliance_assessment", {})
            findings = assessment.get("findings", [])

            report = "# Compliance Assessment Report\n\n"
            report += f"**Target Region:** {assessment.get('target_region', 'N/A')}\n"
            report += f"**Applicable Frameworks:** {', '.join(assessment.get('applicable_frameworks', []))}\n\n"

            for f in findings:
                report += f"## Finding: {f.get('control', 'N/A')}\n"
                report += f"- **Framework:** {f.get('framework', 'N/A')}\n"
                report += f"- **Constraint Type:** {f.get('constraint_type', 'N/A')}\n"
                report += f"- **Status:** {f.get('status', 'N/A')}\n"
                report += f"- **Requirement:** {f.get('requirement', 'N/A')}\n"
                report += f"- **Details:** {f.get('details', 'N/A')}\n"
                report += f"- **Source:** {f.get('source_citation', 'N/A')}\n"
                report += f"- **Recommendation:** {f.get('recommendation', 'N/A')}\n\n"

            report += "---\n"
            report += assessment.get('disclaimer', '*This output is decision support, not legal advice.*')
            return report
        except (json.JSONDecodeError, AttributeError):
            return compliance_json

    def _format_rationale(self, arb: ArbitrationDecision) -> str:
        """Format arbitration rationale as a readable markdown document."""
        return f"""# Arbitration Rationale

**Session:** {arb.session_id}
**Date:** {arb.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

## Final Recommendation

{arb.final_recommendation}

## Full Rationale

{arb.rationale}

---

*This arbitration is based on structured evaluation of agent inputs. Every conflict has been logged with traceable reasoning. Final deployment requires human approval before any Infrastructure-as-Code is applied to a live subscription.*
"""

    def get_artifacts(self, session_id: str) -> list[Artifact]:
        return self.artifacts.get(session_id, [])

    def complete_session(self, session_id: str, approved: bool = True):
        """Complete a session with human approval/rejection. Records trace + audit."""
        session = self.sessions.get(session_id)
        if not session:
            self.tracer.record(TraceEvent(
                event_type=TraceEventType.ERROR,
                session_id=session_id,
                error="Session not found on complete",
            ))
            raise ValueError(f"Session {session_id} not found")

        if approved:
            session.status = SessionStatus.HUMAN_APPROVED
        else:
            session.status = SessionStatus.HUMAN_REJECTED

        session.duration_seconds = (datetime.now(timezone.utc) - session.created_at).total_seconds()
        session.updated_at = datetime.now(timezone.utc)

        self.tracer.record(TraceEvent(
            event_type=TraceEventType.HUMAN_APPROVAL if approved else TraceEventType.SESSION_END,
            session_id=session_id,
            metadata={
                "approved": approved,
                "duration_seconds": session.duration_seconds,
                "agent_turns": len(self.turns.get(session_id, [])),
                "conflicts": len(self.conflicts.get(session_id, [])),
                "artifacts": len(self.artifacts.get(session_id, [])),
            },
        ))

        self.audit.log_decision(
            session_id, "session_complete", "system",
            f"Session {'approved' if approved else 'rejected'} after {session.duration_seconds:.1f}s",
            evidence={
                "approved": approved,
                "duration_seconds": session.duration_seconds,
                "final_status": session.status.value,
            },
        )

        # Export trace to file
        self.tracer.export_to_file(session_id)

    async def run_full_session(self, user_input: str, region: str = "") -> dict:
        """Run a complete end-to-end session. Returns summary."""
        session = self.create_session()
        self.add_requirement(session.id, user_input, region)
        turns = await self.run_all_agents(session.id)
        arb = await self.run_judge(session.id)
        artifacts = self.generate_artifacts(session.id)
        self.complete_session(session.id, approved=False)  # Wait for human approval

        return {
            "session_id": session.id,
            "status": session.status,
            "turns_count": len(turns),
            "conflicts_detected": len(self.conflicts[session.id]),
            "artifacts_generated": len(artifacts),
        }

    def build_result_dict(self, session_id: str) -> dict:
        """Build a complete result dict from a session, suitable for dashboard display."""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        turns = self.turns.get(session_id, [])
        conflicts = self.conflicts.get(session_id, [])
        arb = self.arbitrations.get(session_id)
        artifacts = self.artifacts.get(session_id, [])

        total_time_ms = sum(t.duration_ms or 0 for t in turns)
        agent_timing = {}
        agent_outputs = {}
        for t in turns:
            if t.duration_ms:
                agent_timing[t.agent_type.value] = {"duration_ms": t.duration_ms, "status": t.status}
            if t.status == "completed" and t.output_text:
                try:
                    agent_outputs[t.agent_type.value] = json.loads(t.output_text)
                except json.JSONDecodeError:
                    agent_outputs[t.agent_type.value] = {"raw": t.output_text[:500]}
            else:
                agent_outputs[t.agent_type.value] = {"error": t.error or "No output"}

        final_rec = arb.final_recommendation if arb else ""
        if isinstance(final_rec, dict):
            final_rec = json.dumps(final_rec, indent=2)

        prompt = session.requirement.raw_text if session.requirement else ""

        return {
            "session_id": session_id,
            "prompt": prompt,
            "region": session.region or "",
            "status": "completed",
            "conflicts": [
                {"dimension": c.dimension.value,
                 "agents": [c.agent_a_type.value, c.agent_b_type.value],
                 "summary": c.summary}
                for c in conflicts
            ],
            "arbitration": {
                "final_recommendation": final_rec,
                "overruled": arb.overruled if arb else None,
                "resolved_in_favor_of": arb.resolved_in_favor_of if arb else None,
            } if arb else None,
            "artifacts": [
                {"type": a.artifact_type, "format": a.format, "content": a.content[:2000]}
                for a in artifacts
            ],
            "agent_outputs": agent_outputs,
            "agent_timing": agent_timing,
            "total_time_ms": total_time_ms,
        }
