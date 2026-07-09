"""Tests for Pydantic-based structured output validation."""

import json
import pytest
from pydantic import ValidationError

from src.core.models import AgentType
from src.core.agent_schemas import (
    extract_json_from_llm_output,
    validate_agent_output,
    extract_conflicts_from_validated,
    ArchitectResponse,
    CostResponse,
    SecurityResponse,
    ComplianceResponse,
    JudgeResponse,
)


class TestExtractJson:
    """Test JSON extraction from LLM output text."""

    def test_plain_json(self):
        text = '{"architecture": {"compute": {"recommendation": "AKS"}}}'
        assert extract_json_from_llm_output(text) == text

    def test_json_with_code_fence(self):
        text = 'Here is the result:\n```json\n{"architecture": {"compute": "AKS"}}\n```\nEnd.'
        expected = '{"architecture": {"compute": "AKS"}}'
        assert extract_json_from_llm_output(text) == expected

    def test_json_with_plain_fence(self):
        text = 'Output:\n```\n{"analysis": {"estimated_monthly_cost": "$500"}}\n```'
        expected = '{"analysis": {"estimated_monthly_cost": "$500"}}'
        assert extract_json_from_llm_output(text) == expected

    def test_json_with_extra_text(self):
        text = 'Some text before\n{"architecture": {"compute": "AKS"}}\nand after.'
        expected = '{"architecture": {"compute": "AKS"}}'
        assert extract_json_from_llm_output(text) == expected

    def test_empty_text(self):
        assert extract_json_from_llm_output("") == "{}"

    def test_malformed_no_json(self):
        text = "This is just plain text with no JSON at all."
        assert extract_json_from_llm_output(text) == text


class TestArchitectValidation:
    """Test Architect response schema validation."""

    def test_valid_architect_output(self):
        raw = json.dumps({
            "architecture": {
                "compute": {"recommendation": "AKS", "justification": "Managed K8s", "alternatives": ["App Service"]},
                "storage": {"recommendation": "Blob Storage", "justification": "Cost-effective", "alternatives": []},
                "networking": {"recommendation": "Hub-spoke VNet", "justification": "Security", "alternatives": []},
                "data": {"recommendation": "Azure SQL", "justification": "Managed DB", "alternatives": ["Cosmos DB"]},
            },
            "summary": "A solid architecture."
        })
        result = validate_agent_output(raw, AgentType.ARCHITECT)
        assert "architecture" in result
        assert result["architecture"]["compute"]["recommendation"] == "AKS"
        assert result["summary"] == "A solid architecture."

    def test_partial_architect_output(self):
        """Missing fields should get defaults."""
        raw = json.dumps({"architecture": {"compute": {"recommendation": "AKS"}}})
        result = validate_agent_output(raw, AgentType.ARCHITECT)
        assert result["architecture"]["compute"]["recommendation"] == "AKS"
        assert result["architecture"]["storage"]["recommendation"] == ""
        assert result["summary"] == ""

    def test_empty_architect_output(self):
        result = validate_agent_output("{}", AgentType.ARCHITECT)
        assert result["architecture"]["compute"]["recommendation"] == ""

    def test_invalid_json_fallback(self):
        result = validate_agent_output("not json at all", AgentType.ARCHITECT)
        assert "raw_response" in result
        assert "_error" in result

    def test_architect_with_llm_output(self):
        """Simulate LLM wrapping JSON in markdown."""
        text = 'Let me design that.\n```json\n{"architecture": {"compute": {"recommendation": "AKS"}}}\n```'
        result = validate_agent_output(text, AgentType.ARCHITECT)
        assert result["architecture"]["compute"]["recommendation"] == "AKS"


class TestCostValidation:
    """Test Cost response schema validation."""

    def test_valid_cost_output(self):
        raw = json.dumps({
            "analysis": {
                "estimated_monthly_cost": "$4,200",
                "cost_breakdown": {"compute": "$2,000", "storage": "$500"},
                "cost_optimization_opportunities": [
                    {"area": "Reserved Instances", "potential_savings": "30%", "recommendation": "Buy RIs"}
                ],
                "budget_alert_threshold": "WARN at $4,000",
                "conflicts_with_architect": [
                    {"item": "D-series VMs", "architect_recommends": "D-series", "cost_concern": "Too expensive", "estimated_savings": "$200"}
                ],
            }
        })
        result = validate_agent_output(raw, AgentType.COST)
        assert result["analysis"]["estimated_monthly_cost"] == "$4,200"
        assert len(result["analysis"]["cost_optimization_opportunities"]) == 1
        assert len(result["analysis"]["conflicts_with_architect"]) == 1

    def test_conflicts_extraction(self):
        validated = {
            "analysis": {
                "conflicts_with_architect": [
                    {"item": "VM size", "architect_recommends": "D8", "cost_concern": "Overprovisioned", "estimated_savings": "$300"}
                ]
            }
        }
        conflicts = extract_conflicts_from_validated(validated, AgentType.COST)
        assert len(conflicts) == 1
        assert conflicts[0]["item"] == "VM size"


class TestSecurityValidation:
    """Test Security response schema validation."""

    def test_valid_security_output(self):
        raw = json.dumps({
            "security_assessment": {
                "overall_risk_rating": "MEDIUM",
                "findings": [
                    {"control": "Encryption at rest", "status": "OK", "details": "Encrypted", "risk_if_unaddressed": "Data exposure"}
                ],
                "conflicts_with_architect": [],
            }
        })
        result = validate_agent_output(raw, AgentType.SECURITY)
        assert result["security_assessment"]["overall_risk_rating"] == "MEDIUM"
        assert len(result["security_assessment"]["findings"]) == 1
        assert result["security_assessment"]["findings"][0]["control"] == "Encryption at rest"


class TestComplianceValidation:
    """Test Compliance response schema validation."""

    def test_valid_compliance_output(self):
        raw = json.dumps({
            "compliance_assessment": {
                "target_region": "India",
                "applicable_frameworks": ["DPDP Act 2023"],
                "findings": [
                    {
                        "framework": "DPDP",
                        "constraint_type": "data_residency",
                        "requirement": "Data must stay in India",
                        "status": "POTENTIAL VIOLATION",
                        "details": "GRS replicates outside India",
                        "source_citation": "Section 16",
                        "recommendation": "Use LRS",
                    }
                ],
                "conflicts_with_architect": [],
                "disclaimer": "Not legal advice",
            }
        })
        result = validate_agent_output(raw, AgentType.COMPLIANCE)
        assert result["compliance_assessment"]["target_region"] == "India"
        assert len(result["compliance_assessment"]["findings"]) == 1

    def test_conflicts_extraction(self):
        validated = {
            "compliance_assessment": {
                "conflicts_with_architect": [
                    {"item": "GRS storage", "architect_recommends": "GRS", "compliance_concern": "Data residency", "recommendation": "Use LRS"}
                ]
            }
        }
        conflicts = extract_conflicts_from_validated(validated, AgentType.COMPLIANCE)
        assert len(conflicts) == 1
        assert conflicts[0]["item"] == "GRS storage"


class TestJudgeValidation:
    """Test Judge response schema validation."""

    def test_valid_judge_output(self):
        raw = json.dumps({
            "arbitration": {
                "conflicts_detected": 2,
                "conflict_summaries": [
                    {
                        "dimension": "cost_vs_compliance",
                        "agents_involved": ["Cost", "Compliance"],
                        "issue": "Cost recommends GRS",
                        "resolution": "OVERRULE Cost",
                        "rationale": "GRS violates DPDP",
                        "overruled_agent": "Cost",
                        "resolved_in_favor_of": "Compliance",
                    }
                ],
                "final_verdict": {
                    "approved_architecture": "Use LRS",
                    "plain_language_summary": "We chose LRS for compliance"
                }
            },
            "disclaimer": "This is decision support",
        })
        result = validate_agent_output(raw, AgentType.JUDGE)
        assert result["arbitration"]["conflicts_detected"] == 2
        assert len(result["arbitration"]["conflict_summaries"]) == 1
        assert result["arbitration"]["final_verdict"]["approved_architecture"] == "Use LRS"
        assert result["disclaimer"] == "This is decision support"


class TestArchitectModel:
    """Test Pydantic models directly."""

    def test_architect_response_creation(self):
        response = ArchitectResponse(
            architecture={
                "compute": {"recommendation": "AKS", "justification": "Good", "alternatives": ["App Service"]}
            },
            summary="Test"
        )
        assert response.architecture.compute.recommendation == "AKS"
        assert response.summary == "Test"

    def test_cost_response_defaults(self):
        response = CostResponse()
        assert response.analysis.estimated_monthly_cost == ""
        assert response.analysis.cost_optimization_opportunities == []
        assert response.analysis.conflicts_with_architect == []

    def test_security_response_findings(self):
        response = SecurityResponse(
            security_assessment={
                "overall_risk_rating": "HIGH",
                "findings": [{"control": "Test", "status": "CRITICAL GAP", "details": "Issue", "risk_if_unaddressed": "Bad"}]
            }
        )
        assert response.security_assessment.overall_risk_rating == "HIGH"
        assert response.security_assessment.findings[0].status == "CRITICAL GAP"

    def test_compliance_response_with_frameworks(self):
        response = ComplianceResponse(
            compliance_assessment={
                "target_region": "EU",
                "applicable_frameworks": ["GDPR"],
                "disclaimer": "Disclaimer text"
            }
        )
        assert "GDPR" in response.compliance_assessment.applicable_frameworks
        assert response.compliance_assessment.disclaimer == "Disclaimer text"

    def test_judge_response_with_verdict(self):
        response = JudgeResponse(
            arbitration={
                "conflicts_detected": 1,
                "conflict_summaries": [
                    {"dimension": "test", "agents_involved": ["A", "B"], "issue": "Test", "resolution": "OK", "rationale": "Fine"}
                ],
                "final_verdict": {"approved_architecture": "LRS", "plain_language_summary": "Simple"}
            }
        )
        assert response.arbitration.conflicts_detected == 1
        assert response.arbitration.final_verdict.approved_architecture == "LRS"


class TestAgentTypeMapping:
    """Test that all agent types have registered schemas."""

    def test_all_types_have_schemas(self):
        from src.core.agent_schemas import AGENT_RESPONSE_SCHEMAS
        for agent_type in AgentType:
            assert agent_type in AGENT_RESPONSE_SCHEMAS, f"Missing schema for {agent_type}"

    def test_extract_conflicts_architect_empty(self):
        assert extract_conflicts_from_validated({}, AgentType.ARCHITECT) == []

    def test_extract_conflicts_unknown_type(self):
        assert extract_conflicts_from_validated({}, "unknown") == []
