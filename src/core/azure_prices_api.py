"""
Azure Retail Prices API Client — Live Pricing Data Source

Queries the Microsoft Azure Retail Prices API (public, no auth required)
for real-time VM, storage, and service pricing across all Azure regions.

API Docs: https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices
Endpoint: https://prices.azure.com/api/retail/prices

Features:
- Public API — no authentication needed
- Filter by region, SKU, service name, price type
- Supports Pay-As-You-Go, Reservation, and Spot pricing
- Pagination handling (NextPageLink)
- Caching via the existing LLMCache to avoid redundant API calls
- Graceful fallback to static pricing data on network failure
"""

from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Optional
import httpx

from src.core.azure_pricing import get_region_pricing, VMSize
from src.core.llm_cache import get_cache

logger = logging.getLogger(__name__)

AZURE_RETAIL_API = "https://prices.azure.com/api/retail/prices"
DEFAULT_API_VERSION = "2023-01-01-preview"  # Latest preview (supports savings plans)
REQUEST_TIMEOUT = 10.0  # seconds
MAX_RETRIES = 2


@dataclass
class AzurePriceItem:
    """A single pricing item from the Azure Retail Prices API."""
    retail_price: float = 0.0
    unit_price: float = 0.0
    currency_code: str = "USD"
    arm_region_name: str = ""
    sku_name: str = ""
    service_name: str = ""
    meter_name: str = ""
    unit_of_measure: str = "1 Hour"
    price_type: str = "Consumption"  # Consumption, Reservation, Spot
    tier_minimum_units: Optional[float] = None
    reservation_term: Optional[str] = None  # 1 Year, 3 Years
    effective_start_date: str = ""


def _parse_price_item(item: dict) -> AzurePriceItem:
    """Parse a raw API response item into an AzurePriceItem."""
    return AzurePriceItem(
        retail_price=item.get("retailPrice", 0.0),
        unit_price=item.get("unitPrice", 0.0),
        currency_code=item.get("currencyCode", "USD"),
        arm_region_name=item.get("armRegionName", ""),
        sku_name=item.get("skuName", ""),
        service_name=item.get("serviceName", ""),
        meter_name=item.get("meterName", ""),
        unit_of_measure=item.get("unitOfMeasure", "1 Hour"),
        price_type=item.get("type", "Consumption"),
        tier_minimum_units=item.get("tierMinimumUnits"),
        reservation_term=item.get("reservationTerm"),
        effective_start_date=item.get("effectiveStartDate", ""),
    )


def build_filter(**kwargs) -> str:
    """Build an OData $filter string from keyword arguments.

    Examples:
        build_filter(armRegionName="centralindia", serviceName="Virtual Machines")
        => "armRegionName eq 'centralindia' and serviceName eq 'Virtual Machines'"

        build_filter(skuName="Standard_D4_v5")
        => "skuName eq 'Standard_D4_v5'"
    """
    clauses = []
    for key, value in kwargs.items():
        if value is not None:
            clauses.append(f"{key} eq '{value}'")
    return " and ".join(clauses)


def query_prices(
    service_name: Optional[str] = None,
    arm_region_name: Optional[str] = None,
    sku_name: Optional[str] = None,
    price_type: Optional[str] = None,
    meter_name: Optional[str] = None,
    max_results: int = 50,
    use_cache: bool = True,
) -> list[AzurePriceItem]:
    """Query the Azure Retail Prices API for pricing data.

    This is the primary public entry point. All filters are optional.
    The API is public and requires no authentication.

    Args:
        service_name: e.g. "Virtual Machines", "Storage", "SQL Database"
        arm_region_name: Azure region name e.g. "centralindia", "eastus"
        sku_name: VM SKU e.g. "Standard_D4_v5"
        price_type: "Consumption", "Reservation", or "Spot"
        meter_name: Specific meter name for granular filtering
        max_results: Maximum items to return (API returns up to 1000 per page)
        use_cache: Whether to check the LLM cache first

    Returns:
        List of AzurePriceItem matching the filters
    """
    # Build cache key from query parameters
    cache_key_parts = f"{service_name}|{arm_region_name}|{sku_name}|{price_type}|{meter_name}"

    if use_cache:
        try:
            cache = get_cache()
            cache_key = f"azure_prices:{cache_key_parts}"
            cached = cache.get_raw(cache_key)
            if cached is not None:
                cached_items = json.loads(cached)
                logger.info(f"[PRICES CACHE HIT] {cache_key_parts} ({len(cached_items)} items)")
                return [AzurePriceItem(**item) for item in cached_items]
        except Exception as e:
            logger.debug(f"Cache lookup failed for prices: {e}")

    logger.info(f"[PRICES API] Querying: service={service_name}, region={arm_region_name}, sku={sku_name}")

    filter_str = build_filter(
        serviceName=service_name,
        armRegionName=arm_region_name,
        skuName=sku_name,
        type=price_type,
        meterName=meter_name,
    )

    url = AZURE_RETAIL_API
    if filter_str:
        url += f"?$filter={filter_str}"

    all_items: list[AzurePriceItem] = []
    retries = 0

    while url and len(all_items) < max_results:
        try:
            resp = httpx.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            items = data.get("Items", [])
            for item in items:
                all_items.append(_parse_price_item(item))
                if len(all_items) >= max_results:
                    break

            # Follow pagination
            url = data.get("NextPageLink", "")
            retries = 0  # Reset retries on success

        except httpx.TimeoutException:
            retries += 1
            if retries > MAX_RETRIES:
                logger.warning(f"Azure Prices API timeout after {MAX_RETRIES} retries")
                break
            logger.warning(f"Azure Prices API timeout (retry {retries}/{MAX_RETRIES})")
            continue

        except httpx.HTTPStatusError as e:
            logger.warning(f"Azure Prices API HTTP error: {e.response.status_code} {e.response.text[:200]}")
            break

        except Exception as e:
            logger.warning(f"Azure Prices API error: {e}")
            break

    logger.info(f"[PRICES API] Retrieved {len(all_items)} items for {cache_key_parts}")

    # Cache the results using raw key-value API
    if use_cache and all_items:
        try:
            cache = get_cache()
            cache_key = f"azure_prices:{cache_key_parts}"
            serialized = json.dumps([item.__dict__ for item in all_items])
            cache.set_raw(cache_key, serialized)
        except Exception as e:
            logger.debug(f"Failed to cache prices: {e}")

    return all_items


def get_vm_price(sku_name: str, arm_region_name: str, price_type: str = "Consumption") -> Optional[float]:
    """Get the hourly price for a specific VM SKU in a specific region.

    Example:
        get_vm_price("Standard_D4_v5", "centralindia")
        => 0.176 (hourly price in USD)
    """
    items = query_prices(
        service_name="Virtual Machines",
        arm_region_name=arm_region_name,
        sku_name=sku_name,
        price_type=price_type,
        max_results=5,
    )
    if items:
        return items[0].retail_price
    return None


def get_storage_price(region: str, tier: str = "Hot Block Blob LRS") -> Optional[float]:
    """Get the per-GB-month storage price for a region.

    Example:
        get_storage_price("centralindia", "Hot Block Blob LRS")
        => 0.0184 (per GB/month in USD)
    """
    items = query_prices(
        service_name="Storage",
        arm_region_name=region,
        meter_name=tier,
        max_results=3,
    )
    if items:
        return items[0].retail_price
    return None


def compare_regions_for_sku(sku_name: str, regions: list[str] | None = None) -> dict[str, float]:
    """Compare the price of a VM SKU across multiple regions.

    Args:
        sku_name: VM SKU e.g. "Standard_D4_v5"
        regions: List of Azure region names. Defaults to all 4 supported regions.

    Returns:
        Dict of region_name -> hourly_price
    """
    if regions is None:
        regions = ["centralindia", "northeurope", "eastus", "uaenorth"]

    results = {}
    for region in regions:
        price = get_vm_price(sku_name, region)
        if price is not None:
            results[region] = price
        else:
            # Fallback to static pricing
            try:
                pricing = get_region_pricing(region)
                vm = pricing.vm_pricing.get(sku_name)
                if vm:
                    results[region] = vm.price_per_hour
            except Exception:
                pass
    return results


def get_recommendation_summary(sku_name: str, region: str = "centralindia") -> dict:
    """Get a complete pricing summary for a VM SKU including all price types.

    Returns PAYG, Reservation (1yr, 3yr), and Spot prices if available.
    Makes a single API call (without price_type filter) and splits results
    by price_type in Python — avoids 3 separate API calls.
    """
    results = {"sku": sku_name, "region": region, "prices": {}}

    # Single API call without price_type filter - get all price types at once
    items = query_prices(
        service_name="Virtual Machines",
        arm_region_name=region,
        sku_name=sku_name,
        price_type=None,  # No filter = all price types
        max_results=10,
    )

    for item in items:
        price_type = item.price_type
        if price_type not in results["prices"]:
            results["prices"][price_type] = {
                "hourly": item.retail_price,
                "monthly": round(item.retail_price * 730, 2),
                "currency": item.currency_code,
                "term": item.reservation_term,
            }

    # Fallback to static pricing for Consumption if API returned nothing
    if "Consumption" not in results["prices"]:
        try:
            pricing = get_region_pricing(region)
            vm = pricing.vm_pricing.get(sku_name)
            if vm:
                results["prices"]["Consumption"] = {
                    "hourly": vm.price_per_hour,
                    "monthly": round(vm.price_per_hour * 730, 2),
                    "currency": "USD",
                    "term": None,
                }
        except Exception:
            pass

    return results


def verify_api_access() -> dict:
    """Verify that the Azure Retail Prices API is accessible.

    Makes a minimal query and returns connectivity status.
    Useful for health checks and diagnostics.

    Returns:
        dict with "status", "latency_ms", and "items_count" keys
    """
    start = time.monotonic()
    try:
        resp = httpx.get(
            f"{AZURE_RETAIL_API}?$filter=serviceName eq 'Virtual Machines'&$top=1",
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        latency = (time.monotonic() - start) * 1000
        return {
            "status": "ok",
            "latency_ms": round(latency, 2),
            "items_count": len(data.get("Items", [])),
            "message": "Azure Retail Prices API is accessible",
        }
    except httpx.TimeoutException:
        return {
            "status": "timeout",
            "latency_ms": REQUEST_TIMEOUT * 1000,
            "items_count": 0,
            "message": f"API did not respond within {REQUEST_TIMEOUT}s",
        }
    except Exception as e:
        return {
            "status": "error",
            "latency_ms": round((time.monotonic() - start) * 1000, 2),
            "items_count": 0,
            "message": f"API error: {e}",
        }
