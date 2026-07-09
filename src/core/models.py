"""The AI Architect Panel - Data Models."""

from __future__ import annotations
import uuid
from enum import Enum
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


def _unique_id(prefix: str = "") -> str:
    """Generate a unique ID with prefix."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


class AgentType(str, Enum):
    """The five specialist agent roles."""
    ARCHITECT = "architect"
    COST = "cost"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    JUDGE = "judge"


class SessionStatus(str, Enum):
    PENDING = "pending"
    REQUIREMENT_EXTRACTED = "requirement_extracted"
    AGENTS_RUNNING = "agents_running"
    AGENTS_COMPLETE = "agents_complete"
    ARBITRATING = "arbitrating"
    ARBITRATION_COMPLETE = "arbitration_complete"
    ARTIFACTS_GENERATED = "artifacts_generated"
    COMPLETED = "completed"
    FAILED = "failed"
    HUMAN_APPROVAL_PENDING = "human_approval_pending"
    HUMAN_APPROVED = "human_approved"
    HUMAN_REJECTED = "human_rejected"


class ConflictDimension(str, Enum):
    COST_VS_SECURITY = "cost_vs_security"
    COST_VS_COMPLIANCE = "cost_vs_compliance"
    SECURITY_VS_COMPLIANCE = "security_vs_compliance"
    ARCHITECT_VS_COST = "architect_vs_cost"
    ARCHITECT_VS_SECURITY = "architect_vs_security"
    ARCHITECT_VS_COMPLIANCE = "architect_vs_compliance"


class Requirement(BaseModel):
    """Structured requirement extracted from plain-language input."""
    raw_text: str
    workload_description: str = ""
    target_region: str = ""
    compliance_frameworks: list[str] = Field(default_factory=list)
    estimated_scale: str = ""  # small / medium / large / unknown
    key_services: list[str] = Field(default_factory=list)
    special_constraints: list[str] = Field(default_factory=list)


class Session(BaseModel):
    """A single design session."""
    id: str = Field(default_factory=lambda: _unique_id("session_"))
    status: SessionStatus = SessionStatus.PENDING
    requirement: Optional[Requirement] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str = "demo_user"
    region: str = ""
    duration_seconds: Optional[float] = None


class AgentTurn(BaseModel):
    """A single agent's response in a session."""
    id: str = Field(default_factory=lambda: _unique_id("turn_"))
    session_id: str
    agent_type: AgentType
    input_text: str = ""
    output_text: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: Optional[int] = None
    model_used: str = ""
    status: str = "pending"  # pending, running, completed, failed
    error: Optional[str] = None


class Conflict(BaseModel):
    """A detected disagreement between two agent turns."""
    id: str = Field(default_factory=lambda: _unique_id("conflict_"))
    session_id: str
    dimension: ConflictDimension
    agent_a_turn_id: str
    agent_b_turn_id: str
    agent_a_type: AgentType
    agent_b_type: AgentType
    summary: str = ""
    agent_a_position: str = ""
    agent_b_position: str = ""
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ArbitrationDecision(BaseModel):
    """The Judge's resolution of detected conflicts."""
    id: str = Field(default_factory=lambda: _unique_id("arb_"))
    session_id: str
    conflict_ids: list[str] = Field(default_factory=list)
    final_recommendation: str = ""
    rationale: str = ""
    resolved_in_favor_of: Optional[str] = None
    overruled: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_plain_language: bool = False


class ComplianceRule(BaseModel):
    """A structured compliance rule for a specific region."""
    id: str = ""
    region: str
    governing_framework: str
    constraint_type: str  # residency, consent, audit, encryption, breach_notification
    constraint_text: str
    source_citation: str
    applies_to_services: list[str] = Field(default_factory=list)
    active: bool = True


class Artifact(BaseModel):
    """A generated artifact from a session."""
    id: str = Field(default_factory=lambda: _unique_id("art_"))
    session_id: str
    artifact_type: str  # iac, cost_forecast, compliance_report, rationale
    format: str = ""  # bicep, terraform, json, markdown
    content: str = ""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    download_url: Optional[str] = None


class SessionSummary(BaseModel):
    """A complete session summary for export/review."""
    session_id: str
    plain_language_recap: str = ""
    requirement: Optional[Requirement] = None
    agent_turns: list[AgentTurn] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    arbitration: Optional[ArbitrationDecision] = None
    artifacts: list[Artifact] = Field(default_factory=list)
    status: SessionStatus
    duration_seconds: Optional[float] = None
    created_at: Optional[datetime] = None
