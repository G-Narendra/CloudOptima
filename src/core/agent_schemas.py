"""
CloudOptima — Pydantic Validation Schemas for Agent Outputs

Replaces ad-hoc JSON regex parsing with typed, validated Pydantic models.
Every agent response is validated against its schema at parse time.
"""

from __future__ import annotations
import json
import logging
import re
from typing import Optional
from pydantic import BaseModel, Field, ValidationError

from src.core.models import AgentType

logger = logging.getLogger(__name__)

# ─── Architect Schema ────────────────────────────────────────────────


class ComputeRecommendation(BaseModel):
    recommendation: str = ""
    justification: str = ""
    alternatives: list[str] = Field(default_factory=list)


class StorageRecommendation(BaseModel):
    recommendation: str = ""
    justification: str = ""
    alternatives: list[str] = Field(default_factory=list)


class NetworkingRecommendation(BaseModel):
    recommendation: str = ""
    justification: str = ""
    alternatives: list[str] = Field(default_factory=list)


class DataRecommendation(BaseModel):
    recommendation: str = ""
    justification: str = ""
    alternatives: list[str] = Field(default_factory=list)


class ArchitectureDesign(BaseModel):
    compute: ComputeRecommendation = Field(default_factory=ComputeRecommendation)
    storage: StorageRecommendation = Field(default_factory=StorageRecommendation)
    networking: NetworkingRecommendation = Field(default_factory=NetworkingRecommendation)
    data: DataRecommendation = Field(default_factory=DataRecommendation)


class ArchitectResponse(BaseModel):
    architecture: ArchitectureDesign = Field(default_factory=ArchitectureDesign)
    summary: str = ""


# ─── Cost Schema ─────────────────────────────────────────────────────


class CostOptimization(BaseModel):
    area: str = ""
    potential_savings: str = ""
    recommendation: str = ""


class CostConflictItem(BaseModel):
    item: str = ""
    architect_recommends: str = ""
    cost_concern: str = ""
    estimated_savings: str = ""


class CostAnalysis(BaseModel):
    estimated_monthly_cost: str = ""
    cost_breakdown: dict[str, str] = Field(default_factory=dict)
    cost_optimization_opportunities: list[CostOptimization] = Field(default_factory=list)
    budget_alert_threshold: str = ""
    conflicts_with_architect: list[CostConflictItem] = Field(default_factory=list)


class CostResponse(BaseModel):
    analysis: CostAnalysis = Field(default_factory=CostAnalysis)


# ─── Security Schema ─────────────────────────────────────────────────


class SecurityFinding(BaseModel):
    control: str = ""
    status: str = ""
    details: str = ""
    risk_if_unaddressed: str = ""


class SecurityConflictItem(BaseModel):
    item: str = ""
    architect_recommends: str = ""
    security_concern: str = ""
    recommendation: str = ""


class SecurityAssessment(BaseModel):
    overall_risk_rating: str = "MEDIUM"
    findings: list[SecurityFinding] = Field(default_factory=list)
    conflicts_with_architect: list[SecurityConflictItem] = Field(default_factory=list)


class SecurityResponse(BaseModel):
    security_assessment: SecurityAssessment = Field(default_factory=SecurityAssessment)


# ─── Compliance Schema ───────────────────────────────────────────────


class ComplianceFinding(BaseModel):
    framework: str = ""
    constraint_type: str = ""
    requirement: str = ""
    status: str = "NOT COVERED"
    details: str = ""
    source_citation: str = ""
    recommendation: str = ""


class ComplianceConflictItem(BaseModel):
    item: str = ""
    architect_recommends: str = ""
    compliance_concern: str = ""
    recommendation: str = ""


class ComplianceAssessment(BaseModel):
    target_region: str = ""
    applicable_frameworks: list[str] = Field(default_factory=list)
    findings: list[ComplianceFinding] = Field(default_factory=list)
    conflicts_with_architect: list[ComplianceConflictItem] = Field(default_factory=list)
    disclaimer: str = ""


class ComplianceResponse(BaseModel):
    compliance_assessment: ComplianceAssessment = Field(default_factory=ComplianceAssessment)


# ─── Judge Schema ────────────────────────────────────────────────────


class ConflictSummary(BaseModel):
    dimension: str = ""
    agents_involved: list[str] = Field(default_factory=list)
    issue: str = ""
    resolution: str = ""
    rationale: str = ""
    overruled_agent: Optional[str] = None
    resolved_in_favor_of: Optional[str] = None


class FinalVerdict(BaseModel):
    approved_architecture: str = ""
    plain_language_summary: str = ""


class Arbitration(BaseModel):
    conflicts_detected: int = 0
    conflict_summaries: list[ConflictSummary] = Field(default_factory=list)
    final_verdict: FinalVerdict = Field(default_factory=FinalVerdict)


class JudgeResponse(BaseModel):
    arbitration: Arbitration = Field(default_factory=Arbitration)
    disclaimer: str = ""


# ─── Schema Registry ─────────────────────────────────────────────────

AGENT_RESPONSE_SCHEMAS: dict[AgentType, type[BaseModel]] = {
    AgentType.ARCHITECT: ArchitectResponse,
    AgentType.COST: CostResponse,
    AgentType.SECURITY: SecurityResponse,
    AgentType.COMPLIANCE: ComplianceResponse,
    AgentType.JUDGE: JudgeResponse,
}


# ─── Validation Functions ────────────────────────────────────────────


def extract_json_from_llm_output(output_text: str) -> str:
    """Extract JSON string from LLM output (handles code fences and extra text)."""
    if not output_text:
        return "{}"

    # Try ```json ... ``` first
    if "```json" in output_text:
        return output_text.split("```json")[1].split("```")[0].strip()

    # Try ``` ... ``` (any code fence)
    if "```" in output_text:
        return output_text.split("```")[1].split("```")[0].strip()

    # Try to find a JSON object directly
    match = re.search(r"\{.*\}", output_text, re.DOTALL)
    if match:
        return match.group()

    return output_text.strip()


def validate_agent_output(
    output_text: str,
    agent_type: AgentType,
) -> dict:
    """Parse and validate agent output against its Pydantic schema.

    Returns a validated dict (or partial dict with defaults on failure).
    Logs validation errors but never crashes — ensures graceful degradation.
    """
    schema = AGENT_RESPONSE_SCHEMAS.get(agent_type)
    if not schema:
        logger.warning(f"No schema registered for agent type: {agent_type}")
        return {"raw_response": output_text}

    try:
        json_str = extract_json_from_llm_output(output_text)
        parsed = json.loads(json_str)
        validated = schema.model_validate(parsed)
        return validated.model_dump(exclude_none=False)

    except json.JSONDecodeError as e:
        logger.warning(f"JSON decode failed for {agent_type}: {e}")
        return {"raw_response": output_text, "_error": f"JSON decode failed: {e}"}

    except ValidationError as e:
        logger.warning(f"Pydantic validation failed for {agent_type}: {e}")
        return {"raw_response": output_text, "_error": f"Validation failed: {e}"}

    except Exception as e:
        logger.error(f"Unexpected error validating {agent_type} output: {e}")
        return {"raw_response": output_text, "_error": str(e)}


def extract_conflicts_from_validated(
    validated_output: dict,
    agent_type: AgentType,
) -> list[dict]:
    """Extract conflict items from a validated agent output dict."""
    if agent_type == AgentType.ARCHITECT:
        return []

    if agent_type == AgentType.COST:
        analysis = validated_output.get("analysis", {})
        return analysis.get("conflicts_with_architect", [])

    if agent_type == AgentType.SECURITY:
        assessment = validated_output.get("security_assessment", {})
        return assessment.get("conflicts_with_architect", [])

    if agent_type == AgentType.COMPLIANCE:
        assessment = validated_output.get("compliance_assessment", {})
        return assessment.get("conflicts_with_architect", [])

    return []
