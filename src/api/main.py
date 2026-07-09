"""The AI Architect Panel - FastAPI Application."""

from __future__ import annotations
import logging
from typing import Optional
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager

from src.config import settings
from src.core.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

# Global orchestrator instance
orchestrator = Orchestrator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request/Response Models ──────────────────────────────────────────────

class SessionCreateRequest(BaseModel):
    user_input: str
    region: str = ""
    user_id: str = "demo_user"


class SessionResponse(BaseModel):
    session_id: str
    status: str
    region: str
    created_at: str
    requirement_text: Optional[str] = None


class ArtifactResponse(BaseModel):
    id: str
    artifact_type: str
    format: str
    content: str

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    checks: dict


# ─── Endpoints ────────────────────────────────────────────────────────────

@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """System health check endpoint."""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc).isoformat(),
        checks={
            "orchestrator": "available",
            "nvidia_api": "configured" if settings.nvidia_api_key else "demo_mode",
        }
    )


@app.post("/api/v1/sessions", response_model=SessionResponse)
async def create_session(request: SessionCreateRequest):
    """Create a new session and run all agents."""
    session = orchestrator.create_session(user_id=request.user_id)
    orchestrator.add_requirement(session.id, request.user_input, request.region)
    return SessionResponse(
        session_id=session.id,
        status=session.status.value,
        region=session.region,
        created_at=session.created_at.isoformat(),
        requirement_text=session.requirement.raw_text if session.requirement else None,
    )


@app.get("/api/v1/sessions", response_model=list[SessionResponse])
async def list_sessions():
    """List all sessions."""
    return [
        SessionResponse(
            session_id=s.id,
            status=s.status.value,
            region=s.region,
            created_at=s.created_at.isoformat(),
            requirement_text=s.requirement.raw_text if s.requirement else None,
        )
        for s in orchestrator.list_sessions()
    ]


@app.get("/api/v1/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details including all agent turns, conflicts, arbitration, and artifacts."""
    session = orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session": {
            "id": session.id,
            "status": session.status.value,
            "region": session.region,
            "created_at": session.created_at.isoformat(),
            "duration_seconds": session.duration_seconds,
            "requirement": session.requirement.model_dump() if session.requirement else None,
        },
        "agent_turns": [
            {
                "id": t.id,
                "agent_type": t.agent_type.value,
                "status": t.status,
                "duration_ms": t.duration_ms,
                "output_text": t.output_text[:2000] if t.output_text else "",
                "error": t.error,
            }
            for t in orchestrator.turns.get(session_id, [])
        ],
        "conflicts": [
            {
                "id": c.id,
                "dimension": c.dimension.value,
                "agents": [c.agent_a_type.value, c.agent_b_type.value],
                "summary": c.summary,
            }
            for c in orchestrator.conflicts.get(session_id, [])
        ],
        "arbitration": {
            "id": arb.id,
            "final_recommendation": arb.final_recommendation[:1000],
            "rationale": arb.rationale[:3000],
            "resolved_in_favor_of": arb.resolved_in_favor_of,
            "overruled": arb.overruled,
        } if session_id in orchestrator.arbitrations else None,
    }


@app.post("/api/v1/sessions/{session_id}/run")
async def run_session(session_id: str):
    """Run all agents for a session (after creating it)."""
    session = orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    turns = await orchestrator.run_all_agents(session_id)
    arb = await orchestrator.run_judge(session_id)
    artifacts = orchestrator.generate_artifacts(session_id)

    return {
        "session_id": session_id,
        "status": session.status.value,
        "agent_turns_completed": len([t for t in turns if t.status == "completed"]),
        "conflicts_detected": len(orchestrator.conflicts.get(session_id, [])),
        "artifacts_generated": len(artifacts),
    }


@app.get("/api/v1/sessions/{session_id}/agents")
async def get_agent_trace(session_id: str):
    """Get full agent trace for a session."""
    session = orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return [
        {
            "agent_type": t.agent_type.value,
            "status": t.status,
            "duration_ms": t.duration_ms,
            "model_used": t.model_used,
            "output_text": t.output_text,
            "error": t.error,
        }
        for t in orchestrator.turns.get(session_id, [])
    ]


@app.get("/api/v1/sessions/{session_id}/conflicts")
async def get_conflicts(session_id: str):
    """List detected conflicts for a session."""
    return [
        {
            "id": c.id,
            "dimension": c.dimension.value,
            "agent_a_type": c.agent_a_type.value,
            "agent_b_type": c.agent_b_type.value,
            "summary": c.summary,
            "agent_a_position": c.agent_a_position,
            "agent_b_position": c.agent_b_position,
        }
        for c in orchestrator.conflicts.get(session_id, [])
    ]


@app.get("/api/v1/sessions/{session_id}/arbitration")
async def get_arbitration(session_id: str):
    """Get Judge's decision and rationale."""
    arb = orchestrator.arbitrations.get(session_id)
    if not arb:
        raise HTTPException(status_code=404, detail="Arbitration not found for this session")
    return arb.model_dump()


@app.get("/api/v1/sessions/{session_id}/artifacts", response_model=list[ArtifactResponse])
async def get_artifacts(session_id: str):
    """Get all generated artifacts for a session."""
    artifacts = orchestrator.get_artifacts(session_id)
    return [
        ArtifactResponse(
            id=a.id,
            artifact_type=a.artifact_type,
            format=a.format,
            content=a.content[:50000],  # Limit response size
        )
        for a in artifacts
    ]


@app.get("/api/v1/sessions/{session_id}/artifacts/{artifact_type}")
async def get_artifact_by_type(session_id: str, artifact_type: str, format: Optional[str] = None):
    """Get a specific artifact type (iac, cost-forecast, compliance-report, rationale)."""
    artifacts = orchestrator.get_artifacts(session_id)
    matching = [
        a for a in artifacts
        if a.artifact_type == artifact_type
        and (format is None or a.format == format)
    ]
    if not matching:
        raise HTTPException(status_code=404, detail=f"Artifact type '{artifact_type}' not found")
    return matching[0].model_dump()


@app.post("/api/v1/sessions/{session_id}/approve")
async def approve_session(session_id: str):
    """Human approval gate - marks a session as approved for deployment."""
    try:
        orchestrator.complete_session(session_id, approved=True)
        return {"session_id": session_id, "status": "human_approved"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
