"""Demo-mode client - always returns mock responses for instant results."""

from __future__ import annotations
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class NVIDIAClient:
    """Mock client that always returns instant demo responses."""

    def __init__(self, model: Optional[str] = None):
        self.model = model or "mock-model"
        logger.info(f"[MOCK] NVIDIAClient initialized (model={self.model})")

    def chat_completion(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        """Return mock response instantly — no API calls."""
        return self._mock_response(messages)

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
