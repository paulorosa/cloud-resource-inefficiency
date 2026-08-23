"""Abstract interfaces and protocols for collectors, metrics, and pricing."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from .enums import CloudProvider, ResourceType
from .models import CloudResource, MetricSummary, PricingDetails


class BaseResourceCollector(ABC):
    """Abstract collector for discovering cloud resources."""

    @property
    @abstractmethod
    def provider(self) -> CloudProvider:
        """The cloud provider this collector belongs to."""
        pass

    @property
    @abstractmethod
    def resource_type(self) -> ResourceType:
        """The specific resource type this collector retrieves."""
        pass

    @abstractmethod
    def collect(self, region: str, **kwargs: Any) -> List[CloudResource]:
        """Discover and return all resources of target type in the specified region."""
        pass


class BaseMetricsProvider(ABC):
    """Abstract provider for querying usage and performance metrics."""

    @property
    @abstractmethod
    def provider(self) -> CloudProvider:
        """The cloud provider this metrics provider handles."""
        pass

    @abstractmethod
    def get_metric_summary(
        self,
        resource: CloudResource,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        statistic: str = "Sum",
        **kwargs: Any
    ) -> MetricSummary:
        """Calculate and return a summary of the requested metric over the time period."""
        pass


class BasePricingProvider(ABC):
    """Abstract provider for pricing queries and monthly cost calculation."""

    @property
    @abstractmethod
    def provider(self) -> CloudProvider:
        """The cloud provider this pricing provider handles."""
        pass

    @abstractmethod
    def get_resource_pricing(self, resource: CloudResource) -> PricingDetails:
        """Compute the estimated monthly cost and pricing details for a given resource."""
        pass
