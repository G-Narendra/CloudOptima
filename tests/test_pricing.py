"""Tests for the multi-region Azure pricing database."""

from src.core.azure_pricing import (
    resolve_region,
    get_region_pricing,
    get_vm_pricing,
    estimate_monthly_vm_cost,
    estimate_storage_cost,
    compare_region_costs,
    get_recommended_vm_for_workload,
    REGION_PRICING,
)


def test_resolve_region_india_variants():
    """Verify all India region aliases resolve to centralindia."""
    assert resolve_region("india") == "centralindia"
    assert resolve_region("centralindia") == "centralindia"
    assert resolve_region("central india") == "centralindia"
    assert resolve_region("in") == "centralindia"


def test_resolve_region_eu_variants():
    """Verify all Europe region aliases resolve to northeurope."""
    assert resolve_region("eu") == "northeurope"
    assert resolve_region("europe") == "northeurope"
    assert resolve_region("northeurope") == "northeurope"
    assert resolve_region("north europe") == "northeurope"


def test_resolve_region_us_variants():
    """Verify all US region aliases resolve to eastus."""
    assert resolve_region("us") == "eastus"
    assert resolve_region("usa") == "eastus"
    assert resolve_region("eastus") == "eastus"
    assert resolve_region("united states") == "eastus"


def test_resolve_region_uae_variants():
    """Verify all UAE region aliases resolve to uaenorth."""
    assert resolve_region("uae") == "uaenorth"
    assert resolve_region("uaenorth") == "uaenorth"
    assert resolve_region("dubai") == "uaenorth"
    assert resolve_region("abudhabi") == "uaenorth"
    assert resolve_region("abu dhabi") == "uaenorth"
    assert resolve_region("united arab emirates") == "uaenorth"


def test_resolve_region_case_insensitive():
    """Verify region resolution is case-insensitive."""
    assert resolve_region("UAE") == "uaenorth"
    assert resolve_region("North Europe") == "northeurope"
    assert resolve_region("EAST US") == "eastus"


def test_resolve_unknown_region():
    """Verify unknown regions return the input unchanged (passthrough)."""
    result = resolve_region("mars")
    assert result == "mars"


def test_get_region_pricing_all_regions():
    """Verify each of the 4 regions has VM and storage pricing."""
    for region_name in ["centralindia", "northeurope", "eastus", "uaenorth"]:
        pricing = get_region_pricing(region_name)
        assert pricing.region_name == region_name
        assert len(pricing.vm_pricing) > 0
        assert len(pricing.storage_pricing) > 0


def test_get_region_pricing_fallback():
    """Verify unknown regions fall back to East US."""
    pricing = get_region_pricing("mars")
    assert pricing.region_name == "eastus"


def test_get_vm_pricing():
    """Verify VM pricing lookup returns correct price for a known SKU."""
    vm = get_vm_pricing("Standard_D4_v5", "uaenorth")
    assert vm is not None
    assert vm.sku == "Standard_D4_v5"
    assert vm.price_per_hour > 0


def test_get_vm_pricing_unknown():
    """Verify unknown SKU returns None."""
    vm = get_vm_pricing("NonExistent_SKU", "uaenorth")
    assert vm is None


def test_get_vm_pricing_all_regions_d4v5():
    """Verify Standard_D4_v5 exists in all regions."""
    for region_name in REGION_PRICING:
        vm = get_vm_pricing("Standard_D4_v5", region_name)
        assert vm is not None, f"D4_v5 not found in {region_name}"
        assert vm.price_per_hour > 0


def test_estimate_monthly_vm_cost():
    """Verify monthly cost calculation matches expected formula."""
    cost = estimate_monthly_vm_cost([("Standard_D4_v5", 2)], "uaenorth")
    pricing = get_region_pricing("uaenorth")
    d4 = pricing.vm_pricing["Standard_D4_v5"]
    expected = d4.price_per_hour * 2 * 730
    assert abs(cost - expected) < 0.01


def test_estimate_storage_cost():
    """Verify storage cost calculation for 100GB hot blob in UAE."""
    cost = estimate_storage_cost(100, "uaenorth", "blob_hot_lrs")
    assert cost > 0
    assert abs(cost - 2.08) < 0.10


def test_compare_region_costs():
    """Verify cost comparison returns data for all 4 regions."""
    results = compare_region_costs("Standard_D4_v5", 100)
    assert len(results) == len(REGION_PRICING)
    for region_name, data in results.items():
        assert data["vm_monthly"] > 0
        assert data["total_monthly"] > 0


def test_get_recommended_vm_for_workload():
    """Verify workload-based VM recommendations."""
    vm = get_recommended_vm_for_workload("general", "medium", "uaenorth")
    assert vm is not None
    assert vm.sku in ["Standard_D4_v5", "Standard_D4_v6"]

    vm_small = get_recommended_vm_for_workload("general", "small", "uaenorth")
    assert vm_small.vcpu >= 2


def test_get_recommended_memory_optimized():
    """Verify memory-optimized recommendation has sufficient RAM."""
    vm = get_recommended_vm_for_workload("memory", "medium", "uaenorth")
    assert vm is not None
    assert vm.ram_gb >= 16


def test_all_regions_have_storage_pricing():
    """Verify all regions have storage pricing for hot blob LRS."""
    for region_name in REGION_PRICING:
        pricing = get_region_pricing(region_name)
        assert "blob_hot_lrs" in pricing.storage_pricing, f"Missing blob_hot_lrs in {region_name}"


def test_price_consistency():
    """Verify UAE pricing is at least 80% of India pricing for same SKU."""
    uae_price = get_vm_pricing("Standard_D4_v5", "uaenorth").price_per_hour
    india_price = get_vm_pricing("Standard_D4_v5", "centralindia").price_per_hour
    assert uae_price >= india_price * 0.8
