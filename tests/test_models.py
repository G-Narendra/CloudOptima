"""Tests for data models - Session, AgentTurn, Conflict, Arbitration, etc."""

from src.core.models import (
    Session, SessionStatus, AgentTurn, AgentType, Conflict,
    ConflictDimension, ArbitrationDecision, ComplianceRule,
    Requirement, Artifact,
)


def test_session_creation():
    """Verify a session gets a unique ID and default status."""
    session = Session()
    assert session.id.startswith("session_")
    assert session.status == SessionStatus.PENDING
    assert session.user_id == "demo_user"
    assert session.created_at is not None


def test_session_with_requirement():
    """Verify a session can store a parsed requirement."""
    session = Session()
    req = Requirement(
        raw_text="I need HIPAA-compliant storage in India",
        target_region="india",
        compliance_frameworks=["HIPAA", "DPDP"],
    )
    session.requirement = req
    session.region = "india"
    assert session.requirement.target_region == "india"
    assert "HIPAA" in session.requirement.compliance_frameworks


def test_agent_turn_creation():
    """Verify an AgentTurn gets a unique ID and correct agent type."""
    turn = AgentTurn(
        session_id="test_session",
        agent_type=AgentType.ARCHITECT,
        input_text="Design a storage solution",
        output_text='{"architecture": {"compute": "AKS"}}',
    )
    assert turn.id.startswith("turn_")
    assert turn.agent_type == AgentType.ARCHITECT
    assert turn.status == "pending"


def test_conflict_creation():
    """Verify a conflict records both agent positions."""
    conflict = Conflict(
        session_id="test_session",
        dimension=ConflictDimension.COST_VS_COMPLIANCE,
        agent_a_turn_id="turn_1",
        agent_b_turn_id="turn_2",
        agent_a_type=AgentType.COST,
        agent_b_type=AgentType.COMPLIANCE,
        summary="Cost vs Compliance disagreement",
    )
    assert conflict.id.startswith("conflict_")
    assert conflict.dimension == ConflictDimension.COST_VS_COMPLIANCE
    assert conflict.agent_a_type == AgentType.COST


def test_arbitration_decision():
    """Verify arbitration records which agent was overruled and why."""
    decision = ArbitrationDecision(
        session_id="test_session",
        conflict_ids=["conflict_1", "conflict_2"],
        final_recommendation="Use LRS storage",
        rationale="GRS violates DPDP data residency",
        resolved_in_favor_of="Compliance",
        overruled="Cost",
    )
    assert decision.id.startswith("arb_")
    assert decision.resolved_in_favor_of == "Compliance"
    assert decision.overruled == "Cost"
    assert not decision.is_plain_language


def test_compliance_rule():
    """Verify a compliance rule stores region, framework, and constraint type."""
    rule = ComplianceRule(
        id="IN-DPDP-001",
        region="india",
        governing_framework="India DPDP Act 2023",
        constraint_type="residency",
        constraint_text="Personal data must be stored in India",
        source_citation="DPDP Act 2023, Section 16",
        applies_to_services=["Azure Blob Storage"],
        active=True,
    )
    assert rule.region == "india"
    assert rule.active


def test_artifact_creation():
    """Verify a generated artifact stores type, format, and content."""
    artifact = Artifact(
        session_id="test_session",
        artifact_type="iac",
        format="bicep",
        content="param location string",
    )
    assert artifact.artifact_type == "iac"
    assert artifact.format == "bicep"


def test_session_status_enum():
    """Verify all expected status values exist."""
    assert SessionStatus.PENDING.value == "pending"
    assert SessionStatus.ARBITRATION_COMPLETE.value == "arbitration_complete"
    assert SessionStatus.HUMAN_APPROVED.value == "human_approved"
