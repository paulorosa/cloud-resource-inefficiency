"""GCP Pricing Provider for GCS storage costs."""

import threading
from typing import Dict, Optional

from cloud_resource_inefficiency.core.enums import CloudProvider, ResourceType
from cloud_resource_inefficiency.core.interfaces import BasePricingProvider
from cloud_resource_inefficiency.core.models import CloudResource, PricingDetails


DEFAULT_STORAGE_RATES = {
    "standard": 0.020,
    "nearline": 0.010,
    "coldline": 0.004,
    "archive": 0.0036,
}


class GCPPricingProvider(BasePricingProvider):
    """Calculates resource pricing for GCP GCS buckets."""

    def __init__(self) -> None:
        self._pricing_cache: Dict[str, float] = {}
        self._lock = threading.Lock()

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.GCP

    def get_resource_pricing(self, resource: CloudResource) -> PricingDetails:
        """Calculate estimated monthly pricing for a GCS bucket."""
        if resource.resource_type != ResourceType.GCP_GCS_BUCKET:
            return PricingDetails(
                monthly_cost=0.0,
                currency="USD",
                rate_source="unsupported_resource_type",
            )
        
        return self._calculate_gcs_pricing(resource)

    def _calculate_gcs_pricing(self, resource: CloudResource) -> PricingDetails:
        """Calculates monthly pricing for a GCS bucket."""
        raw_meta = resource.raw_metadata or {}
        storage_class = str(raw_meta.get("storage_class", "standard")).lower()
        size_bytes = float(raw_meta.get("size_bytes", 0.0))
        size_gb = size_bytes / (1024 ** 3)
        
        rate_per_gb = DEFAULT_STORAGE_RATES.get(storage_class, DEFAULT_STORAGE_RATES["standard"])
        storage_cost = size_gb * rate_per_gb
        
        cost_breakdown = {
            "storage_cost": round(storage_cost, 4),
            "size_gb": round(size_gb, 4),
        }
        
        unit_rates = {
            f"{storage_class}_per_gb_month": rate_per_gb,
        }
        
        return PricingDetails(
            monthly_cost=round(storage_cost, 4),
            currency="USD",
            rate_source="gcs_default_rates",
            unit_rates=unit_rates,
            cost_breakdown=cost_breakdown,
        )
