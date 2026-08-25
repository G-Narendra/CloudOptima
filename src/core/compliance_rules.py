"""Structured compliance rules knowledge base.

Each rule is traceable to a specific regulation and section. This is the
canonical source of truth for the Compliance Agent's regulatory claims.
"""

from __future__ import annotations
import logging

from src.core.models import ComplianceRule

logger = logging.getLogger(__name__)

# In-memory compliance rules database
# In production, this would be loaded from a database or versioned file
_COMPLIANCE_RULES: dict[str, list[ComplianceRule]] = {}


# India - DPDP Act 2023
_INDIA_DPDP_RULES = [
    ComplianceRule(
        id="IN-DPDP-001",
        region="india",
        governing_framework="India DPDP Act 2023",
        constraint_type="residency",
        constraint_text="Personal data must be stored within India. Critical personal data requires explicit consent for cross-border transfer.",
        source_citation="DPDP Act 2023, Section 16 - Data localization requirements",
        applies_to_services=["Azure Blob Storage", "Azure SQL Database", "Azure Cosmos DB",
                             "Azure Files", "Azure NetApp Files", "Azure Disk Storage"],
    ),
    ComplianceRule(
        id="IN-DPDP-002",
        region="india",
        governing_framework="India DPDP Act 2023",
        constraint_type="consent",
        constraint_text="Explicit consent must be obtained before processing any personal data. Consent withdrawal must be as easy as giving consent. Data processing purposes must be specified at time of consent.",
        source_citation="DPDP Act 2023, Section 7 - Consent requirements",
        applies_to_services=["*"],
    ),
    ComplianceRule(
        id="IN-DPDP-003",
        region="india",
        governing_framework="India DPDP Act 2023",
        constraint_type="audit",
        constraint_text="Data fiduciaries must maintain records of data processing activities and undergo annual audit by an independent auditor.",
        source_citation="DPDP Act 2023, Section 18 - Audit requirements",
        applies_to_services=["*"],
    ),
    ComplianceRule(
        id="IN-DPDP-004",
        region="india",
        governing_framework="India DPDP Act 2023",
        constraint_type="breach_notification",
        constraint_text="Data breaches must be reported to the Data Protection Board and affected data principals within a specified timeframe.",
        source_citation="DPDP Act 2023, Section 25 - Breach notification",
        applies_to_services=["*"],
    ),
    ComplianceRule(
        id="IN-DPDP-005",
        region="india",
        governing_framework="India DPDP Act 2023",
        constraint_type="encryption",
        constraint_text="Data fiduciaries must implement appropriate technical safeguards to protect personal data, including encryption.",
        source_citation="DPDP Act 2023, Section 22 - Security safeguards",
        applies_to_services=["*"],
    ),
]

# EU - GDPR
_EU_GDPR_RULES = [
    ComplianceRule(
        id="EU-GDPR-001",
        region="eu",
        governing_framework="EU GDPR",
        constraint_type="residency",
        constraint_text="Personal data may be transferred outside the EU only if adequate safeguards are in place (Standard Contractual Clauses, Binding Corporate Rules, or adequacy decision).",
        source_citation="GDPR Articles 44-49 - International transfers",
        applies_to_services=["Azure Blob Storage", "Azure SQL Database", "Azure Cosmos DB",
                             "Azure Files", "Azure NetApp Files", "Azure Disk Storage"],
    ),
    ComplianceRule(
        id="EU-GDPR-002",
        region="eu",
        governing_framework="EU GDPR",
        constraint_type="consent",
        constraint_text="Consent must be freely given, specific, informed, and unambiguous. Data subjects have the right to withdraw consent at any time.",
        source_citation="GDPR Article 4(11), Article 7 - Conditions for consent",
        applies_to_services=["*"],
    ),
    ComplianceRule(
        id="EU-GDPR-003",
        region="eu",
        governing_framework="EU GDPR",
        constraint_type="encryption",
        constraint_text="Appropriate technical measures, including encryption and pseudonymization, must be implemented to protect personal data.",
        source_citation="GDPR Article 32 - Security of processing",
        applies_to_services=["*"],
    ),
    ComplianceRule(
        id="EU-GDPR-004",
        region="eu",
        governing_framework="EU GDPR",
        constraint_type="breach_notification",
        constraint_text="Personal data breach must be reported to supervisory authority within 72 hours of becoming aware of the breach.",
        source_citation="GDPR Article 33 - Notification of a personal data breach",
        applies_to_services=["*"],
    ),
    ComplianceRule(
        id="EU-GDPR-005",
        region="eu",
        governing_framework="EU GDPR",
        constraint_type="audit",
        constraint_text="Data controllers must maintain records of processing activities and demonstrate compliance upon request.",
        source_citation="GDPR Article 30 - Records of processing activities",
        applies_to_services=["*"],
    ),
]

# US - HIPAA
_US_HIPAA_RULES = [
    ComplianceRule(
        id="US-HIPAA-001",
        region="us",
        governing_framework="US HIPAA",
        constraint_type="encryption",
        constraint_text="Implement encryption and decryption controls for electronic protected health information (ePHI) at rest and in transit.",
        source_citation="45 CFR 164.312(a)(2)(iv) - Encryption and decryption",
        applies_to_services=["Azure Blob Storage", "Azure SQL Database", "Azure Cosmos DB",
                             "Azure Files", "Azure Disk Storage", "Azure Virtual Network"],
    ),
    ComplianceRule(
        id="US-HIPAA-002",
        region="us",
        governing_framework="US HIPAA",
        constraint_type="audit",
        constraint_text="Implement hardware, software, and/or procedural mechanisms to record and examine access and other activity in information systems containing ePHI.",
        source_citation="45 CFR 164.312(b) - Audit controls",
        applies_to_services=["*"],
    ),
    ComplianceRule(
        id="US-HIPAA-003",
        region="us",
        governing_framework="US HIPAA",
        constraint_type="audit",
        constraint_text="Conduct an accurate and thorough assessment of the potential risks and vulnerabilities to the confidentiality, integrity, and availability of ePHI.",
        source_citation="45 CFR 164.308(a)(1)(ii)(A) - Risk analysis",
        applies_to_services=["*"],
    ),
    ComplianceRule(
        id="US-HIPAA-004",
        region="us",
        governing_framework="US HIPAA",
        constraint_type="consent",
        constraint_text="Implement policies and procedures for authorizing access to ePHI. Only minimum necessary information should be accessed or disclosed.",
        source_citation="45 CFR 164.312(a)(1) - Access control; 45 CFR 164.502(b) - Minimum necessary",
        applies_to_services=["*"],
    ),
    ComplianceRule(
        id="US-HIPAA-005",
        region="us",
        governing_framework="US HIPAA",
        constraint_type="breach_notification",
        constraint_text="Notify affected individuals, the Secretary of HHS, and (in some cases) the media following a breach of unsecured ePHI.",
        source_citation="45 CFR 164.400-414 - Breach notification requirements",
        applies_to_services=["*"],
    ),
]


def get_rules_for_region(region: str) -> list[ComplianceRule]:
    """Get all active compliance rules for a region.

    Uses a hybrid approach:
    1. Hardcoded rules (primary) — curated manually for known regions.
    2. RAG fallback (secondary) — vector DB similarity search for unknown regions.
    """
    region = region.lower().strip()

    # Step 1: Check hardcoded rules
    if region in _COMPLIANCE_RULES:
        return [r for r in _COMPLIANCE_RULES[region] if r.active]

    # Lazy initialization for known regions with string matching
    if "india" in region or "in" in region:
        _COMPLIANCE_RULES["india"] = _INDIA_DPDP_RULES
        return _INDIA_DPDP_RULES
    elif "eu" in region or "europe" in region:
        _COMPLIANCE_RULES["eu"] = _EU_GDPR_RULES
        return _EU_GDPR_RULES
    elif "us" in region or "usa" in region or "united states" in region:
        _COMPLIANCE_RULES["us"] = _US_HIPAA_RULES
        return _US_HIPAA_RULES
    elif "uae" in region or "united arab emirates" in region or "dubai" in region or "abudhabi" in region or "uaenorth" in region:
        _COMPLIANCE_RULES["uae"] = _UAE_PDPL_RULES
        return _UAE_PDPL_RULES

    # Step 2: RAG fallback for unknown regions
    try:
        from src.core.compliance_rag import hybrid_get_rules as rag_get
        rag_rules = rag_get(region)
        if rag_rules:
            return rag_rules
    except Exception as e:
        logger.warning(f"RAG fallback failed for '{region}': {e}")

    return []


def get_all_rules() -> list[ComplianceRule]:
    """Get all compliance rules across all regions."""
    rules = []
    for region_list in _COMPLIANCE_RULES.values():
        rules.extend(region_list)
    return rules


def get_frameworks_for_region(region: str) -> list[str]:
    """Get the governing frameworks applicable to a region."""
    rules = get_rules_for_region(region)
    return list(set(r.governing_framework for r in rules))


# UAE - PDPL (Federal Decree-Law No. 45 of 2021)
_UAE_PDPL_RULES = [
    ComplianceRule(
        id="AE-PDPL-001",
        region="uae",
        governing_framework="UAE PDPL (Federal Decree-Law No. 45 of 2021)",
        constraint_type="residency",
        constraint_text="Personal data may be transferred outside the UAE only if the destination provides adequate data protection as determined by the UAE Data Office, or with explicit consent.",
        source_citation="UAE PDPL Article 14-16 - Cross-border data transfer",
        applies_to_services=["*"],
    ),
    ComplianceRule(
        id="AE-PDPL-002",
        region="uae",
        governing_framework="UAE PDPL (Federal Decree-Law No. 45 of 2021)",
        constraint_type="consent",
        constraint_text="Processing of personal data requires express consent of the data subject, unless exceptions apply (public health, legal compliance, contract performance).",
        source_citation="UAE PDPL Article 6 - Consent requirements",
        applies_to_services=["*"],
    ),
    ComplianceRule(
        id="AE-PDPL-003",
        region="uae",
        governing_framework="UAE PDPL (Federal Decree-Law No. 45 of 2021)",
        constraint_type="breach_notification",
        constraint_text="Data breaches compromising privacy, confidentiality, or security of personal data must be reported to the UAE Data Office and affected data subjects within 72 hours for high-risk breaches.",
        source_citation="UAE PDPL Article 30 - Breach notification",
        applies_to_services=["*"],
    ),
    ComplianceRule(
        id="AE-PDPL-004",
        region="uae",
        governing_framework="UAE PDPL (Federal Decree-Law No. 45 of 2021)",
        constraint_type="audit",
        constraint_text="Data controllers must maintain records of processing activities and demonstrate compliance with PDPL requirements upon request by the UAE Data Office.",
        source_citation="UAE PDPL Article 19 - Records of processing",
        applies_to_services=["*"],
    ),
    ComplianceRule(
        id="AE-PDPL-005",
        region="uae",
        governing_framework="UAE PDPL (Federal Decree-Law No. 45 of 2021)",
        constraint_type="encryption",
        constraint_text="Appropriate technical and organizational measures, including encryption, must be implemented to protect personal data from unauthorized access or processing.",
        source_citation="UAE PDPL Article 21 - Security measures",
        applies_to_services=["*"],
    ),
    ComplianceRule(
        id="AE-PDPL-006",
        region="uae",
        governing_framework="UAE PDPL (Federal Decree-Law No. 45 of 2021)",
        constraint_type="audit",
        constraint_text="Data Protection Impact Assessments (DPIA) must be conducted for high-risk processing activities. Penalties for non-compliance range from AED 50,000 to AED 5,000,000.",
        source_citation="UAE PDPL Article 22 - DPIA; Article 42 - Penalties",
        applies_to_services=["*"],
    ),
    ComplianceRule(
        id="AE-PDPL-007",
        region="uae",
        governing_framework="UAE PDPL (Federal Decree-Law No. 45 of 2021)",
        constraint_type="residency",
        constraint_text="DIFC and ADGM free zones have separate data protection regulations (DIFC Law No. 5 of 2020, ADGM Data Protection Regulations 2021) that take precedence within those jurisdictions.",
        source_citation="DIFC Law No. 5 of 2020; ADGM Data Protection Regulations 2021",
        applies_to_services=["*"],
    ),
]

# Pre-populate the rules
_COMPLIANCE_RULES["india"] = _INDIA_DPDP_RULES
_COMPLIANCE_RULES["eu"] = _EU_GDPR_RULES
_COMPLIANCE_RULES["us"] = _US_HIPAA_RULES
_COMPLIANCE_RULES["uae"] = _UAE_PDPL_RULES
