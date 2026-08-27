"""Orchestration engine for scanning cloud environments and evaluating inefficiency rules."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from cloud_resource_inefficiency.core.enums import CloudProvider, ResourceType
from cloud_resource_inefficiency.core.models import Opportunity, ScanResult
from cloud_resource_inefficiency.core.registry import InefficiencyRegistry, default_registry
from cloud_resource_inefficiency.providers.aws import register_aws_provider
from cloud_resource_inefficiency.providers.azure import register_azure_provider
from cloud_resource_inefficiency.providers.gcp import register_gcp_provider

logger = logging.getLogger(__name__)


class InefficiencyScanner:
    """
    Main scanner engine that orchestrates resource discovery, metric analysis,
    pricing calculations, and rule evaluation across cloud providers.
    """

    def __init__(
        self,
        registry: Optional[InefficiencyRegistry] = None,
        providers: Optional[List[CloudProvider]] = None,
        regions: Optional[List[str]] = None,
        auto_register_defaults: bool = True,
    ) -> None:
        self.registry = registry or default_registry
        self.providers = providers or [CloudProvider.AWS]
        self.default_regions = regions or ["us-east-1"]

        if auto_register_defaults:
            if CloudProvider.AWS in self.providers:
                # Ensure AWS default components are registered if not already present
                if not self.registry.get_rules_for_provider(CloudProvider.AWS):
                    register_aws_provider(registry=self.registry)
            
            if CloudProvider.GCP in self.providers:
                # Ensure GCP default components are registered if not already present
                if not self.registry.get_rules_for_provider(CloudProvider.GCP):
                    register_gcp_provider(registry=self.registry)

            if CloudProvider.AZURE in self.providers:
                if not self.registry.get_rules_for_provider(CloudProvider.AZURE):
                    register_azure_provider(registry=self.registry)

    def scan(
        self,
        resource_types: Optional[List[ResourceType]] = None,
        regions: Optional[List[str]] = None,
        lookback_days: int = 14,
        max_allowed_io_ops: float = 0.0,
        **kwargs: Any
    ) -> ScanResult:
        """
        Execute an inefficiency scan across specified resource types and regions.

        Args:
            resource_types: Resource types to evaluate. If None, evaluates all registered types.
            regions: List of cloud regions to scan. Defaults to instance default_regions.
            lookback_days: Number of days to inspect in CloudWatch metrics.
            max_allowed_io_ops: Maximum allowed I/O operations before considering resource active.

        Returns:
            ScanResult containing identified opportunities, metrics, and saving totals.
        """
        start_time = datetime.now(timezone.utc)
        target_regions = regions or self.default_regions
        
        # Determine target resource types
        if resource_types is None:
            rules = self.registry.get_all_rules()
            target_types = list({rule.target_resource_type for rule in rules})
        else:
            target_types = resource_types

        all_opportunities: List[Opportunity] = []
        errors: List[Dict[str, Any]] = []
        total_scanned_resources = 0

        for resource_type in target_types:
            collector = self.registry.get_collector(resource_type)
            if not collector:
                logger.warning("No collector registered for resource type: %s", resource_type)
                continue

            provider = collector.provider
            metrics_provider = self.registry.get_metrics_provider(provider)
            pricing_provider = self.registry.get_pricing_provider(provider)

            if not metrics_provider or not pricing_provider:
                logger.warning(
                    "Missing metrics provider or pricing provider for cloud provider %s", provider
                )
                continue

            rules = self.registry.get_rules_for_resource_type(resource_type)
            if not rules:
                continue

            for region in target_regions:
                try:
                    resources = collector.collect(region=region, **kwargs)
                except Exception as exc:
                    logger.error("Failed collecting %s in region %s: %s", resource_type.value, region, exc)
                    errors.append({
                        "resource_type": resource_type.value,
                        "region": region,
                        "error": str(exc),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    continue

                total_scanned_resources += len(resources)

                for resource in resources:
                    for rule in rules:
                        try:
                            opp = rule.evaluate(
                                resource=resource,
                                metrics_provider=metrics_provider,
                                pricing_provider=pricing_provider,
                                lookback_days=lookback_days,
                                max_allowed_io_ops=max_allowed_io_ops,
                                **kwargs
                            )
                            if opp:
                                all_opportunities.append(opp)
                        except Exception as exc:
                            logger.error(
                                "Error evaluating rule %s on resource %s: %s",
                                rule.rule_id,
                                resource.resource_id,
                                exc,
                            )
                            errors.append({
                                "rule_id": rule.rule_id,
                                "resource_id": resource.resource_id,
                                "region": region,
                                "error": str(exc),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            })

        end_time = datetime.now(timezone.utc)
        return ScanResult(
            opportunities=all_opportunities,
            scanned_resources_count=total_scanned_resources,
            start_time=start_time,
            end_time=end_time,
            errors=errors,
        )
