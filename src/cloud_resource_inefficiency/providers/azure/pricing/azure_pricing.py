"""Pricing estimates for Azure Managed Disks."""

from cloud_resource_inefficiency.core.enums import CloudProvider, ResourceType
from cloud_resource_inefficiency.core.interfaces import BasePricingProvider
from cloud_resource_inefficiency.core.models import CloudResource, PricingDetails


DEFAULT_DISK_RATES = {
    "PREMIUM_LRS": 0.135,
    "PREMIUM_ZRS": 0.162,
    "STANDARDSSD_LRS": 0.075,
    "STANDARDSSD_ZRS": 0.09,
    "STANDARD_LRS": 0.045,
    "STANDARD_ZRS": 0.054,
    "ULTRASSD_LRS": 0.12,
}


class AzurePricingProvider(BasePricingProvider):
    """Calculates monthly storage estimates using configurable local rates."""

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.AZURE

    def get_resource_pricing(self, resource: CloudResource) -> PricingDetails:
        if resource.resource_type != ResourceType.AZURE_MANAGED_DISK:
            return PricingDetails(monthly_cost=0.0, rate_source="unsupported_resource_type")
        metadata = resource.raw_metadata or {}
        sku = str(metadata.get("sku", "Standard_LRS")).upper()
        rate = DEFAULT_DISK_RATES.get(sku)
        if rate is None:
            rate = next(
                (value for key, value in DEFAULT_DISK_RATES.items() if key.replace("_", "") == sku.replace("_", "")),
                DEFAULT_DISK_RATES["STANDARD_LRS"],
            )
        size_gib = float(metadata.get("size_gib", 0.0) or 0.0)
        storage_cost = size_gib * rate
        return PricingDetails(
            monthly_cost=round(storage_cost, 4),
            currency="USD",
            rate_source="azure_managed_disk_default_rates",
            unit_rates={"storage_rate_per_gib": rate},
            cost_breakdown={"storage_cost": storage_cost, "size_gib": size_gib},
        )