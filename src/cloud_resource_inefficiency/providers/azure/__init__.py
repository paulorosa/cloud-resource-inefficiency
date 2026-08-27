"""Azure provider initialization and registration."""

from cloud_resource_inefficiency.core.registry import InefficiencyRegistry, default_registry
from cloud_resource_inefficiency.providers.azure.client_factory import AzureClientFactory
from cloud_resource_inefficiency.providers.azure.collectors.managed_disk_collector import AzureManagedDiskCollector
from cloud_resource_inefficiency.providers.azure.metrics.monitor import AzureMonitorMetricsProvider
from cloud_resource_inefficiency.providers.azure.pricing.azure_pricing import AzurePricingProvider
from cloud_resource_inefficiency.providers.azure.rules.managed_disk_inactive_detached import (
    InactiveDetachedManagedDiskRule,
)


def register_azure_provider(
    registry: InefficiencyRegistry = default_registry,
    client_factory: AzureClientFactory = None,
) -> None:
    """Registers Azure Managed Disk components."""
    factory = client_factory or AzureClientFactory()
    registry.register_collector(AzureManagedDiskCollector(client_factory=factory))
    registry.register_metrics_provider(AzureMonitorMetricsProvider(client_factory=factory))
    registry.register_pricing_provider(AzurePricingProvider())
    registry.register_rule(InactiveDetachedManagedDiskRule())


__all__ = [
    "AzureClientFactory",
    "AzureManagedDiskCollector",
    "AzureMonitorMetricsProvider",
    "AzurePricingProvider",
    "InactiveDetachedManagedDiskRule",
    "register_azure_provider",
]