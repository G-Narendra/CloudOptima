"""NVIDIA NIMs API client - OpenAI-compatible wrapper with retry logic and cost tracking."""

from __future__ import annotations
import json
import logging
import time
from typing import Optional
from dataclasses import dataclass, field
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

from src.config import settings
from src.core.llm_cache import get_cache

logger = logging.getLogger(__name__)

# Cost per 1M tokens for NVIDIA NIMs models (approximate)
# These are estimates; actual costs depend on the specific NIM deployed
MODEL_COST_PER_1M_TOKENS: dict[str, dict[str, float]] = {
    "meta/llama-3.1-70b-instruct": {"input": 0.59, "output": 0.79},
    "meta/llama-3.1-8b-instruct": {"input": 0.10, "output": 0.10},
    "mistralai/mistral-small-4-119b-2603": {"input": 0.75, "output": 1.00},
    "mistralai/mixtral-8x22b-instruct": {"input": 0.90, "output": 0.90},
}
DEFAULT_MODEL_COST = {"input": 0.50, "output": 0.50}


@dataclass
class LLMCallRecord:
    """Record of a single LLM API call for cost tracking."""
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    status: str = "success"


class LLMCostTracker:
    """Tracks LLM API call costs and usage."""

    def __init__(self):
        self.calls: list[LLMCallRecord] = []
        self.total_cost: float = 0.0

    def record_call(self, record: LLMCallRecord):
        self.calls.append(record)
        self.total_cost += record.cost_usd
        logger.info(f"[LLM COST] {record.model}: ${record.cost_usd:.6f} ({record.input_tokens} in / {record.output_tokens} out) in {record.latency_ms:.0f}ms")

    def get_total_cost(self) -> float:
        return self.total_cost

    def get_call_count(self) -> int:
        return len(self.calls)

    def get_report(self) -> dict:
        return {
            "total_calls": len(self.calls),
            "total_cost_usd": round(self.total_cost, 6),
            "by_model": {},
        }


# Global cost tracker
_cost_tracker: Optional[LLMCostTracker] = None


def get_cost_tracker() -> LLMCostTracker:
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = LLMCostTracker()
    return _cost_tracker


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate estimated cost for an LLM call."""
    cost_table = MODEL_COST_PER_1M_TOKENS.get(model, DEFAULT_MODEL_COST)
    input_cost = (input_tokens / 1_000_000) * cost_table["input"]
    output_cost = (output_tokens / 1_000_000) * cost_table["output"]
    return input_cost + output_cost


class NVIDIAClient:
    """Client for NVIDIA NIMs API (OpenAI-compatible)."""

    def __init__(self, model: Optional[str] = None):
        self.base_url = settings.nvidia_base_url
        self.api_key = settings.nvidia_api_key
        self.model = model or settings.nvidia_model
        self.cost_tracker = get_cost_tracker()

        if not self.api_key and not settings.demo_mode:
            logger.warning("NVIDIA_API_KEY not set. Running in demo mode will use mock responses.")
        elif not self.api_key and settings.demo_mode:
            logger.info("NVIDIA_API_KEY not set but DEMO_MODE=true - using mock responses.")

        # Only initialize client if we have an API key
        if self.api_key:
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                http_client=httpx.Client(timeout=60.0),
            )
        else:
            self.client = None

    def chat_completion(
        self,
        messages: list[dict],
        temperature: float = 0.2,  # Lower default for structured outputs
        max_tokens: int = 2048,
    ) -> str:
        """Send a chat completion request to NVIDIA NIMs with caching.

        Checks the response cache before making the API call. On cache hit,
        returns the cached response immediately (zero latency, zero cost).
        On cache miss, calls the API, stores the result, and returns it.

        Falls back to mock responses in demo mode.
        Tracks token usage and cost for observability on live calls.
        """
        # Demo mode: skip cache, return mock
        if settings.demo_mode or not self.client:
            logger.info(f"[DEMO] Returning mock response for model={self.model}")
            return self._mock_response(messages)

        # Check cache before API call (best-effort — never block on cache failure)
        cache = get_cache()
        try:
            cached = cache.get(messages, self.model, temperature)
            if cached is not None:
                logger.info(f"[CACHE HIT] model={self.model} temp={temperature:.1f}")
                return cached
        except Exception as cache_err:
            logger.warning(f"Cache lookup failed (proceeding without cache): {cache_err}")

        logger.info(f"[CACHE MISS] model={self.model} temp={temperature:.1f}")

        start_time = time.monotonic()
        try:
            response = self._make_api_call(messages, temperature, max_tokens)
            latency = (time.monotonic() - start_time) * 1000

            content = response.choices[0].message.content or ""

            # Track token usage and cost
            usage = response.usage
            if usage:
                input_tokens = usage.prompt_tokens or 0
                output_tokens = usage.completion_tokens or 0
                cost = calculate_cost(self.model, input_tokens, output_tokens)

                record = LLMCallRecord(
                    model=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost,
                    latency_ms=latency,
                    status="success",
                )
                self.cost_tracker.record_call(record)

            # Store in cache (best-effort)
            try:
                cache.set(messages, self.model, temperature, content)
            except Exception as cache_err:
                logger.warning(f"Failed to cache response: {cache_err}")

            return content

        except Exception as e:
            latency = (time.monotonic() - start_time) * 1000
            logger.error(f"NVIDIA API call failed after {latency:.0f}ms: {e}")
            # Fall back to mock response if API is unavailable
            logger.warning("Falling back to mock response due to API failure")
            return self._mock_response(messages)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.RemoteProtocolError)),
    )
    def _make_api_call(self, messages: list[dict], temperature: float, max_tokens: int):
        """Make the actual API call with retry logic."""
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def _mock_response(self, messages: list[dict]) -> str:
        """Generate a mock response for demo/testing mode."""
        system_text = str(messages[0].get("content", "")).lower() if messages else ""
        user_text = messages[-1]["content"].lower() if messages else ""

        # Check system prompt for role-specific phrases
        # Use specific multi-word phrases to avoid false positives
        if "solutions architect" in system_text or "architect agent" in system_text:
            return self._mock_architect()
        elif "finops" in system_text or "cost optimization" in system_text:
            return self._mock_cost()
        elif "security engineer" in system_text or "security agent" in system_text:
            return self._mock_security()
        elif "compliance and regulatory" in system_text or "regulatory specialist" in system_text:
            return self._mock_compliance()
        elif "you are the judge" in system_text or "arbitration" in system_text:
            return self._mock_judge()

        # Fallback: check user prompt for agent type keywords
        if "architect" in user_text:
            return self._mock_architect()
        elif "cost" in user_text:
            return self._mock_cost()
        elif "security" in user_text:
            return self._mock_security()
        elif "compliance" in user_text:
            return self._mock_compliance()
        elif "judge" in user_text or "arbitrat" in user_text:
            return self._mock_judge()

        return "I am an AI agent assisting with cloud architecture design. Please provide more details about your requirements."

    def _mock_architect(self) -> str:
        return json.dumps({
            "architecture": {
                "compute": {
                    "recommendation": "Azure Kubernetes Service (AKS) with D-series VMs for general-purpose workloads",
                    "justification": "AKS provides managed Kubernetes orchestration, auto-scaling, and integration with Azure AD for RBAC",
                    "alternatives": ["Azure App Service (simpler, less control)", "Azure Functions (serverless, event-driven)"],
                },
                "storage": {
                    "recommendation": "Azure Blob Storage with hot-tier access tier, geo-redundant storage (GRS)",
                    "justification": "Cost-effective for structured and unstructured data with 11 nines durability",
                    "alternatives": ["Azure Files (SMB shares)", "Azure Disk Storage (high-performance VHDs)"],
                },
                "networking": {
                    "recommendation": "Azure Virtual Network with hub-spoke topology, Azure Firewall, and Application Gateway",
                    "justification": "Hub-spoke provides centralized connectivity and security policy enforcement",
                    "alternatives": ["Virtual WAN (large-scale)", "Point-to-site VPN (small deployments)"],
                },
                "data": {
                    "recommendation": "Azure SQL Database with Business Critical tier and active geo-replication",
                    "justification": "Fully managed relational database with built-in HA, automated backups, and 99.995% SLA",
                    "alternatives": ["Azure Cosmos DB (NoSQL, global distribution)", "Azure Database for PostgreSQL (open-source)"],
                },
            },
            "summary": "A balanced architecture using AKS for compute, Blob Storage for data, hub-spoke networking, and Azure SQL for the data tier.",
        })

    def _mock_cost(self) -> str:
        return json.dumps({
            "analysis": {
                "estimated_monthly_cost": "$4,200 - $5,800",
                "cost_breakdown": {
                    "compute_aks": "$1,800 - $2,500",
                    "storage_blob": "$400 - $600",
                    "networking": "$600 - $900",
                    "data_azure_sql": "$1,400 - $1,800",
                },
                "cost_optimization_opportunities": [
                    {
                        "area": "Reserved Instances for AKS node pool",
                        "potential_savings": "30-40%",
                        "recommendation": "Purchase 1-year reserved instances for baseline node count",
                    },
                    {
                        "area": "Storage tier optimization",
                        "potential_savings": "15-25%",
                        "recommendation": "Use cool tier for data accessed less than once per month; archive tier for backups",
                    },
                    {
                        "area": "Azure SQL serverless for dev/test",
                        "potential_savings": "40-60%",
                        "recommendation": "Use serverless compute tier in non-production environments",
                    },
                ],
                "budget_alert_threshold": "WARN at $4,000/mo, CRITICAL at $6,000/mo",
                "conflicts_with_architect": [
                    {
                        "item": "AKS D-series VMs",
                        "architect_recommends": "D-series VMs for general-purpose",
                        "cost_concern": "D-series may be overprovisioned; consider B-series burstable VMs for dev/staging workloads",
                        "estimated_savings": "$200-400/mo",
                    },
                    {
                        "item": "Azure SQL Business Critical",
                        "architect_recommends": "Business Critical tier",
                        "cost_concern": "General Purpose tier may suffice for most workloads with 99.99% SLA vs 99.995%",
                        "estimated_savings": "$500-800/mo",
                    },
                ],
            },
        })

    def _mock_security(self) -> str:
        return json.dumps({
            "security_assessment": {
                "overall_risk_rating": "MEDIUM",
                "findings": [
                    {
                        "control": "Encryption at rest",
                        "status": "OK with recommendation",
                        "details": "Azure Storage and SQL both support encryption at rest. Recommend customer-managed keys (CMK) for production.",
                        "risk_if_unaddressed": "Data at rest is encrypted with Microsoft-managed keys - meets baseline compliance but not BYOK requirements",
                    },
                    {
                        "control": "Network security",
                        "status": "CONFIGURATION NEEDED",
                        "details": "Hub-spoke topology recommended but requires NSG rules, Azure Firewall policies, and private endpoints for data services.",
                        "risk_if_unaddressed": "Without proper NSG rules and private endpoints, data exfiltration via public endpoints is possible",
                    },
                    {
                        "control": "Identity and access management (IAM)",
                        "status": "RECOMMENDATION",
                        "details": "AKS integrated with Azure AD RBAC is good. Recommend managed identities for service-to-service auth, avoid connection strings.",
                        "risk_if_unaddressed": "Connection strings in configuration are a common credential leakage vector",
                    },
                    {
                        "control": "Data protection",
                        "status": "CRITICAL GAP",
                        "details": "No backup and disaster recovery plan specified in the architecture. Need Azure Backup for VMs, point-in-time restore for SQL, and geo-replication.",
                        "risk_if_unaddressed": "Data loss in case of regional failure - no RPO/RTO defined",
                    },
                ],
                "conflicts_with_architect": [
                    {
                        "item": "Geo-redundant storage (GRS)",
                        "architect_recommends": "GRS for all storage",
                        "security_concern": "GRS replicates to paired region. If the paired region is in a different jurisdiction, this may cause data sovereignty issues.",
                        "recommendation": "Use RA-GRS or consider region-specific redundancy requirements",
                    },
                ],
            },
        })

    def _mock_compliance(self) -> str:
        return json.dumps({
            "compliance_assessment": {
                "target_region": "India (assumed based on requirement)",
                "applicable_frameworks": ["India DPDP Act 2023", "EU GDPR (if EU data subjects involved)"],
                "findings": [
                    {
                        "framework": "India DPDP Act 2023",
                        "constraint_type": "data_residency",
                        "requirement": "Personal data must be stored within India. Critical personal data requires explicit consent for cross-border transfer.",
                        "status": "POTENTIAL VIOLATION",
                        "details": "GRS storage replicates data to a paired region outside India by default. This violates DPDP data residency requirements.",
                        "source_citation": "DPDP Act 2023, Section 16 - Data localization requirements for personal data",
                        "recommendation": "Use Locally Redundant Storage (LRS) with region-specific backup, or Zone-Redundant Storage (ZRS) within India regions only",
                    },
                    {
                        "framework": "India DPDP Act 2023",
                        "constraint_type": "consent",
                        "requirement": "Explicit consent must be obtained before processing any personal data. Consent withdrawal must be as easy as giving consent.",
                        "status": "NEEDS DESIGN CONSIDERATION",
                        "details": "The architecture must include a consent management mechanism (e.g., a consent portal, preference center) that logs consent, withdrawal, and data processing purposes.",
                        "source_citation": "DPDP Act 2023, Section 7 - Consent requirements",
                        "recommendation": "Include Azure AD B2C or custom consent management in the architecture",
                    },
                    {
                        "framework": "India DPDP Act 2023",
                        "constraint_type": "audit",
                        "requirement": "Data fiduciaries must maintain records of data processing activities and undergo annual audit by an independent auditor.",
                        "status": "NOT COVERED IN ARCHITECTURE",
                        "details": "No audit logging or data processing records infrastructure has been specified.",
                        "source_citation": "DPDP Act 2023, Section 18 - Audit requirements",
                        "recommendation": "Include Azure Monitor, Log Analytics, and audit log storage in the architecture",
                    },
                ],
                "conflicts_with_architect": [
                    {
                        "item": "Geo-redundant storage (GRS)",
                        "architect_recommends": "GRS for durability",
                        "compliance_concern": "GRS replicates data outside India, violating DPDP data residency requirements",
                        "recommendation": "Switch to LRS or ZRS with India-region backup strategy",
                    },
                    {
                        "item": "Cost agent's reserved instances recommendation",
                        "architect_recommends": "Reserved instances may save cost",
                        "compliance_concern": "Reserved instances lock to a specific region/zone. If data residency requirements change, you cannot easily migrate.",
                        "recommendation": "Use pay-as-you-go or short-term reservations (1 year max) to maintain flexibility",
                    },
                ],
                "disclaimer": "This output is decision support for a design exercise, not legal advice, and has not been reviewed by qualified legal counsel. Compliance requirements vary by specific use case, data types, and jurisdictions involved.",
            },
        })

    def _mock_judge(self) -> str:
        return json.dumps({
            "arbitration": {
                "conflicts_detected": 3,
                "conflict_summaries": [
                    {
                        "dimension": "cost_vs_compliance",
                        "agents_involved": ["Cost", "Compliance"],
                        "issue": "Cost agent recommends GRS storage ($400-600/mo). Compliance agent identifies GRS violates India DPDP data residency.",
                        "resolution": "OVERRULE Cost - Data residency is a legal requirement, not optional.",
                        "rationale": "GRS replicates data to a paired region (potentially outside India), violating DPDP Act Section 16. The cost savings from GRS vs LRS/ZRS (~$100/mo) is not worth regulatory non-compliance. Recommendation: Use LRS or ZRS within India regions.",
                        "overruled_agent": "Cost",
                        "resolved_in_favor_of": "Compliance",
                    },
                    {
                        "dimension": "cost_vs_security",
                        "agents_involved": ["Cost", "Security"],
                        "issue": "Cost agent recommends B-series burstable VMs for dev/staging. Security agent requires D-series for consistent performance of security tooling.",
                        "resolution": "PARTIAL OVERRIDE - Use B-series for dev/staging, D-series for production.",
                        "rationale": "Security agent's concern about consistent performance for security tooling applies to production only. For dev/staging environments, B-series burstable VMs with auto-shutdown provide adequate security posture at significantly lower cost.",
                        "overruled_agent": "Cost (partial)",
                        "resolved_in_favor_of": "Hybrid - both agents partially satisfied",
                    },
                    {
                        "dimension": "architect_vs_compliance",
                        "agents_involved": ["Architect", "Compliance"],
                        "issue": "Architect recommends Azure SQL Business Critical. Compliance requires audit logging infrastructure not in scope.",
                        "resolution": "SUSTAIN Architecture with additions.",
                        "rationale": "Azure SQL Business Critical provides the high availability and security controls needed. However, the architecture must be extended to include Azure Monitor, Log Analytics, and a consent management system to meet DPDP audit and consent requirements per Sections 7 and 18.",
                        "overruled_agent": "None (both partially correct)",
                        "resolved_in_favor_of": "Architect with Compliance additions",
                    },
                ],
                "final_verdict": {
                    "approved_architecture": "Use LRS/ZRS storage within India region (overriding GRS for compliance). Use D-series AKS for production, B-series for dev/staging. Keep Azure SQL Business Critical. Add: audit logging (Azure Monitor + Log Analytics), consent management, and backup/DR plan.",
                    "plain_language_summary": "The cheapest storage option had to be rejected because Indian law requires patient data to stay in India. The backup storage recommended by the architect stores data outside India - so we're switching to a storage option that keeps data within Indian borders. The security team's request for powerful servers was only needed for the live environment, not test environments, so we save money there. The overall design is approved with additions for logging and consent systems to meet legal requirements.",
                },
            },
            "disclaimer": "This arbitration is based on structured evaluation of agent inputs. Every conflict has been logged with traceable reasoning. Final deployment requires human approval before any Infrastructure-as-Code is applied to a live subscription.",
        })
