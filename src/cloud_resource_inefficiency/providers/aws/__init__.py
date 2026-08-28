"""AWS Provider initialization and registration."""

from cloud_resource_inefficiency.core.enums import CloudProvider, ResourceType
from cloud_resource_inefficiency.core.registry import InefficiencyRegistry, default_registry
from cloud_resource_inefficiency.providers.aws.client_factory import AWSClientFactory
from cloud_resource_inefficiency.providers.aws.collectors.ebs_collector import AWSEBSCollector
from cloud_resource_inefficiency.providers.aws.metrics.cloudwatch import AWSCloudWatchMetricsProvider
from cloud_resource_inefficiency.providers.aws.pricing.aws_pricing import AWSPricingProvider
from cloud_resource_inefficiency.providers.aws.rules.ebs_inactive_detached import InactiveDetachedEBSVolumeRule
from typing import Optional


def register_aws_provider(
    registry: InefficiencyRegistry = default_registry,
    client_factory: Optional[AWSClientFactory] = None,
    use_remote_pricing_api: bool = True,
) -> None:
    """Registers all default AWS collectors, metrics, pricing providers, and rules."""
    factory = client_factory or AWSClientFactory()

    # Register collectors
    registry.register_collector(AWSEBSCollector(client_factory=factory))

    # Register metrics provider
    registry.register_metrics_provider(AWSCloudWatchMetricsProvider(client_factory=factory))

    # Register pricing provider
    registry.register_pricing_provider(
        AWSPricingProvider(client_factory=factory, use_remote_api=use_remote_pricing_api)
    )

    # Register rules
    registry.register_rule(InactiveDetachedEBSVolumeRule())


__all__ = [
    "AWSClientFactory",
    "AWSEBSCollector",
    "AWSCloudWatchMetricsProvider",
    "AWSPricingProvider",
    "InactiveDetachedEBSVolumeRule",
    "register_aws_provider",
]
