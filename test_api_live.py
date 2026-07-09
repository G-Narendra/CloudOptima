"""
Pre-deployment verification script.
Tests the live Azure Retail Prices API, runs diagnostics, and reports results.
"""
import sys
import os
import time
import json

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx

AZURE_RETAIL_API = "https://prices.azure.com/api/retail/prices"
PASS = 0
FAIL = 0
WARN = 0
SCRIPT_START = time.monotonic()

def test(name, condition, detail=""):
    global PASS, FAIL, WARN
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")

def warn(name, detail=""):
    global WARN
    WARN += 1
    print(f"  [WARN] {name}  {detail}")


print("=" * 60)
print("PRE-DEPLOYMENT VERIFICATION")
print("=" * 60)
print()

# --- [1/5] Azure Retail Prices API ---
print("--- [1/5] Azure Retail Prices API ---")

start = time.monotonic()
try:
    # Azure Retail Prices API uses OData $filter syntax
    # Note: $top is NOT supported - use NextPageLink for pagination
    url = f"{AZURE_RETAIL_API}?$filter=serviceName eq 'Virtual Machines'"
    resp = httpx.get(url, timeout=15.0)
    
    test("HTTP Status 200", resp.status_code == 200, f"Got {resp.status_code}")
    
    data = resp.json()
    all_items = data.get("Items", [])
    # Take first 3 items (no $top parameter - API paginates via NextPageLink)
    items = all_items[:3]
    
    test("Response has Items array", isinstance(all_items, list), f"Type: {type(all_items)}")
    test("At least 1 item returned", len(all_items) >= 1, f"Total count: {len(all_items)}")
    
    if items:
        item = items[0]
        test("Item has retailPrice", "retailPrice" in item)
        test("Item has skuName", "skuName" in item)
        test("Item has armRegionName", "armRegionName" in item)
        print(f"\n  Sample data from API:")
        for i, item in enumerate(items[:3]):
            region = item.get("armRegionName", "?")
            sku = item.get("skuName", "?")
            price = item.get("retailPrice", "?")
            currency = item.get("currencyCode", "?")
            print(f"    {i+1}. {region} | {sku} | {currency} ${price}/hr")
    
    api_latency = (time.monotonic() - start) * 1000
    print(f"\n  API Latency: {api_latency:.0f}ms\n")

except Exception as e:
    test(f"API accessible", False, str(e))
    print(f"\n  ERROR: {e}\n")


# --- [2/5] Azure Prices API Module ---
print("--- [2/5] Azure Prices API Module ---")

try:
    from src.core.azure_prices_api import (
        query_prices, get_vm_price, verify_api_access,
        compare_regions_for_sku, get_recommendation_summary
    )
    test("Module imported successfully", True)
    
    # Test verify_api_access
    access = verify_api_access()
    test(f"verify_api_access status={access['status']}", 
         access["status"] == "ok", f"Latency: {access.get('latency_ms', '?')}ms")
    
    # Test query_prices with specific SKU
    items = query_prices(
        service_name="Virtual Machines",
        arm_region_name="centralindia",
        sku_name="Standard_D4_v5",
        max_results=3,
        use_cache=False,
    )
    test(f"query_prices returned {len(items)} items", len(items) >= 1, f"Count: {len(items)}")
    if items:
        test(f"Price for Standard_D4_v5 in centralindia: ${items[0].retail_price}/hr", 
             items[0].retail_price > 0)
    
    # Test get_vm_price
    price = get_vm_price("Standard_D4_v5", "centralindia")
    test(f"get_vm_price returned ${price}/hr", price is not None and price > 0)
    
    # Test compare_regions
    comparison = compare_regions_for_sku("Standard_D4_v5", 
                                          regions=["centralindia", "eastus", "northeurope"])
    test(f"compare_regions returned {len(comparison)} regions", len(comparison) >= 2)
    for region, p in comparison.items():
        print(f"    {region}: ${p:.4f}/hr")
    
except Exception as e:
    test(f"Module test failed", False, str(e))
    import traceback
    traceback.print_exc()


# --- [3/5] Static Pricing Data Integrity ---
print("\n--- [3/5] Static Pricing Data Integrity ---")

try:
    from src.core.azure_pricing import (
        REGION_PRICING, resolve_region, get_region_pricing,
        estimate_monthly_vm_cost, compare_region_costs,
    )
    
    test("4 regions defined", len(REGION_PRICING) == 4, f"Count: {len(REGION_PRICING)}")
    
    for region_name, pricing in REGION_PRICING.items():
        test(f"{pricing.display_name} has VMs", len(pricing.vm_pricing) > 0, 
             f"SKUs: {len(pricing.vm_pricing)}")
        test(f"{pricing.display_name} has storage tiers", len(pricing.storage_pricing) > 0)
    
    test("resolve_region('india') -> 'centralindia'", 
         resolve_region("india") == "centralindia")
    test("resolve_region('uae') -> 'uaenorth'", 
         resolve_region("uae") == "uaenorth")
    
    cost = estimate_monthly_vm_cost([("Standard_D4_v5", 3)], "centralindia")
    test(f"estimate_monthly_vm_cost: 3x D4_v5 = ${cost:.2f}/mo", cost > 0)
    
    comparison = compare_region_costs("Standard_D4_v5", 1000)
    test("compare_region_costs returns 4 regions", len(comparison) == 4)
    
except Exception as e:
    test(f"Pricing data test failed", False, str(e))
    import traceback
    traceback.print_exc()


# --- [4/5] Orchestrator Integrity ---
print("\n--- [4/5] Orchestrator & Callback Integrity ---")

try:
    from src.core.orchestrator import Orchestrator
    from src.core.models import AgentType, SessionStatus
    
    # Test basic orchestrator creation
    orch = Orchestrator()
    test("Orchestrator instance created", orch is not None)
    
    # Test callback registration
    callbacks_fired = {"agent": False, "judge": False}
    def on_agent(k, info):
        callbacks_fired["agent"] = True
    def on_judge(n):
        callbacks_fired["judge"] = True
    
    orch.set_callbacks(on_agent_done=on_agent, on_judge_done=on_judge)
    test("set_callbacks registered successfully", orch._on_agent_done is not None)
    
    orch.clear_callbacks()
    test("clear_callbacks works", orch._on_agent_done is None)
    
    # Test session lifecycle (sync, non-async)
    session = orch.create_session()
    test("create_session returns valid session", session.id.startswith("session_"))
    
    orch.add_requirement(session.id, "Test infrastructure", "india")
    test("add_requirement sets region", session.region == "india")
    
    test("get_session retrieves session", orch.get_session(session.id) is not None)
    test("list_sessions returns at least 1", len(orch.list_sessions()) >= 1)
    
except Exception as e:
    test(f"Orchestrator test failed", False, str(e))
    import traceback
    traceback.print_exc()


# --- [5/5] Summary ---
duration = time.monotonic() - SCRIPT_START
print("\n--- [5/5] Summary ---")
print(f"\n  Total: {PASS + FAIL + WARN} | Pass: {PASS} | Fail: {FAIL} | Warn: {WARN}")

if FAIL == 0:
    print("\n  ALL CHECKS PASSED - Ready for deployment")
else:
    print(f"\n  {FAIL} check(s) failed - review issues before deployment")

print(f"\n  Duration: {duration:.1f}s")
print("=" * 60)

# Return exit code for CI/CD
sys.exit(0 if FAIL == 0 else 1)
