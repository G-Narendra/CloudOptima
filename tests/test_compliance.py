"""Tests for compliance rules knowledge base."""

from src.core.compliance_rules import (
    get_rules_for_region,
    get_frameworks_for_region,
    get_all_rules,
)


def test_get_rules_for_india():
    """Verify India DPDP rules are returned for 'india' region."""
    rules = get_rules_for_region("india")
    assert len(rules) > 0
    assert any(r.governing_framework == "India DPDP Act 2023" for r in rules)


def test_get_rules_for_eu():
    """Verify EU GDPR rules are returned for 'eu' region."""
    rules = get_rules_for_region("eu")
    assert len(rules) > 0
    assert any(r.governing_framework == "EU GDPR" for r in rules)


def test_get_rules_for_us():
    """Verify US HIPAA rules are returned for 'us' region."""
    rules = get_rules_for_region("us")
    assert len(rules) > 0
    assert any("HIPAA" in r.governing_framework for r in rules)


def test_get_rules_for_uae():
    """Verify UAE PDPL rules are returned for 'uae' region."""
    rules = get_rules_for_region("uae")
    assert len(rules) > 0
    assert any("UAE PDPL" in r.governing_framework for r in rules)


def test_get_rules_for_uae_variants():
    """Verify UAE region variants (dubai, uaenorth) all return PDPL rules."""
    rules_dubai = get_rules_for_region("dubai")
    rules_uaenorth = get_rules_for_region("uaenorth")
    rules_emirates = get_rules_for_region("united arab emirates")
    assert len(rules_dubai) > 0
    assert len(rules_uaenorth) > 0
    assert len(rules_emirates) > 0
    fw_dubai = set(r.governing_framework for r in rules_dubai)
    fw_uaenorth = set(r.governing_framework for r in rules_uaenorth)
    assert fw_dubai == fw_uaenorth


def test_get_rules_for_unknown_region():
    """Verify unknown region returns empty list."""
    rules = get_rules_for_region("mars")
    assert len(rules) == 0


def test_get_frameworks_for_india():
    """Verify India region returns DPDP framework."""
    frameworks = get_frameworks_for_region("india")
    assert "India DPDP Act 2023" in frameworks


def test_get_frameworks_for_eu():
    """Verify EU region returns GDPR framework."""
    frameworks = get_frameworks_for_region("eu")
    assert "EU GDPR" in frameworks


def test_get_frameworks_for_uae():
    """Verify UAE region returns PDPL framework."""
    frameworks = get_frameworks_for_region("uae")
    assert "UAE PDPL (Federal Decree-Law No. 45 of 2021)" in frameworks


def test_get_all_rules():
    """Verify all 4 frameworks are present across all rules."""
    all_rules = get_all_rules()
    frameworks = set(r.governing_framework for r in all_rules)
    assert len(frameworks) >= 4


def test_region_case_insensitivity():
    """Verify region matching is case-insensitive."""
    rules_upper = get_rules_for_region("UAE")
    rules_lower = get_rules_for_region("uae")
    assert len(rules_upper) == len(rules_lower)


def test_uae_compliance_structure():
    """Verify UAE PDPL rules have all required constraint types."""
    rules = get_rules_for_region("uae")
    constraint_types = set(r.constraint_type for r in rules)
    assert "residency" in constraint_types
    assert "consent" in constraint_types
    assert "breach_notification" in constraint_types
    assert "audit" in constraint_types
    assert "encryption" in constraint_types


def test_uae_pdpl_has_separate_rules():
    """Verify UAE PDPL rules are distinct from India DPDP and GDPR."""
    uae_rules = get_rules_for_region("uae")
    india_rules = get_rules_for_region("india")
    uae_frameworks = set(r.governing_framework for r in uae_rules)
    india_frameworks = set(r.governing_framework for r in india_rules)
    assert not uae_frameworks.intersection(india_frameworks)
