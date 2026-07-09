# Contributing to AI Architect Panel

## Development Setup

```bash
# Clone the repo
git clone <repo-url>
cd ai-architect-panel

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate      # Windows

# Install dev dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov mypy

# Copy environment config
cp .env.example .env
```

## Project Structure

```
ai-architect-panel/
├── src/
│   └── core/
│       ├── __init__.py
│       ├── agent_base.py         # Base agent + system prompts
│       ├── agent_schemas.py      # Pydantic response schemas
│       ├── config.py             # pydantic-settings config
│       ├── compliance_rules.py   # RAG compliance rules
│       ├── compliance_rag.py     # Vector store for compliance
│       ├── health.py             # Health check endpoint
│       ├── llm_cache.py          # Disk-persisted LLM cache
│       ├── llm_client.py         # LLM client abstraction
│       ├── models.py             # Pydantic data models
│       ├── nvidia_client.py      # NVIDIA NIMs API client
│       ├── observability.py      # Tracing, audit, metrics
│       ├── orchestrator.py       # Session orchestrator
│       └── sentry.py             # Sentry error tracking
├── tests/
│   ├── test_agent_schemas.py
│   ├── test_compliance.py
│   ├── test_dashboard_helpers.py
│   ├── test_health.py
│   ├── test_llm_cache.py
│   ├── test_models.py
│   ├── test_observability.py
│   ├── test_orchestrator.py
│   ├── test_pricing.py
│   └── test_sentry.py
├── dashboard.py                  # Streamlit UI
├── requirements.txt
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

## How to Add a New Agent

Adding a new specialist agent requires only **~15 lines of code** across 4 files:

### 1. Define the schema (`src/core/agent_schemas.py`)

```python
class NewAgentResponse(BaseModel):
    analysis: NewAgentAnalysis = Field(default_factory=NewAgentAnalysis)

AGENT_RESPONSE_SCHEMAS[AgentType.NEW_AGENT] = NewAgentResponse
```

### 2. Add the agent type (`src/core/models.py`)

```python
class AgentType(str, Enum):
    NEW_AGENT = "new_agent"
```

### 3. Write the system prompt (`src/core/agent_base.py`)

```python
SYSTEM_PROMPTS[AgentType.NEW_AGENT] = (
    "You are an expert in ... Output JSON with the following structure: ..."
)
```

### 4. Register in the orchestrator (`src/core/orchestrator.py`)

```python
self.agents[AgentType.NEW_AGENT] = BaseAgent(AgentType.NEW_AGENT)
```

### 5. Add to the dashboard (`dashboard.py`)

```python
AGENT_CONFIG["new_agent"] = {
    "icon": ":material/rocket:",
    "label": "New Agent",
    "color": "#FF5733",
    "desc": "Description of what this agent does",
}
```

### 6. Write tests

```python
# tests/test_agent_schemas.py
def test_new_agent_validation():
    raw = json.dumps({"analysis": {"result": "test"}})
    result = validate_agent_output(raw, AgentType.NEW_AGENT)
    assert result["analysis"]["result"] == "test"
```

## Coding Standards

### Type Hints
Every function must have type annotations, including return types:
```python
def get_stats(self) -> dict:
    ...
```

### Error Handling
- Wrap all external I/O in try/except
- Log the error WITH context (don't silently `except: pass`)
- Never let external failures crash the main flow
```python
try:
    result = external_call()
except Exception as e:
    logger.warning(f"Operation failed for {context}: {e}")
    return fallback_value
```

### Logging
- Use `logger.info()` for lifecycle events
- Use `logger.warning()` for recoverable failures
- Use `logger.error()` for unrecoverable failures
- Use `logger.debug()` for detailed trace information

### Testing
- Every new feature must include tests
- Test happy paths, edge cases, AND failure modes
- Use descriptive test names: `test_cache_eviction_when_over_max_size`
- Mock external services (Sentry, NVIDIA API) in unit tests
- Run the full suite before submitting: `pytest tests/ -v`

### Naming Conventions
- Classes: `PascalCase` (e.g., `WorkflowTracer`, `LLMCache`)
- Functions/methods: `snake_case` (e.g., `detect_conflicts`, `extract_json_from_llm_output`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TTL_SECONDS`, `AGENT_CONFIG`)
- Private methods: `_leading_underscore` (e.g., `_evict_oldest`)

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/core/ --cov-report=term-missing

# Run specific test file
pytest tests/test_llm_cache.py -v

# Run specific test class
pytest tests/test_llm_cache.py::TestDiskPersistence -v

# Run with warnings
pytest tests/ -v -W all
```

## Pull Request Checklist

- [ ] Tests pass: `pytest tests/ -v -q`
- [ ] New tests added for new functionality
- [ ] Type hints added to all new functions
- [ ] Docstrings added to all new public functions/classes
- [ ] Logging added for important events
- [ ] Error handling covers external failures gracefully
- [ ] No `except: pass` without logging
- [ ] Constants defined at module top (not magic numbers)
- [ ] `.env.example` updated if new config vars added

## Release Process

1. Update version in `src/config.py`
2. Run full test suite
3. Update `CHANGELOG.md`
4. Tag release: `git tag v1.0.0`
5. Push tags: `git push --tags`

## Architecture Decisions

| Decision | Rationale |
|---|---|
| Sequential agent execution | Each agent's output feeds the next context window |
| Pydantic over raw JSON | Type-safe validation, defaults, IDE autocompletion |
| Threading.Lock over asyncio.Lock | Cache used in both sync and async contexts |
| Wall-clock timestamps (time.time()) | TTLs work correctly across process restarts |
| FIFO eviction over LRU | Simpler implementation, adequate for 1000-entry cache |
| sentry_sdk import inside functions | Avoids import errors if SDK is not installed |
