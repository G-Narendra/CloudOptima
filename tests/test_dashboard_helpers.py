"""Tests for dashboard helper functions (assemble_prompt, _get_summary)."""

import json
import sys
import os

# We need to test the helper functions in isolation
# The full dashboard module requires streamlit which isn't available in all test envs
# So we test the pure functions extracted from dashboard.py

# Import the assemble_prompt function by simulating the module
from src.core.sanitize import sanitize_text, detect_suspicious_input


class TestSanitize:
    """Test input sanitization functions."""

    def test_sanitize_text_strips_whitespace(self):
        assert sanitize_text("  hello  ") == "hello"

    def test_sanitize_text_removes_null_bytes(self):
        assert sanitize_text("hello\x00world") == "helloworld"

    def test_sanitize_text_limits_length(self):
        long_text = "a" * 20000
        result = sanitize_text(long_text, max_length=100)
        assert len(result) == 100

    def test_sanitize_text_handles_none(self):
        assert sanitize_text(None) == ""  # type: ignore

    def test_sanitize_text_handles_non_string(self):
        assert sanitize_text(123) == "123"  # type: ignore

    def test_detect_suspicious_input_script_tag(self):
        assert detect_suspicious_input("<script>alert('xss')</script>") is True

    def test_detect_suspicious_input_javascript(self):
        assert detect_suspicious_input("javascript:void(0)") is True

    def test_detect_suspicious_input_onerror(self):
        assert detect_suspicious_input("onerror=alert") is True

    def test_detect_suspicious_input_safe(self):
        assert detect_suspicious_input("Hello, this is a normal prompt") is False

    def test_detect_suspicious_input_empty(self):
        assert detect_suspicious_input("") is False

    def test_detect_suspicious_input_none(self):
        assert detect_suspicious_input(None) is False  # type: ignore

    def test_sanitize_for_display_escapes_html(self):
        from src.core.sanitize import sanitize_for_display
        result = sanitize_for_display("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;" in result

    def test_safe_truncate_short_text(self):
        from src.core.sanitize import safe_truncate
        assert safe_truncate("Hello world", 100) == "Hello world"

    def test_safe_truncate_long_text(self):
        from src.core.sanitize import safe_truncate
        text = "Hello " * 50
        result = safe_truncate(text, 50)
        assert len(result) <= 53  # 50 + "..."
        assert result.endswith("...")

    def test_validate_prompt_input_with_suspicious(self):
        from src.core.sanitize import validate_prompt_input
        fields = {
            "project_description": "<script>alert('xss')</script>",
            "workload_type": "normal workload",
            "budget": "$500",
        }
        warnings = validate_prompt_input(fields)
        assert "project_description" in warnings
        assert "workload_type" not in warnings


class TestAssemblePrompt:
    """Test prompt assembly logic (mirrors dashboard.assemble_prompt)."""

    def _assemble_prompt(
        self,
        project_description: str,
        workload_type: str = "",
        region: str = "",
        compliance: list[str] | None = None,
        scale: str = "",
        budget: str = "",
        key_services: str = "",
        additional_context: str = "",
    ) -> str:
        """Replicate assemble_prompt from dashboard.py for isolated testing."""
        parts = [f"I need infrastructure for: {project_description}"]
        if workload_type:
            parts.append(f"\nWorkload type: {workload_type}")
        if region:
            parts.append(f"\nTarget deployment region: {region}")
        if compliance:
            parts.append(f"\nCompliance requirements: {', '.join(compliance)}")
        if scale:
            scale_options = {
                "small": "Small — dev/test, < 1K users",
                "medium": "Medium — production, 1K–50K users",
                "large": "Large — production, 50K–500K users",
                "enterprise": "Enterprise — > 500K users, HA required",
            }
            parts.append(f"\nExpected scale: {scale_options.get(scale, scale)}")
        if budget:
            parts.append(f"\nMonthly budget: {budget}")
        if key_services:
            parts.append(f"\nPreferred services: {key_services}")
        if additional_context:
            parts.append(f"\nAdditional context: {additional_context}")
        return "\n".join(parts)

    def test_basic_prompt(self):
        prompt = self._assemble_prompt("A simple web app")
        assert "I need infrastructure for: A simple web app" in prompt

    def test_full_prompt(self):
        prompt = self._assemble_prompt(
            project_description="Patient data pipeline",
            workload_type="Real-time ETL",
            region="india",
            compliance=["HIPAA", "DPDP"],
            scale="medium",
            budget="$5,000",
            key_services="AKS, Azure SQL",
            additional_context="Multi-region DR needed",
        )
        assert "Patient data pipeline" in prompt
        assert "Real-time ETL" in prompt
        assert "india" in prompt
        assert "HIPAA" in prompt
        assert "Medium" in prompt
        assert "$5,000" in prompt
        assert "AKS" in prompt
        assert "Multi-region" in prompt

    def test_prompt_with_partial_input(self):
        prompt = self._assemble_prompt(
            project_description="Test",
            region="eu",
            compliance=["GDPR"],
        )
        assert "GDPR" in prompt
        assert "eu" in prompt
        assert "Expected scale" not in prompt
        assert "Monthly budget" not in prompt

    def test_empty_compliance(self):
        prompt = self._assemble_prompt("Test")
        assert "Compliance requirements" not in prompt


class TestGetSummary:
    """Test _get_summary logic from dashboard.py."""

    def _format_raw_output(self, output: dict) -> str | None:
        """Format raw/error output - mirrors dashboard._format_agent_output_human_readable."""
        if not output:
            return "<em>No output available</em>"
        if "raw" in output:
            raw_text = output["raw"]
            try:
                import re
                match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if match:
                    parsed = json.loads(match.group())
                    return self._get_summary("architect", parsed)  # Try to extract
            except (json.JSONDecodeError, AttributeError):
                pass
            return f"<div style='color: #aaa; font-size: 0.85rem;'><strong>Analysis output:</strong><br><code>{raw_text[:400]}</code></div>"
        if "_error" in output or "error" in output:
            err = output.get("_error", output.get("error", "Unknown error"))
            return f"<div style='color: #EF4444;'>⚠️ {err}</div>"
        return None

    def _get_summary(self, agent_type: str, output: dict) -> str:
        """Replicate _get_summary from dashboard.py for isolated testing."""
        formatted = self._format_raw_output(output)
        if formatted is not None:
            return formatted

        if agent_type == "architect" and "architecture" in output:
            arch = output["architecture"]
            parts = []
            for key in ["compute", "storage", "networking", "data"]:
                rec = arch.get(key, {}).get("recommendation", "")[:120]
                if rec:
                    parts.append(f"<strong>{key.title()}:</strong> {rec}")
            summary = output.get("summary", "")
            if summary:
                parts.append(f"<br><em>— {summary[:200]}</em>")
            return "<br>".join(parts) if parts else json.dumps(output, indent=2)[:300]
        elif agent_type == "cost" and "analysis" in output:
            a = output["analysis"]
            cost = a.get("estimated_monthly_cost", "N/A")
            breakdown = a.get("cost_breakdown", {})
            opts = a.get("cost_optimization_opportunities", [])
            details = "<br>".join(
                f"<span style='color: #888;'>• {k}:</span> {v}"
                for k, v in list(breakdown.items())[:4]
            )
            savings = "<br>".join(
                f"• {o.get('area', '')}: save {o.get('potential_savings', '')}"
                for o in opts[:3]
            )
            return f"<strong>Estimated monthly cost:</strong> <span style='color: #F59E0B;'>{cost}</span><br>{details}<br><br><strong>Savings opportunities:</strong><br>{savings}"
        elif agent_type == "security" and "security_assessment" in output:
            s = output["security_assessment"]
            risk = s.get("overall_risk_rating", "N/A")
            findings = s.get("findings", [])
            items = []
            for f in findings[:5]:
                status = f.get("status", "")
                icon = {"OK": "✅", "RECOMMENDATION": "ℹ️", "CONFIGURATION NEEDED": "⚠️", "CRITICAL GAP": "🚫"}.get(status, "•")
                items.append(f"{icon} <strong>{f.get('control', '')}</strong>: {f.get('details', '')[:100]}")
            findings_text = "<br>".join(items)
            return f"<strong>Risk rating:</strong> <span style='color: #EF4444;'>{risk}</span><br><br>{findings_text}"
        elif agent_type == "compliance" and "compliance_assessment" in output:
            c = output["compliance_assessment"]
            fw = ", ".join(c.get("applicable_frameworks", []))
            findings = c.get("findings", [])
            items = []
            for f in findings[:4]:
                status = f.get("status", "")
                icon = {"OK": "✅", "POTENTIAL VIOLATION": "🚫", "NEEDS DESIGN CONSIDERATION": "⚠️", "NOT COVERED IN ARCHITECTURE": "📋"}.get(status, "•")
                items.append(f"{icon} <strong>{f.get('framework', '')}</strong>: {f.get('requirement', '')[:120]}")
            findings_text = "<br>".join(items)
            return f"<strong>Applicable frameworks:</strong> {fw}<br><br>{findings_text}"
        return json.dumps(output, indent=2)[:300]

    def test_architect_summary(self):
        output = {
            "architecture": {
                "compute": {"recommendation": "AKS cluster"},
                "storage": {"recommendation": "Blob Storage"},
                "networking": {"recommendation": "VNet"},
                "data": {"recommendation": "Azure SQL"},
            }
        }
        summary = self._get_summary("architect", output)
        assert "compute" in summary.lower() or "Compute" in summary
        assert "AKS" in summary

    def test_cost_summary(self):
        output = {
            "analysis": {
                "estimated_monthly_cost": "$4,200",
                "cost_optimization_opportunities": [
                    {"area": "Reserved Instances", "potential_savings": "30%"},
                    {"area": "Storage tier", "potential_savings": "15%"},
                ],
            }
        }
        summary = self._get_summary("cost", output)
        assert "$4,200" in summary
        assert "30%" in summary

    def test_security_summary(self):
        output = {
            "security_assessment": {
                "overall_risk_rating": "HIGH",
                "findings": [
                    {"control": "Encryption", "status": "CRITICAL GAP"},
                    {"control": "IAM", "status": "OK"},
                ],
            }
        }
        summary = self._get_summary("security", output)
        assert "HIGH" in summary
        assert "Encryption" in summary

    def test_compliance_summary(self):
        output = {
            "compliance_assessment": {
                "applicable_frameworks": ["GDPR", "DPDP"],
            }
        }
        summary = self._get_summary("compliance", output)
        assert "GDPR" in summary
        assert "DPDP" in summary

    def test_unknown_agent_type(self):
        output = {"raw": "some data"}
        summary = self._get_summary("unknown", output)
        assert summary is not None
        assert "some data" in summary

    def test_architect_partial_data(self):
        output = {"architecture": {"compute": {"recommendation": "AKS"}}}
        summary = self._get_summary("architect", output)
        assert "AKS" in summary
