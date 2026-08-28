"""Cloud Providers package."""

from .aws import (
    AWSClientFactory,
    AWSEBSCollector,
    AWSCloudWatchMetricsProvider,
    AWSPricingProvider,
    InactiveDetachedEBSVolumeRule,
    register_aws_provider,
)
from .azure import (
    AzureClientFactory,
    AzureManagedDiskCollector,
    AzureMonitorMetricsProvider,
    AzurePricingProvider,
    InactiveDetachedManagedDiskRule,
    register_azure_provider,
)

__all__ = [
    "AWSClientFactory",
    "AWSEBSCollector",
    "AWSCloudWatchMetricsProvider",
    "AWSPricingProvider",
    "InactiveDetachedEBSVolumeRule",
    "register_aws_provider",
    "AzureClientFactory",
    "AzureManagedDiskCollector",
    "AzureMonitorMetricsProvider",
    "AzurePricingProvider",
    "InactiveDetachedManagedDiskRule",
    "register_azure_provider",
]
