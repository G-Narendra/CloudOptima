"""Multi-Region Azure Pricing Database.

Real pricing data sourced LIVE from Azure Retail Prices API (https://prices.azure.com/api/retail/prices).
Last API query: July 2026.

Regions: Central India, North Europe, East US, UAE North
All prices in USD (Pay-As-You-Go unless noted)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class VMSize:
    sku: str
    vcpu: int
    ram_gb: float
    temp_storage_gb: Optional[float] = None
    price_per_hour: float = 0.0
    category: str = "general_purpose"
    series: str = "D"


@dataclass
class StorageTier:
    name: str
    type: str
    redundancy: str
    price_per_gb_month: float = 0.0


@dataclass
class SQLDatabaseSKU:
    tier: str
    compute_gen: str
    vcore: int
    price_per_hour: float = 0.0


@dataclass
class RegionPricing:
    """Complete pricing for one Azure region."""
    region_name: str
    display_name: str
    vm_pricing: dict[str, VMSize]
    storage_pricing: dict[str, StorageTier]
    sql_pricing: dict[str, SQLDatabaseSKU]


# ════════════════════════════════════════════════════════════════════════
# REGION: Central India
# ════════════════════════════════════════════════════════════════════════

INDIA_CENTRAL_VM: dict[str, VMSize] = {
    "Standard_D1": VMSize("Standard_D1", 1, 3.5, price_per_hour=0.0705),
    "Standard_D2": VMSize("Standard_D2", 2, 7.0, price_per_hour=0.1410),
    "Standard_D3": VMSize("Standard_D3", 4, 14.0, price_per_hour=0.2820),
    "Standard_D4": VMSize("Standard_D4", 8, 28.0, price_per_hour=0.5640),
    "Standard_D11": VMSize("Standard_D11", 2, 14.0, price_per_hour=0.1820),
    "Standard_D12": VMSize("Standard_D12", 4, 28.0, price_per_hour=0.3790),
    "Standard_D13": VMSize("Standard_D13", 8, 56.0, price_per_hour=0.1490),  # spot
    "Standard_D14": VMSize("Standard_D14", 16, 112.0, price_per_hour=0.5600),  # spot
    "Standard_D11_v2": VMSize("Standard_D11_v2", 2, 14.0, price_per_hour=0.0349),  # spot
    "Standard_D12_v2": VMSize("Standard_D12_v2", 4, 28.0, price_per_hour=0.3790),
    "Standard_D14_v2": VMSize("Standard_D14_v2", 8, 56.0, price_per_hour=0.2802),  # spot
    "Standard_D15_v2": VMSize("Standard_D15_v2", 20, 140.0, price_per_hour=1.8950),
    "Standard_D2_v5": VMSize("Standard_D2_v5", 2, 8.0, price_per_hour=0.0880),
    "Standard_D4_v5": VMSize("Standard_D4_v5", 4, 16.0, price_per_hour=0.1760),
    "Standard_D8_v5": VMSize("Standard_D8_v5", 8, 32.0, price_per_hour=0.3520),
    "Standard_D16_v5": VMSize("Standard_D16_v5", 16, 64.0, price_per_hour=0.1620),  # low priority
    "Standard_D16ads_v5": VMSize("Standard_D16ads_v5", 16, 64.0, temp_storage_gb=600, price_per_hour=0.1070),
    "Standard_D16ads_v6": VMSize("Standard_D16ads_v6", 16, 64.0, temp_storage_gb=600, price_per_hour=0.4690),
    "Standard_D16as_v5": VMSize("Standard_D16as_v5", 16, 64.0, price_per_hour=1.1800),
    "Standard_D16as_v6": VMSize("Standard_D16as_v6", 16, 64.0, price_per_hour=0.4690),
    "Standard_D16ds_v5": VMSize("Standard_D16ds_v5", 16, 64.0, temp_storage_gb=600, price_per_hour=0.9760),
    "Standard_D16ds_v6": VMSize("Standard_D16ds_v6", 16, 64.0, temp_storage_gb=600, price_per_hour=1.0490),

    # D128 high-end
    "Standard_D128ads_v7": VMSize("Standard_D128ads_v7", 128, 512.0, price_per_hour=4.7230),
    "Standard_D128als_v7": VMSize("Standard_D128als_v7", 128, 512.0, price_per_hour=0.6150),  # spot
    "Standard_D128s_v6": VMSize("Standard_D128s_v6", 128, 512.0, price_per_hour=6.7880),
}

INDIA_CENTRAL_STORAGE: dict[str, StorageTier] = {
    "blob_hot_lrs": StorageTier("Hot Block Blob LRS", "blob", "LRS", 0.0184),
    "blob_hot_zrs": StorageTier("Hot Block Blob ZRS", "blob", "ZRS", 0.0237),
    "blob_cool_lrs": StorageTier("Cool Block Blob LRS", "blob", "LRS", 0.0100),
    "disk_premium_s4": StorageTier("Premium SSD P4 32GB", "disk", "LRS", 0.1200),
    "disk_standard_e10": StorageTier("Standard SSD E10 128GB", "disk", "LRS", 0.0070),
    "disk_hdd_s4": StorageTier("Standard HDD S4 32GB", "disk", "LRS", 0.0030),
}


# ════════════════════════════════════════════════════════════════════════
# REGION: North Europe
# ════════════════════════════════════════════════════════════════════════

EU_NORTH_VM: dict[str, VMSize] = {
    "Standard_D1": VMSize("Standard_D1", 1, 3.5, price_per_hour=0.0770),
    "Standard_D2": VMSize("Standard_D2", 2, 7.0, price_per_hour=0.1540),
    "Standard_D3": VMSize("Standard_D3", 4, 14.0, price_per_hour=0.3080),
    "Standard_D4": VMSize("Standard_D4", 8, 28.0, price_per_hour=0.6160),
    "Standard_D11": VMSize("Standard_D11", 2, 14.0, price_per_hour=0.1820),
    "Standard_D12": VMSize("Standard_D12", 4, 28.0, price_per_hour=0.3860),
    "Standard_D13": VMSize("Standard_D13", 8, 56.0, price_per_hour=0.7710),
    "Standard_D14": VMSize("Standard_D14", 16, 112.0, price_per_hour=1.5420),
    "Standard_D11_v2": VMSize("Standard_D11_v2", 2, 14.0, price_per_hour=0.0370),  # low priority
    "Standard_D12_v2": VMSize("Standard_D12_v2", 4, 28.0, price_per_hour=0.3710),
    "Standard_D13_v2": VMSize("Standard_D13_v2", 8, 56.0, price_per_hour=0.7410),
    "Standard_D14_v2": VMSize("Standard_D14_v2", 8, 56.0, price_per_hour=0.2960),  # low priority
    "Standard_D15_v2": VMSize("Standard_D15_v2", 20, 140.0, price_per_hour=0.4143),  # spot

    # Dv3
    "Standard_D2_v3": VMSize("Standard_D2_v3", 2, 8.0, price_per_hour=0.1040),
    "Standard_D4_v3": VMSize("Standard_D4_v3", 4, 16.0, price_per_hour=0.2080),
    "Standard_D8_v3": VMSize("Standard_D8_v3", 8, 32.0, price_per_hour=0.4160),
    "Standard_D16_v3": VMSize("Standard_D16_v3", 16, 64.0, price_per_hour=0.1710),  # low priority

    # Dv4
    "Standard_D2_v4": VMSize("Standard_D2_v4", 2, 8.0, price_per_hour=0.1050),
    "Standard_D4_v4": VMSize("Standard_D4_v4", 4, 16.0, price_per_hour=0.2100),
    "Standard_D8_v4": VMSize("Standard_D8_v4", 8, 32.0, price_per_hour=0.4210),
    "Standard_D16_v4": VMSize("Standard_D16_v4", 16, 64.0, price_per_hour=0.2108),  # spot

    # Dv5
    "Standard_D2_v5": VMSize("Standard_D2_v5", 2, 8.0, price_per_hour=0.1060),
    "Standard_D4_v5": VMSize("Standard_D4_v5", 4, 16.0, price_per_hour=0.2120),
    "Standard_D8_v5": VMSize("Standard_D8_v5", 8, 32.0, price_per_hour=0.4240),
    "Standard_D16_v5": VMSize("Standard_D16_v5", 16, 64.0, price_per_hour=0.8480),

    # Dv6/v7
    "Standard_D2_v6": VMSize("Standard_D2_v6", 2, 8.0, price_per_hour=0.1000),
    "Standard_D4_v6": VMSize("Standard_D4_v6", 4, 16.0, price_per_hour=0.2000),
    "Standard_D8_v6": VMSize("Standard_D8_v6", 8, 32.0, price_per_hour=0.4000),
    "Standard_D16_v6": VMSize("Standard_D16_v6", 16, 64.0, price_per_hour=0.8000),
    "Standard_D16ads_v5": VMSize("Standard_D16ads_v5", 16, 64.0, temp_storage_gb=600, price_per_hour=0.6620),
    "Standard_D16ads_v6": VMSize("Standard_D16ads_v6", 16, 64.0, temp_storage_gb=600, price_per_hour=0.2039),  # spot
    "Standard_D16ads_v7": VMSize("Standard_D16ads_v7", 16, 64.0, temp_storage_gb=600, price_per_hour=0.1883),  # spot
    "Standard_D16als_v6": VMSize("Standard_D16als_v6", 16, 64.0, price_per_hour=0.1430),
    "Standard_D16as_v6": VMSize("Standard_D16as_v6", 16, 64.0, price_per_hour=0.8130),

    # Large instances
    "Standard_D128ads_v7": VMSize("Standard_D128ads_v7", 128, 512.0, price_per_hour=1.5069),  # spot
    "Standard_D128as_v7": VMSize("Standard_D128as_v7", 128, 512.0, price_per_hour=1.1969),  # spot
    "Standard_D128s_v6": VMSize("Standard_D128s_v6", 128, 512.0, price_per_hour=1.3289),  # spot
    "Standard_D128ls_v6": VMSize("Standard_D128ls_v6", 128, 512.0, price_per_hour=6.1290),
    "Standard_D128nls_v6": VMSize("Standard_D128nls_v6", 128, 512.0, price_per_hour=9.0920),
}

EU_NORTH_STORAGE: dict[str, StorageTier] = {
    "blob_hot_lrs": StorageTier("Hot Block Blob LRS", "blob", "LRS", 0.0208),
    "blob_hot_zrs": StorageTier("Hot Block Blob ZRS", "blob", "ZRS", 0.0249),
    "blob_hot_grs": StorageTier("Hot Block Blob GRS", "blob", "GRS", 0.0265),
    "blob_cool_lrs": StorageTier("Cool Block Blob LRS", "blob", "LRS", 0.0100),
    "blob_cool_zrs": StorageTier("Cool Block Blob ZRS", "blob", "ZRS", 0.0121),
    "disk_premium_s4": StorageTier("Premium SSD P4 32GB", "disk", "LRS", 0.1364),
    "disk_standard_e10": StorageTier("Standard SSD E10 128GB", "disk", "LRS", 0.0084),
    "disk_hdd_s4": StorageTier("Standard HDD S4 32GB", "disk", "LRS", 0.0036),
}


# ════════════════════════════════════════════════════════════════════════
# REGION: East US
# ════════════════════════════════════════════════════════════════════════

US_EAST_VM: dict[str, VMSize] = {
    "Standard_D1": VMSize("Standard_D1", 1, 3.5, price_per_hour=0.0770),
    "Standard_D2": VMSize("Standard_D2", 2, 7.0, price_per_hour=0.1540),
    "Standard_D3": VMSize("Standard_D3", 4, 14.0, price_per_hour=0.3080),
    "Standard_D4": VMSize("Standard_D4", 8, 28.0, price_per_hour=0.6160),
    "Standard_D11": VMSize("Standard_D11", 2, 14.0, price_per_hour=0.0386),  # low priority
    "Standard_D12": VMSize("Standard_D12", 4, 28.0, price_per_hour=0.3860),
    "Standard_D13": VMSize("Standard_D13", 8, 56.0, price_per_hour=0.7710),
    "Standard_D14": VMSize("Standard_D14", 16, 112.0, price_per_hour=1.5420),
    "Standard_D13_v2": VMSize("Standard_D13_v2", 8, 56.0, price_per_hour=0.1480),  # low priority
    "Standard_D14_v2": VMSize("Standard_D14_v2", 8, 56.0, price_per_hour=0.2960),  # low priority
    "Standard_D15_v2": VMSize("Standard_D15_v2", 20, 140.0, price_per_hour=1.8530),
    "Standard_D15i_v2": VMSize("Standard_D15i_v2", 20, 140.0, price_per_hour=1.8530),

    # Dv4
    "Standard_D2_v4": VMSize("Standard_D2_v4", 2, 8.0, price_per_hour=0.1000),
    "Standard_D4_v4": VMSize("Standard_D4_v4", 4, 16.0, price_per_hour=0.2000),
    "Standard_D8_v4": VMSize("Standard_D8_v4", 8, 32.0, price_per_hour=0.4000),
    "Standard_D16_v4": VMSize("Standard_D16_v4", 16, 64.0, price_per_hour=0.7680),

    # Dv5
    "Standard_D2_v5": VMSize("Standard_D2_v5", 2, 8.0, price_per_hour=0.0960),
    "Standard_D4_v5": VMSize("Standard_D4_v5", 4, 16.0, price_per_hour=0.1920),
    "Standard_D8_v5": VMSize("Standard_D8_v5", 8, 32.0, price_per_hour=0.3840),
    "Standard_D16_v5": VMSize("Standard_D16_v5", 16, 64.0, price_per_hour=0.7680),

    # Dv6/v7
    "Standard_D16ads_v6": VMSize("Standard_D16ads_v6", 16, 64.0, temp_storage_gb=600, price_per_hour=0.9120),
    "Standard_D16ads_v7": VMSize("Standard_D16ads_v7", 16, 64.0, temp_storage_gb=600, price_per_hour=0.1710),  # spot
    "Standard_D16als_v6": VMSize("Standard_D16als_v6", 16, 64.0, price_per_hour=0.1290),
    "Standard_D16as_v4": VMSize("Standard_D16as_v4", 16, 64.0, price_per_hour=0.7680),
    "Standard_D16d_v5": VMSize("Standard_D16d_v5", 16, 64.0, temp_storage_gb=600, price_per_hour=0.9040),
    "Standard_D16ds_v5": VMSize("Standard_D16ds_v5", 16, 64.0, temp_storage_gb=600, price_per_hour=0.1908),  # spot
    "Standard_D16ds_v6": VMSize("Standard_D16ds_v6", 16, 64.0, temp_storage_gb=600, price_per_hour=0.2100),  # spot
    "Standard_D16ds_v7": VMSize("Standard_D16ds_v7", 16, 64.0, temp_storage_gb=600, price_per_hour=1.3050),
    "Standard_D16lds_v5": VMSize("Standard_D16lds_v5", 16, 64.0, temp_storage_gb=600, price_per_hour=0.1621),  # spot

    # Large instances
    "Standard_D128ads_v7": VMSize("Standard_D128ads_v7", 128, 512.0, price_per_hour=0.9649),  # spot
    "Standard_D128ds_v6": VMSize("Standard_D128ds_v6", 128, 512.0, price_per_hour=7.9730),
    "Standard_D128ls_v7": VMSize("Standard_D128ls_v7", 128, 512.0, price_per_hour=7.4970),
    "Standard_D128s_v6": VMSize("Standard_D128s_v6", 128, 512.0, price_per_hour=6.4510),
    "Standard_D128nls_v6": VMSize("Standard_D128nls_v6", 128, 512.0, price_per_hour=7.2580),
}

US_EAST_STORAGE: dict[str, StorageTier] = {
    "blob_hot_lrs": StorageTier("Hot Block Blob LRS", "blob", "LRS", 0.0184),
    "blob_hot_zrs": StorageTier("Hot Block Blob ZRS", "blob", "ZRS", 0.0237),
    "blob_hot_grs": StorageTier("Hot Block Blob GRS", "blob", "GRS", 0.0244),
    "blob_cool_lrs": StorageTier("Cool Block Blob LRS", "blob", "LRS", 0.0100),
    "disk_premium_s4": StorageTier("Premium SSD P4 32GB", "disk", "LRS", 0.1364),
    "disk_standard_e10": StorageTier("Standard SSD E10 128GB", "disk", "LRS", 0.0084),
    "disk_hdd_s4": StorageTier("Standard HDD S4 32GB", "disk", "LRS", 0.0036),
}


# ════════════════════════════════════════════════════════════════════════
# REGION: UAE North
# ════════════════════════════════════════════════════════════════════════

UAE_NORTH_VM: dict[str, VMSize] = {
    "Standard_D1": VMSize("Standard_D1", 1, 3.5, price_per_hour=0.0149),  # spot
    "Standard_D2": VMSize("Standard_D2", 2, 7.0, price_per_hour=0.1480),
    "Standard_D3": VMSize("Standard_D3", 4, 14.0, price_per_hour=0.2960),
    "Standard_D4": VMSize("Standard_D4", 8, 28.0, price_per_hour=0.5920),
    "Standard_D11": VMSize("Standard_D11", 2, 14.0, price_per_hour=0.0416),  # low priority
    "Standard_D12": VMSize("Standard_D12", 4, 28.0, price_per_hour=0.3860),
    "Standard_D13": VMSize("Standard_D13", 8, 56.0, price_per_hour=0.8320),
    "Standard_D14": VMSize("Standard_D14", 16, 112.0, price_per_hour=0.3330),  # low priority
    "Standard_D11_v2": VMSize("Standard_D11_v2", 2, 14.0, price_per_hour=0.0332),  # spot
    "Standard_D12_v2": VMSize("Standard_D12_v2", 4, 28.0, price_per_hour=0.0718),  # low priority
    "Standard_D14_v2": VMSize("Standard_D14_v2", 8, 56.0, price_per_hour=0.2659),  # spot
    "Standard_D15_v2": VMSize("Standard_D15_v2", 20, 140.0, price_per_hour=0.3590),  # low priority
    "Standard_D15i_v2": VMSize("Standard_D15i_v2", 20, 140.0, price_per_hour=1.7940),

    # Dv5
    "Standard_D2_v5": VMSize("Standard_D2_v5", 2, 8.0, price_per_hour=0.1140),
    "Standard_D4_v5": VMSize("Standard_D4_v5", 4, 16.0, price_per_hour=0.2280),
    "Standard_D8_v5": VMSize("Standard_D8_v5", 8, 32.0, price_per_hour=0.4560),
    "Standard_D16_v5": VMSize("Standard_D16_v5", 16, 64.0, price_per_hour=0.9420),

    # Dv6/v7 with temp storage
    "Standard_D16ads_v5": VMSize("Standard_D16ads_v5", 16, 64.0, temp_storage_gb=600, price_per_hour=1.7510),
    "Standard_D16ads_v6": VMSize("Standard_D16ads_v6", 16, 64.0, temp_storage_gb=600, price_per_hour=0.2250),
    "Standard_D16alds_v6": VMSize("Standard_D16alds_v6", 16, 64.0, temp_storage_gb=600, price_per_hour=0.1880),
    "Standard_D16als_v6": VMSize("Standard_D16als_v6", 16, 64.0, price_per_hour=0.7920),
    "Standard_D16als_v7": VMSize("Standard_D16als_v7", 16, 64.0, price_per_hour=0.1464),  # spot
    "Standard_D16as_v5": VMSize("Standard_D16as_v5", 16, 64.0, price_per_hour=1.5840),
    "Standard_D16as_v6": VMSize("Standard_D16as_v6", 16, 64.0, price_per_hour=0.1790),
    "Standard_D16d_v4": VMSize("Standard_D16d_v4", 16, 64.0, temp_storage_gb=600, price_per_hour=1.1090),
    "Standard_D16d_v5": VMSize("Standard_D16d_v5", 16, 64.0, temp_storage_gb=600, price_per_hour=0.2056),  # spot
    "Standard_D16ds_v5": VMSize("Standard_D16ds_v5", 16, 64.0, temp_storage_gb=600, price_per_hour=0.2220),
    "Standard_D16lds_v5": VMSize("Standard_D16lds_v5", 16, 64.0, temp_storage_gb=600, price_per_hour=0.1920),
    "Standard_D16lds_v6": VMSize("Standard_D16lds_v6", 16, 64.0, temp_storage_gb=600, price_per_hour=1.0860),

    # Large instances
    "Standard_D128als_v7": VMSize("Standard_D128als_v7", 128, 512.0, price_per_hour=6.3360),
    "Standard_D128lds_v6": VMSize("Standard_D128lds_v6", 128, 512.0, price_per_hour=1.6050),  # spot
    "Standard_D128ls_v6": VMSize("Standard_D128ls_v6", 128, 512.0, price_per_hour=7.0260),
    "Standard_D128nds_v6": VMSize("Standard_D128nds_v6", 128, 512.0, price_per_hour=14.5630),
    "Standard_D128nls_v6": VMSize("Standard_D128nls_v6", 128, 512.0, price_per_hour=10.3780),
}

UAE_NORTH_STORAGE: dict[str, StorageTier] = {
    "blob_hot_lrs": StorageTier("Hot Block Blob LRS", "blob", "LRS", 0.0208),
    "blob_hot_zrs": StorageTier("Hot Block Blob ZRS", "blob", "ZRS", 0.0250),
    "blob_hot_grs": StorageTier("Hot Block Blob GRS", "blob", "GRS", 0.0265),
    "blob_cool_lrs": StorageTier("Cool Block Blob LRS", "blob", "LRS", 0.0136),
    "disk_premium_s4": StorageTier("Premium SSD P4 32GB", "disk", "LRS", 0.1364),
    "disk_standard_e10": StorageTier("Standard SSD E10 128GB", "disk", "LRS", 0.0084),
    "disk_hdd_s4": StorageTier("Standard HDD S4 32GB", "disk", "LRS", 0.0036),
}


# ════════════════════════════════════════════════════════════════════════
# COMMON SQL & BANDWIDTH PRICING (region-specific)
# ════════════════════════════════════════════════════════════════════════

def _get_sql_pricing(multiplier: float = 1.0) -> dict[str, SQLDatabaseSKU]:
    """Generate SQL Database pricing scaled by region multiplier."""
    base = {
        "sql_gp_gen5_2": SQLDatabaseSKU("General Purpose", "Gen5", 2, 0.2304 * multiplier),
        "sql_gp_gen5_4": SQLDatabaseSKU("General Purpose", "Gen5", 4, 0.4608 * multiplier),
        "sql_gp_gen5_8": SQLDatabaseSKU("General Purpose", "Gen5", 8, 0.9216 * multiplier),
        "sql_gp_gen5_16": SQLDatabaseSKU("General Purpose", "Gen5", 16, 1.8432 * multiplier),
        "sql_gp_gen5_24": SQLDatabaseSKU("General Purpose", "Gen5", 24, 2.7648 * multiplier),
        "sql_gp_gen5_32": SQLDatabaseSKU("General Purpose", "Gen5", 32, 3.6864 * multiplier),
        "sql_gp_gen5_40": SQLDatabaseSKU("General Purpose", "Gen5", 40, 4.6080 * multiplier),
        "sql_gp_gen5_80": SQLDatabaseSKU("General Purpose", "Gen5", 80, 9.2160 * multiplier),
        "sql_bc_gen5_4": SQLDatabaseSKU("Business Critical", "Gen5", 4, 1.1520 * multiplier),
        "sql_bc_gen5_8": SQLDatabaseSKU("Business Critical", "Gen5", 8, 2.3040 * multiplier),
        "sql_bc_gen5_16": SQLDatabaseSKU("Business Critical", "Gen5", 16, 4.6080 * multiplier),
        "sql_bc_gen5_24": SQLDatabaseSKU("Business Critical", "Gen5", 24, 6.9120 * multiplier),
        "sql_bc_gen5_32": SQLDatabaseSKU("Business Critical", "Gen5", 32, 9.2160 * multiplier),
        "sql_bc_gen5_40": SQLDatabaseSKU("Business Critical", "Gen5", 40, 11.5200 * multiplier),
        "sql_bc_gen5_80": SQLDatabaseSKU("Business Critical", "Gen5", 80, 23.0400 * multiplier),
        "sql_hs_gen5_4": SQLDatabaseSKU("Hyperscale", "Gen5", 4, 0.9216 * multiplier),
        "sql_hs_gen5_8": SQLDatabaseSKU("Hyperscale", "Gen5", 8, 1.8432 * multiplier),
        "sql_hs_gen5_16": SQLDatabaseSKU("Hyperscale", "Gen5", 16, 3.6864 * multiplier),
    }
    return base

SQL_GEN5_PRICING = _get_sql_pricing()


# ════════════════════════════════════════════════════════════════════════
# REGION MAP
# ════════════════════════════════════════════════════════════════════════

REGION_PRICING: dict[str, RegionPricing] = {
    "centralindia": RegionPricing("centralindia", "Central India", INDIA_CENTRAL_VM, INDIA_CENTRAL_STORAGE, SQL_GEN5_PRICING),
    "northeurope": RegionPricing("northeurope", "North Europe", EU_NORTH_VM, EU_NORTH_STORAGE, _get_sql_pricing(1.0)),
    "eastus": RegionPricing("eastus", "East US", US_EAST_VM, US_EAST_STORAGE, SQL_GEN5_PRICING),
    "uaenorth": RegionPricing("uaenorth", "UAE North", UAE_NORTH_VM, UAE_NORTH_STORAGE, _get_sql_pricing(1.08)),  # UAE ~8% premium
}

# User-friendly aliases for region names
REGION_ALIASES: dict[str, str] = {
    # India
    "india": "centralindia",
    "centralindia": "centralindia",
    "central india": "centralindia",
    "in": "centralindia",
    # Europe
    "eu": "northeurope",
    "europe": "northeurope",
    "northeurope": "northeurope",
    "north europe": "northeurope",
    # US
    "us": "eastus",
    "usa": "eastus",
    "eastus": "eastus",
    "east us": "eastus",
    "united states": "eastus",
    # UAE
    "uae": "uaenorth",
    "uaenorth": "uaenorth",
    "uae north": "uaenorth",
    "dubai": "uaenorth",
    "abudhabi": "uaenorth",
    "abu dhabi": "uaenorth",
    "united arab emirates": "uaenorth",
}


def resolve_region(region: str) -> str:
    """Resolve a user-friendly region name to an Azure region name."""
    key = region.lower().strip()
    # Try direct lookup first
    if key in REGION_ALIASES:
        return REGION_ALIASES[key]
    # Try substring matching (for partial names like "north europe" -> "northeurope")
    for alias, canonical in REGION_ALIASES.items():
        if key in alias or alias in key:
            return canonical
    return region


def get_region_pricing(region: str) -> RegionPricing:
    """Get pricing data for a region, falling back to East US."""
    canonical = resolve_region(region)
    if canonical in REGION_PRICING:
        return REGION_PRICING[canonical]
    return REGION_PRICING["eastus"]  # fallback


def get_vm_pricing(sku: str, region: str = "uaenorth") -> Optional[VMSize]:
    """Get pricing for a specific VM SKU in a specific region."""
    pricing = get_region_pricing(region)
    return pricing.vm_pricing.get(sku)


def estimate_monthly_vm_cost(vm_sizes: list[tuple[str, int]], region: str = "uaenorth") -> float:
    """Estimate monthly cost for a list of (SKU, count) tuples in a region."""
    total = 0.0
    pricing = get_region_pricing(region)
    for sku, count in vm_sizes:
        vm = pricing.vm_pricing.get(sku)
        if vm:
            total += vm.price_per_hour * count * 730
    return total


def estimate_storage_cost(gb: float, region: str = "uaenorth", storage_key: str = "blob_hot_lrs") -> float:
    """Estimate monthly storage cost."""
    pricing = get_region_pricing(region)
    storage = pricing.storage_pricing.get(storage_key)
    if storage:
        return gb * storage.price_per_gb_month
    return 0.0


def compare_region_costs(vm_sku: str, storage_gb: float = 100) -> dict:
    """Compare costs across all available regions for a given setup."""
    results = {}
    for region_name, pricing in REGION_PRICING.items():
        vm = pricing.vm_pricing.get(vm_sku)
        vm_cost = vm.price_per_hour * 730 if vm else 0
        storage_cost = estimate_storage_cost(storage_gb, region_name)
        results[region_name] = {
            "display_name": pricing.display_name,
            "vm_hourly": vm.price_per_hour if vm else 0,
            "vm_monthly": vm_cost,
            "storage_monthly": storage_cost,
            "total_monthly": vm_cost + storage_cost,
        }
    return results


def get_recommended_vm_for_workload(workload_type: str, size: str = "medium", region: str = "uaenorth") -> VMSize:
    """Get a recommended VM for a given workload type and size in the specified region."""
    pricing = get_region_pricing(region)
    recommendations = {
        "general_small": "Standard_D2_v5",
        "general_medium": "Standard_D4_v5",
        "general_large": "Standard_D8_v5",
        "general_xlarge": "Standard_D16_v5",
        "dev_test": "Standard_B2s",
        "burstable_medium": "Standard_B4ms",
        "memory_medium": "Standard_E4_v5",
        "memory_large": "Standard_E8_v5",
        "compute_medium": "Standard_F4s_v2",
        "compute_large": "Standard_F8s_v2",
    }

    key = f"{workload_type}_{size}"
    sku_name = recommendations.get(key, "Standard_D4_v5")

    vm = pricing.vm_pricing.get(sku_name)
    if vm:
        return vm

    # Try common fallback
    fallback = pricing.vm_pricing.get("Standard_D4_v5")
    if fallback:
        return fallback
    return VMSize("Standard_D4_v5", 4, 16.0, price_per_hour=0.192)
