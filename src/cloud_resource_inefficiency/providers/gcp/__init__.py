"""GCP Provider initialization and registration."""

from cloud_resource_inefficiency.core.enums import CloudProvider, ResourceType
from cloud_resource_inefficiency.core.registry import InefficiencyRegistry, default_registry
from cloud_resource_inefficiency.providers.gcp.client_factory import GCPClientFactory
from cloud_resource_inefficiency.providers.gcp.collectors.gcs_collector import GCSCollector
from cloud_resource_inefficiency.providers.gcp.metrics.cloud_monitoring import GCPMonitoringMetricsProvider
from cloud_resource_inefficiency.providers.gcp.pricing.gcp_pricing import GCPPricingProvider
from cloud_resource_inefficiency.providers.gcp.rules.gcs_inactive_bucket import InactiveGCSBucketRule


def register_gcp_provider(
    registry: InefficiencyRegistry = default_registry,
    client_factory: GCPClientFactory = None,
) -> None:
    """Registers all default GCP collectors, metrics, pricing providers, and rules."""
    factory = client_factory or GCPClientFactory()

    # Register collectors
    registry.register_collector(GCSCollector(client_factory=factory))

    # Register metrics provider
    registry.register_metrics_provider(GCPMonitoringMetricsProvider(client_factory=factory))

    # Register pricing provider
    registry.register_pricing_provider(GCPPricingProvider())

    # Register rules
    registry.register_rule(InactiveGCSBucketRule())


__all__ = [
    "GCPClientFactory",
    "GCSCollector",
    "GCPMonitoringMetricsProvider",
    "GCPPricingProvider",
    "InactiveGCSBucketRule",
    "register_gcp_provider",
]
