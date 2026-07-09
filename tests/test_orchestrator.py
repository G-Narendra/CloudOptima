"""Integration tests for the orchestrator - session lifecycle, conflict detection, artifacts."""

import pytest
from src.core.orchestrator import Orchestrator
from src.core.models import AgentType, SessionStatus, ArbitrationDecision


@pytest.fixture
def orch():
    """Create a fresh Orchestrator for each test."""
    return Orchestrator()


@pytest.mark.asyncio
async def test_full_session_flow(orch):
    """Run a complete end-to-end session and verify output artifacts."""
    session = orch.create_session()
    orch.add_requirement(session.id, "Test HIPAA-compliant storage in India", "india")
    assert session.status == SessionStatus.REQUIREMENT_EXTRACTED

    turns = await orch.run_all_agents(session.id)
    assert len(turns) == 4
    assert all(t.status == "completed" for t in turns)
    assert session.status == SessionStatus.AGENTS_COMPLETE

    arb = await orch.run_judge(session.id)
    assert arb.session_id == session.id
    assert arb.final_recommendation
    assert arb.rationale
    assert session.status == SessionStatus.ARBITRATION_COMPLETE

    artifacts = orch.generate_artifacts(session.id)
    assert len(artifacts) == 5

    artifact_types = [a.artifact_type for a in artifacts]
    assert "iac" in artifact_types
    assert "cost_forecast" in artifact_types
    assert "compliance_report" in artifact_types
    assert "rationale" in artifact_types

    iac_artifacts = [a for a in artifacts if a.artifact_type == "iac"]
    formats = [a.format for a in iac_artifacts]
    assert "bicep" in formats
    assert "terraform" in formats


@pytest.mark.asyncio
async def test_conflict_detection(orch):
    """Verify conflicts are detected from mock agent outputs."""
    session = orch.create_session()
    orch.add_requirement(session.id, "Test deployment in India", "india")

    turns = await orch.run_all_agents(session.id)
    conflicts = orch.conflicts.get(session.id, [])
    assert len(conflicts) > 0

    for conflict in conflicts:
        assert conflict.dimension is not None
        assert conflict.agent_a_type is not None
        assert conflict.agent_b_type is not None
        assert conflict.summary


@pytest.mark.asyncio
async def test_agent_turn_records(orch):
    """Verify all agent turns are recorded with correct metadata."""
    session = orch.create_session()
    orch.add_requirement(session.id, "Test requirement")

    turns = await orch.run_all_agents(session.id)
    stored_turns = orch.turns.get(session.id, [])

    assert len(stored_turns) == 4
    agent_types = [t.agent_type for t in stored_turns]
    assert AgentType.ARCHITECT in agent_types
    assert AgentType.COST in agent_types
    assert AgentType.SECURITY in agent_types
    assert AgentType.COMPLIANCE in agent_types

    for turn in stored_turns:
        assert turn.session_id == session.id
        assert turn.status == "completed"
        assert turn.output_text
        assert turn.duration_ms is not None


@pytest.mark.asyncio
async def test_judge_handles_conflicts(orch):
    """Verify the Judge produces resolutions for detected conflicts."""
    session = orch.create_session()
    orch.add_requirement(session.id, "Test deployment in India", "india")

    turns = await orch.run_all_agents(session.id)
    arb = await orch.run_judge(session.id)

    assert arb.rationale
    assert arb.final_recommendation
    assert len(arb.conflict_ids) > 0


def test_session_management(orch):
    """Verify session creation, listing, and retrieval."""
    session1 = orch.create_session("user1")
    assert len(orch.list_sessions()) >= 1
    assert orch.get_session(session1.id) is not None


def test_multiple_sessions(orch):
    """Verify multiple sessions with different users can coexist."""
    s1 = orch.create_session("user1")
    s2 = orch.create_session("user2")
    sessions = orch.list_sessions()
    assert len(sessions) == 2
    assert any(s.user_id == "user1" for s in sessions)
    assert any(s.user_id == "user2" for s in sessions)


def test_add_requirement(orch):
    """Verify adding a requirement updates session state."""
    session = orch.create_session()
    req = orch.add_requirement(session.id, "Test requirement", "eu")
    assert req.raw_text == "Test requirement"
    assert req.target_region == "eu"
    assert session.region == "eu"


def test_artifact_generation_structure(orch):
    """Verify artifact generation produces valid output without running agents."""
    session = orch.create_session()
    orch.add_requirement(session.id, "Test", "india")

    arb = ArbitrationDecision(
        session_id=session.id,
        final_recommendation="Test recommendation",
        rationale="Test rationale",
    )
    orch.arbitrations[session.id] = arb

    artifacts = orch.generate_artifacts(session.id)
    assert len(artifacts) == 5

    for artifact in artifacts:
        assert artifact.session_id == session.id
        assert artifact.content


def test_session_lifecycle_states(orch):
    """Verify session status transitions through lifecycle."""
    session = orch.create_session()
    assert session.status == SessionStatus.PENDING

    orch.add_requirement(session.id, "test")
    assert session.status == SessionStatus.REQUIREMENT_EXTRACTED

    orch.complete_session(session.id, approved=True)
    assert session.status == SessionStatus.HUMAN_APPROVED
    assert session.duration_seconds is not None
