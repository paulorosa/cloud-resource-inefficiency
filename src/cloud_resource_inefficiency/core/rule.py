"""Base abstract class for financial inefficiency rules."""

from abc import ABC, abstractmethod
from typing import Optional

from .enums import CloudProvider, InefficiencyCategory, ResourceType
from .interfaces import BaseMetricsProvider, BasePricingProvider
from .models import CloudResource, Opportunity


class BaseInefficiencyRule(ABC):
    """Abstract base class for all inefficiency detection rules."""

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Unique identifier for the rule (e.g., CER-0066 or AWS-EBS-001)."""
        pass

    @property
    @abstractmethod
    def title(self) -> str:
        """Human-readable title of the inefficiency."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Detailed description of the inefficiency."""
        pass

    @property
    @abstractmethod
    def category(self) -> InefficiencyCategory:
        """Category of the inefficiency (e.g. Unused Resource)."""
        pass

    @property
    @abstractmethod
    def provider(self) -> CloudProvider:
        """Cloud provider target of this rule."""
        pass

    @property
    @abstractmethod
    def target_resource_type(self) -> ResourceType:
        """Resource type evaluated by this rule."""
        pass

    @abstractmethod
    def evaluate(
        self,
        resource: CloudResource,
        metrics_provider: BaseMetricsProvider,
        pricing_provider: BasePricingProvider,
        **kwargs
    ) -> Optional[Opportunity]:
        """
        Evaluate a single resource against this inefficiency rule.

        Returns an Opportunity if an inefficiency is detected, or None if the
        resource is efficient/healthy.
        """
        pass
