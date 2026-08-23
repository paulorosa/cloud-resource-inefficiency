"""
Cloud Resource Inefficiency Library
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A modular, extensible Python library for detecting financial opportunities
and cost inefficiencies across multi-cloud infrastructure.
"""

from .core.enums import (
    CloudProvider,
    ConfidenceLevel,
    InefficiencyCategory,
    ResourceType,
    RiskLevel,
)
from .core.interfaces import (
    BaseMetricsProvider,
    BasePricingProvider,
    BaseResourceCollector,
)
from .core.models import (
    CloudResource,
    MetricSummary,
    Opportunity,
    PricingDetails,
    ScanResult,
)
from .core.registry import InefficiencyRegistry, default_registry
from .core.rule import BaseInefficiencyRule
from .engine.scanner import InefficiencyScanner
from .formatters.output import ScanResultFormatter
from .providers.aws import (
    AWSClientFactory,
    AWSCloudWatchMetricsProvider,
    AWSEBSCollector,
    AWSPricingProvider,
    InactiveDetachedEBSVolumeRule,
    register_aws_provider,
)

__version__ = "0.1.0"

__all__ = [
    # Core Enums
    "CloudProvider",
    "ResourceType",
    "InefficiencyCategory",
    "RiskLevel",
    "ConfidenceLevel",
    # Core Models & DTOs
    "CloudResource",
    "MetricSummary",
    "PricingDetails",
    "Opportunity",
    "ScanResult",
    # Interfaces & Base Classes
    "BaseResourceCollector",
    "BaseMetricsProvider",
    "BasePricingProvider",
    "BaseInefficiencyRule",
    "InefficiencyRegistry",
    "default_registry",
    # Engine & Formatters
    "InefficiencyScanner",
    "ScanResultFormatter",
    # AWS Provider
    "AWSClientFactory",
    "AWSEBSCollector",
    "AWSCloudWatchMetricsProvider",
    "AWSPricingProvider",
    "InactiveDetachedEBSVolumeRule",
    "register_aws_provider",
]
