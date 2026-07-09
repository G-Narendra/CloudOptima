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

    def _get_summary(self, agent_type: str, output: dict) -> str:
        """Replicate _get_summary from dashboard.py for isolated testing."""
        if not output:
            return "<code>No output available</code>"

        if "_error" in output or "error" in output:
            err = output.get("_error", output.get("error", "Unknown error"))
            return f"<code style='color: #EF4444;'>Error: {err}</code>"

        if "raw" in output:
            text = output["raw"]
            clean = text.replace('```json', '').replace('```', '').strip()[:1000]
            return f"<pre style='font-size:0.75rem;color:#ccc;max-height:200px;overflow-y:auto;'>{clean}</pre>"

        # ── Architect ────────────────────────────────────────────────────
        if agent_type == "architect":
            arch = output.get("architecture", {})
            sections = []
            for key in ["compute", "storage", "networking", "data"]:
                section = arch.get(key, {})
                rec = section.get("recommendation", "")
                justification = section.get("justification", "")
                alts = section.get("alternatives", [])
                if rec:
                    parts = f"<strong style='color:#a29bfe;'>{key.title()}</strong>"
                    parts += f"<div style='margin:0.25rem 0 0 0;'>{rec}</div>"
                    if justification:
                        parts += f"<div style='color:#999;font-size:0.8rem;margin:0.2rem 0;'>→ {justification[:200]}</div>"
                    if alts:
                        alt_text = "<span style='color:#666;font-size:0.75rem;'>Alternatives: </span>"
                        alt_text += "<span style='color:#888;font-size:0.75rem;'>" + " | ".join(alts) + "</span>"
                        parts += f"<div style='margin:0.15rem 0 0.4rem 0;'>{alt_text}</div>"
                    sections.append(parts)
            summary = arch.get("summary", "")
            if summary:
                sections.append(f"<em style='color:#aaa;font-size:0.85rem;'>— {summary}</em>")
            if sections:
                return "<div style='line-height:1.6;'>" + "<hr style='border-color:rgba(255,255,255,0.05);margin:0.3rem 0;'>".join(sections) + "</div>"
            return f"<pre style='font-size:0.75rem;color:#ccc;max-height:200px;overflow-y:auto;'>{json.dumps(output, indent=2)[:1500]}</pre>"

        # ── Cost Analyst ─────────────────────────────────────────────────
        if agent_type == "cost":
            analysis = output.get("analysis", {})
            parts = []

            cost = analysis.get("estimated_monthly_cost", "")
            if cost:
                parts.append(
                    f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                    f"<span style='color:#F59E0B;font-weight:600;'>Estimated Monthly Cost</span>"
                    f"<span style='font-size:1.2rem;font-weight:700;color:#FBBF24;'>{cost}</span>"
                    f"</div>"
                )

            breakdown = analysis.get("cost_breakdown", {})
            if breakdown:
                items = "".join(
                    f"<div style='display:flex;justify-content:space-between;font-size:0.8rem;"
                    f"padding:0.15rem 0;border-bottom:1px solid rgba(255,255,255,0.04);'>"
                    f"<span style='color:#aaa;'>{k.replace('_', ' ').title()}</span>"
                    f"<span style='color:#ddd;'>{v}</span></div>"
                    for k, v in breakdown.items()
                )
                parts.append(
                    f"<div style='margin:0.5rem 0;padding:0.4rem;background:rgba(255,255,255,0.03);"
                    f"border-radius:6px;'>"
                    f"<div style='color:#999;font-size:0.75rem;text-transform:uppercase;"
                    f"letter-spacing:1px;margin-bottom:0.3rem;'>Cost Breakdown</div>{items}</div>"
                )

            optimizations = analysis.get("cost_optimization_opportunities", [])
            if optimizations:
                opt_items = "".join(
                    f"<div style='display:flex;justify-content:space-between;align-items:center;"
                    f"padding:0.3rem 0;border-bottom:1px solid rgba(255,255,255,0.04);'>"
                    f"<div style='flex:1;'>"
                    f"<div style='color:#F59E0B;font-size:0.8rem;'>{o['area']}</div>"
                    f"<div style='color:#999;font-size:0.75rem;'>{o.get('recommendation', '')[:120]}</div>"
                    f"</div>"
                    f"<span style='color:#10B981;font-weight:600;font-size:0.9rem;'>{o.get('potential_savings', '')}</span>"
                    f"</div>"
                    for o in optimizations
                )
                parts.append(
                    f"<div style='margin:0.5rem 0;'>"
                    f"<div style='color:#999;font-size:0.75rem;text-transform:uppercase;"
                    f"letter-spacing:1px;margin-bottom:0.3rem;'>Savings Opportunities</div>{opt_items}</div>"
                )

            threshold = analysis.get("budget_alert_threshold", "")
            if threshold:
                parts.append(
                    f"<div style='color:#888;font-size:0.75rem;border-top:1px solid "
                    f"rgba(255,255,255,0.05);padding-top:0.3rem;'>{threshold}</div>"
                )

            if parts:
                return "<div style='line-height:1.5;'>" + "".join(parts) + "</div>"
            return f"<pre style='font-size:0.75rem;color:#ccc;max-height:200px;overflow-y:auto;'>{json.dumps(output, indent=2)[:1500]}</pre>"

        # ── Security Engineer ─────────────────────────────────────────────
        if agent_type == "security":
            assessment = output.get("security_assessment", {})
            parts = []

            risk = assessment.get("overall_risk_rating", "MEDIUM")
            risk_colors = {"LOW": "#10B981", "MEDIUM": "#F59E0B", "HIGH": "#EF4444", "CRITICAL": "#DC2626"}
            color = risk_colors.get(risk.upper(), "#F59E0B")
            parts.append(
                f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                f"<span style='color:#EF4444;font-weight:600;'>Overall Risk Rating</span>"
                f"<span style='color:{color};font-weight:700;font-size:1.1rem;'>{risk.upper()}</span>"
                f"</div>"
            )

            findings = assessment.get("findings", [])
            if findings:
                def _status_color(status):
                    if status.startswith("OK"):
                        return "#10B981"
                    if "NEED" in status or "RECOMMEND" in status.upper():
                        return "#F59E0B"
                    return "#EF4444"

                find_items = "".join(
                    f"<div style='padding:0.4rem;margin:0.3rem 0;background:rgba(255,255,255,0.03);"
                    f"border-radius:6px;border-left:3px solid {_status_color(f['status'])};'>"
                    f"<div style='display:flex;justify-content:space-between;'>"
                    f"<span style='font-weight:500;font-size:0.85rem;color:#ddd;'>{f['control']}</span>"
                    f"<span style='font-size:0.7rem;color:#888;'>{f['status']}</span>"
                    f"</div>"
                    f"<div style='color:#aaa;font-size:0.8rem;margin-top:0.2rem;'>{f.get('details', '')[:200]}</div>"
                    f"<div style='color:#666;font-size:0.75rem;margin-top:0.15rem;font-style:italic;'>"
                    f"Risk: {f.get('risk_if_unaddressed', '')[:150]}</div>"
                    f"</div>"
                    for f in findings
                )
                parts.append(
                    f"<div style='margin:0.5rem 0;'>"
                    f"<div style='color:#999;font-size:0.75rem;text-transform:uppercase;"
                    f"letter-spacing:1px;margin-bottom:0.3rem;'>Findings ({len(findings)})</div>{find_items}</div>"
                )

            if parts:
                return "<div style='line-height:1.5;'>" + "".join(parts) + "</div>"
            return f"<pre style='font-size:0.75rem;color:#ccc;max-height:200px;overflow-y:auto;'>{json.dumps(output, indent=2)[:1500]}</pre>"

        # ── Compliance Officer ────────────────────────────────────────────
        if agent_type == "compliance":
            assessment = output.get("compliance_assessment", {})
            parts = []

            frameworks = assessment.get("applicable_frameworks", [])
            if frameworks:
                badge_html = "".join(
                    f"<span style='display:inline-block;padding:0.15rem 0.5rem;margin:0.15rem;"
                    f"background:rgba(59,130,246,0.15);color:#93C5FD;border-radius:4px;"
                    f"font-size:0.75rem;'>{f}</span>"
                    for f in frameworks
                )
                parts.append(
                    f"<div style='margin:0 0 0.5rem 0;'>"
                    f"<div style='color:#3B82F6;font-weight:600;margin-bottom:0.2rem;'>"
                    f"Applicable Frameworks</div>{badge_html}</div>"
                )

            findings = assessment.get("findings", [])
            if findings:
                status_colors = {
                    "POTENTIAL VIOLATION": "#EF4444",
                    "NEEDS DESIGN CONSIDERATION": "#F59E0B",
                    "NOT COVERED": "#F59E0B",
                    "OK": "#10B981",
                }
                find_items = "".join(
                    f"<div style='padding:0.4rem;margin:0.3rem 0;background:rgba(255,255,255,0.03);"
                    f"border-radius:6px;border-left:3px solid "
                    f"{status_colors.get(f['status'], '#888')};'>"
                    f"<div style='display:flex;justify-content:space-between;'>"
                    f"<span style='font-weight:500;font-size:0.85rem;color:#ddd;'>{f.get('constraint_type', '')} — {f['framework']}</span>"
                    f"<span style='font-size:0.7rem;color:{status_colors.get(f['status'], '#888')};'>{f['status']}</span>"
                    f"</div>"
                    f"<div style='color:#aaa;font-size:0.8rem;margin-top:0.2rem;'>{f.get('details', '')[:200]}</div>"
                    f"<div style='display:flex;justify-content:space-between;margin-top:0.15rem;'>"
                    f"<span style='color:#3B82F6;font-size:0.75rem;'>{f.get('source_citation', '')[:120]}</span>"
                    f"</div>"
                    f"<div style='color:#93C5FD;font-size:0.78rem;margin-top:0.15rem;'>"
                    f"💡 {f.get('recommendation', '')[:200]}</div>"
                    f"</div>"
                    for f in findings
                )
                parts.append(
                    f"<div style='margin:0.5rem 0;'>"
                    f"<div style='color:#999;font-size:0.75rem;text-transform:uppercase;"
                    f"letter-spacing:1px;margin-bottom:0.3rem;'>Findings ({len(findings)})</div>{find_items}</div>"
                )

            if parts:
                return "<div style='line-height:1.5;'>" + "".join(parts) + "</div>"
            return f"<pre style='font-size:0.75rem;color:#ccc;max-height:200px;overflow-y:auto;'>{json.dumps(output, indent=2)[:1500]}</pre>"

        # Fallback: show as JSON
        try:
            formatted = json.dumps(output, indent=2, default=str)[:1500]
            return f"<pre style='font-size:0.75rem;color:#ccc;max-height:200px;overflow-y:auto;'>{formatted}</pre>"
        except Exception:
            return str(output)[:1500]

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
