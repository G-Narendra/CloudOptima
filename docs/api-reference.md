# API Reference — The AI Architect Panel

Base URL: `http://localhost:8000/api/v1`

## Authentication

This prototype does not require authentication. CORS is configured to allow all origins for development use.

## Endpoints

### Health Check

```
GET /api/v1/health
```

Returns system status and configuration.

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "timestamp": "2026-07-07T10:00:00+00:00",
  "checks": {
    "orchestrator": "available",
    "nvidia_api": "demo_mode"
  }
}
```

### Create Session

```
POST /api/v1/sessions
```

Create a new session and register the user's infrastructure requirement.

**Request Body:**
```json
{
  "user_input": "I need a HIPAA-compliant patient data pipeline hosted in India",
  "region": "india",
  "user_id": "demo_user"
}
```

**Response:**
```json
{
  "session_id": "session_a1b2c3d4e5f6",
  "status": "requirement_extracted",
  "region": "india",
  "created_at": "2026-07-07T10:00:00+00:00",
  "requirement_text": "I need a HIPAA-compliant patient data pipeline hosted in India"
}
```

### List Sessions

```
GET /api/v1/sessions
```

Returns all sessions.

**Response:**
```json
[
  {
    "session_id": "session_a1b2c3d4e5f6",
    "status": "completed",
    "region": "india",
    "created_at": "2026-07-07T10:00:00+00:00",
    "requirement_text": "..."
  }
]
```

### Get Session

```
GET /api/v1/sessions/{session_id}
```

Returns complete session details including agent turns, conflicts, and arbitration.

**Response:**
```json
{
  "session": {
    "id": "session_a1b2c3d4e5f6",
    "status": "arbitration_complete",
    "region": "india",
    "created_at": "...",
    "duration_seconds": null,
    "requirement": { "raw_text": "...", "target_region": "india", ... }
  },
  "agent_turns": [
    {
      "id": "turn_...",
      "agent_type": "architect",
      "status": "completed",
      "duration_ms": 123,
      "output_text": "{...}",
      "error": null
    }
  ],
  "conflicts": [
    {
      "id": "conflict_...",
      "dimension": "cost_vs_compliance",
      "agents": ["cost", "compliance"],
      "summary": "Conflict between cost and compliance: 2 disagreement(s) detected"
    }
  ],
  "arbitration": {
    "id": "arb_...",
    "final_recommendation": "Use LRS/ZRS storage within India region...",
    "rationale": "...",
    "resolved_in_favor_of": "Compliance",
    "overruled": "Cost"
  }
}
```

### Run Session Agents

```
POST /api/v1/sessions/{session_id}/run
```

Runs all 4 specialist agents, conflict detection, arbitration, and artifact generation.

**Response:**
```json
{
  "session_id": "session_a1b2c3d4e5f6",
  "status": "artifacts_generated",
  "agent_turns_completed": 4,
  "conflicts_detected": 3,
  "artifacts_generated": 5
}
```

### Get Agent Trace

```
GET /api/v1/sessions/{session_id}/agents
```

Returns full agent outputs for a session.

### Get Conflicts

```
GET /api/v1/sessions/{session_id}/conflicts
```

Returns detailed conflict information including agent positions.

### Get Arbitration

```
GET /api/v1/sessions/{session_id}/arbitration
```

Returns the Judge's final decision and full rationale.

### Get Artifacts

```
GET /api/v1/sessions/{session_id}/artifacts
```

Returns all generated artifacts.

**Response:**
```json
[
  {
    "id": "art_...",
    "artifact_type": "iac",
    "format": "bicep",
    "content": "// Bicep template content..."
  },
  {
    "id": "art_...",
    "artifact_type": "cost_forecast",
    "format": "json",
    "content": "{\"analysis\": {...}}"
  },
  {
    "id": "art_...",
    "artifact_type": "compliance_report",
    "format": "markdown",
    "content": "# Compliance Assessment Report..."
  },
  {
    "id": "art_...",
    "artifact_type": "rationale",
    "format": "markdown",
    "content": "# Arbitration Rationale..."
  }
]
```

### Get Artifact by Type

```
GET /api/v1/sessions/{session_id}/artifacts/{artifact_type}
```

Filter by type (`iac`, `cost-forecast`, `compliance-report`, `rationale`) and optional format.

### Approve Session

```
POST /api/v1/sessions/{session_id}/approve
```

Human approval gate — marks session as approved for deployment.

**Response:**
```json
{
  "session_id": "session_a1b2c3d4e5f6",
  "status": "human_approved"
}
```

## Error Responses

All endpoints return standard HTTP errors:

```json
{
  "detail": "Session not found"
}
```

| Status | Meaning |
|---|---|
| 200 | Success |
| 404 | Session or resource not found |
| 422 | Validation error (invalid request body) |
| 500 | Internal server error |

## Data Types

| Field | Type | Description |
|---|---|---|
| session_id | string | UUID-style unique identifier (prefixed `session_`) |
| status | string | One of 11 session lifecycle states |
| region | string | Target Azure region (alias or canonical name) |
| artifact_type | string | `iac`, `cost_forecast`, `compliance_report`, `rationale` |
| format | string | `bicep`, `terraform`, `json`, `markdown` |
