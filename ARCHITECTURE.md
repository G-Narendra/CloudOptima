# Architecture — The AI Architect Panel

## System Design

### Core Principle: Adversarial Arbitration

Unlike consensus-based multi-agent systems where agents vote or average positions, this system uses **adversarial arbitration** — each agent advocates for its domain expertise, and conflicts are explicitly detected, logged, and resolved by a dedicated Judge agent with traceable rationale.

### Layer Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     User Interface                       │
│              CLI (Rich/Typer) ─── API (FastAPI)           │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                  Orchestrator Layer                      │
│    Session lifecycle · Conflict detection · Artifact gen │
│    Observability (Tracer · Audit · Metrics)              │
└───────┬──────────┬──────────┬──────────┬────────────────┘
        │          │          │          │
┌───────▼──┐ ┌─────▼────┐ ┌──▼──────┐ ┌▼───────────┐
│Architect │ │  Cost    │ │ Security │ │ Compliance  │
│(Compute, │ │(FinOps,  │ │(IAM,     │ │(Data laws,  │
│ Storage, │ │ Pricing, │ │ Encrypt, │ │ Regional    │
│ Network) │ │ RI)      │ │ Network) │ │ Regs)       │
└───────┬──┘ └─────┬────┘ └──┬──────┘ └┬────────────┘
        │          │          │         │
        └──────────┴────┬─────┴─────────┘
                        │
               ┌────────▼────────┐
               │  Judge Agent    │
               │  (Arbitrator)   │
               │  ↓ Resolves     │
               │  conflicts      │
               └────────┬────────┘
                        │
               ┌────────▼────────┐
               │  Artifacts      │
               │  IaC · Cost ·   │
               │  Compliance ·   │
               │  Rationale      │
               └─────────────────┘
```

### Data Flow

1. **User Input** → Plain-language infrastructure requirement + target region
2. **Requirement Extraction** → Structured `Requirement` with region, frameworks, constraints
3. **Parallel Agent Execution** → 4 specialist agents run, each outputs structured JSON
4. **Conflict Detection** → 6 agent-pairs compared across 8 conflict dimensions
5. **Arbitration** → Judge agent reviews conflicts and produces final verdict
6. **Artifact Generation** → 5 artifacts generated (Bicep, Terraform, Cost, Compliance, Rationale)
7. **Human Approval Gate** → Session waits for approval before deployment

## Data Model

### Core Entities

| Model | Fields | Purpose |
|---|---|---|
| `Session` | id, status, region, requirement | Tracks one user request through lifecycle |
| `AgentTurn` | id, agent_type, output_text, status | Records one agent's response |
| `Conflict` | id, dimension, agent_a/b, summary | A detected disagreement between two agents |
| `ArbitrationDecision` | id, conflict_ids, verdict, rationale | The Judge's resolution with reasoning |
| `Artifact` | id, type, format, content | Generated output (IaC, report, etc.) |
| `ComplianceRule` | id, region, framework, constraint | Structured regulatory knowledge |

### Session State Machine

```
PENDING → REQUIREMENT_EXTRACTED → AGENTS_RUNNING → AGENTS_COMPLETE
    → ARBITRATING → ARBITRATION_COMPLETE → ARTIFACTS_GENERATED
        → COMPLETED / FAILED / HUMAN_APPROVED / HUMAN_REJECTED
```

### Conflict Dimensions

| Dimension | Agent A | Agent B | Typical Conflict |
|---|---|---|---|
| COST_VS_SECURITY | Cost | Security | Cheap SKU vs required performance |
| COST_VS_COMPLIANCE | Cost | Compliance | Cheapest storage vs data residency |
| SECURITY_VS_COMPLIANCE | Security | Compliance | Encryption method vs regional standard |
| ARCHITECT_VS_COST | Architect | Cost | Recommended tier vs budget constraints |
| ARCHITECT_VS_SECURITY | Architect | Security | Open architecture vs security hardening |
| ARCHITECT_VS_COMPLIANCE | Architect | Compliance | Global service vs regional requirement |

## LLM Provider Architecture

The `llm_client.py` module provides a unified interface across 5 providers:

```
LLMClient (ABC)
  ├── NvidiaClient    (OpenAI-compatible — default, free)
  ├── OpenAIClient    (GPT-4o)
  ├── AnthropicClient (Claude Opus)
  ├── GoogleClient    (Gemini 1.5 Pro)
  └── DeepSeekClient  (DeepSeek Chat)
```

- **Factory Pattern**: `create_llm_client(provider)` returns the correct client
- **Provider Switching**: Via `LLM_PROVIDER` env var
- **Demo Mode**: When `DEMO_MODE=true` or no API key, returns structured mock responses
- **Retry Logic**: NVIDIA client uses tenacity with exponential backoff (3 attempts)

## Observability System

### WorkflowTracer

- Records `TraceEvent` objects for every significant operation
- Supports span timing (start_span/end_span) for performance tracking
- Exports to JSON files at `.freebuff/traces/`
- OpenTelemetry-compatible export format

### AuditLogger

- Append-only `.audit.jsonl` logs at `.freebuff/audit/`
- Each entry: timestamp, session_id, decision_type, agent, rationale, evidence
- Immutable: entries are never modified after writing

### Trace Event Types

| Event | When |
|---|---|
| SESSION_START / SESSION_END | Session lifecycle |
| AGENT_START / AGENT_END | Each agent execution |
| LLM_CALL_START / LLM_CALL_END | Each LLM API call |
| CONFLICT_DETECTED | Conflict found between agents |
| ARBITRATION_START / ARBITRATION_END | Judge arbitration |
| ARTIFACT_GENERATED | Each output artifact |
| HUMAN_APPROVAL | User approval gate |
| ERROR | Any system error |

## Azure Pricing Database

Sourced from the official [Azure Retail Prices API](https://prices.azure.com/api/retail/prices).

### Data Structure

```
RegionPricing
  ├── region_name      (e.g., "uaenorth")
  ├── display_name     (e.g., "UAE North")
  ├── vm_pricing       (dict of VMSize by SKU)
  ├── storage_pricing  (dict of StorageTier by key)
  └── sql_pricing      (dict of SQLDatabaseSKU by key)
```

### Region Aliasing

20+ user-friendly aliases → canonical region names:
- "dubai", "abudhabi", "uae north", "united arab emirates" → `uaenorth`
- "in", "central india" → `centralindia`
- "eu", "europe", "north europe" → `northeurope`
- "us", "usa", "united states", "east us" → `eastus`

### Coverage

| Region | VM SKUs | Storage Tiers | SQL SKUs |
|---|---|---|---|
| Central India | 22 | 6 | 20 |
| North Europe | 29 | 8 | 20 |
| East US | 27 | 7 | 20 |
| UAE North | 29 | 7 | 20 |

## Compliance Knowledge Base

21 structured rules across 4 frameworks, each with:
- **Source citation** (specific section/article)
- **Constraint type** (residency, consent, audit, encryption, breach_notification)
- **Applicable services** (specific Azure services or "*" for all)
- **Active status** (enabled/disabled)

### Framework Comparison

| Aspect | India DPDP | EU GDPR | US HIPAA | UAE PDPL |
|---|---|---|---|---|
| Residency | Must stay in India | SCC/BCC for transfer | N/A | Adequacy + consent |
| Consent | Explicit, withdrawable | Specific, informed | Minimum necessary | Express consent |
| Breach | Report to Board + principals | 72 hours to authority | HHS + individuals | 72 hours for high-risk |
| Audit | Annual independent | Records on demand | Risk analysis + audit | DPIA + records |
| Penalties | Up to ₹250 Cr | Up to €20M/4% revenue | Up to $1.5M/yr | Up to AED 5M |

## Design Decisions

### Why Not Consensus Voting?
Agents have asymmetric information and expertise. A Cost agent should not have equal weight to a Compliance agent on a data residency question. The Judge provides domain-weighted resolution.

### Why Async Agent Execution?
Currently sequential (due to LLM API rate limits). Architected for parallel execution when rate limits are not a constraint.

### Why Human Approval Gate?
Generated IaC templates deploy real Azure resources. An automated approval pipeline would be irresponsible without human review of the generated templates.

### Why UUIDs for Session IDs?
Previous datetime-based IDs caused collisions when sessions were created rapidly. UUIDs provide guaranteed uniqueness.

## Performance

- 48 unit/integration tests — all passing
- Test suite completes in ~3 seconds
- Full demo session (all 4 agents + Judge) completes in under 5 seconds (demo mode)
- Trace export to JSON averages <50ms per session
