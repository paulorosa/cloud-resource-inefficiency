"""Registry for rules, collectors, metrics, and pricing providers."""

from typing import Dict, List, Optional, Type

from .enums import CloudProvider, ResourceType
from .interfaces import BaseMetricsProvider, BasePricingProvider, BaseResourceCollector
from .rule import BaseInefficiencyRule


class InefficiencyRegistry:
    """Central registry for extensible multi-cloud rule and provider management."""

    def __init__(self) -> None:
        self._rules: Dict[str, BaseInefficiencyRule] = {}
        self._collectors: Dict[ResourceType, BaseResourceCollector] = {}
        self._metrics_providers: Dict[CloudProvider, BaseMetricsProvider] = {}
        self._pricing_providers: Dict[CloudProvider, BasePricingProvider] = {}

    def register_rule(self, rule: BaseInefficiencyRule) -> None:
        """Register a new inefficiency rule."""
        self._rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> Optional[BaseInefficiencyRule]:
        """Get a rule by its unique ID."""
        return self._rules.get(rule_id)

    def get_rules_for_resource_type(self, resource_type: ResourceType) -> List[BaseInefficiencyRule]:
        """Get all registered rules for a given resource type."""
        return [rule for rule in self._rules.values() if rule.target_resource_type == resource_type]

    def get_rules_for_provider(self, provider: CloudProvider) -> List[BaseInefficiencyRule]:
        """Get all registered rules for a given cloud provider."""
        return [rule for rule in self._rules.values() if rule.provider == provider]

    def get_all_rules(self) -> List[BaseInefficiencyRule]:
        """Return all registered rules."""
        return list(self._rules.values())

    def register_collector(self, collector: BaseResourceCollector) -> None:
        """Register a resource collector."""
        self._collectors[collector.resource_type] = collector

    def get_collector(self, resource_type: ResourceType) -> Optional[BaseResourceCollector]:
        """Get collector for a specific resource type."""
        return self._collectors.get(resource_type)

    def register_metrics_provider(self, provider: BaseMetricsProvider) -> None:
        """Register a metrics provider for a cloud provider."""
        self._metrics_providers[provider.provider] = provider

    def get_metrics_provider(self, provider: CloudProvider) -> Optional[BaseMetricsProvider]:
        """Get metrics provider for a cloud provider."""
        return self._metrics_providers.get(provider)

    def register_pricing_provider(self, provider: BasePricingProvider) -> None:
        """Register a pricing provider for a cloud provider."""
        self._pricing_providers[provider.provider] = provider

    def get_pricing_provider(self, provider: CloudProvider) -> Optional[BasePricingProvider]:
        """Get pricing provider for a cloud provider."""
        return self._pricing_providers.get(provider)


# Global default registry instance
default_registry = InefficiencyRegistry()
