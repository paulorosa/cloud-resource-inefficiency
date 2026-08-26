"""Detection rule for Inactive GCS Buckets (GCP-GCS-001)."""

from datetime import datetime, timedelta, timezone
import logging
import re
from typing import Any, Optional

from cloud_resource_inefficiency.core.enums import CloudProvider, ConfidenceLevel, InefficiencyCategory, ResourceType, RiskLevel
from cloud_resource_inefficiency.core.interfaces import BaseMetricsProvider, BasePricingProvider
from cloud_resource_inefficiency.core.models import CloudResource, Opportunity
from cloud_resource_inefficiency.core.rule import BaseInefficiencyRule

logger = logging.getLogger(__name__)


class InactiveGCSBucketRule(BaseInefficiencyRule):
    """Identifies GCS buckets with zero access activity or empty buckets."""

    def __init__(self, lookback_days: int = 30) -> None:
        self._lookback_days = lookback_days

    @property
    def rule_id(self) -> str:
        return "GCP-GCS-001"

    @property
    def title(self) -> str:
        return "Inactive GCS Bucket"

    @property
    def description(self) -> str:
        return (
            "GCS buckets often persist after applications are retired or data is no longer in active use. "
            "Without access activity or when empty, these buckets incur unnecessary storage charges. "
            "Inactive buckets should be deleted to eliminate ongoing costs."
        )

    @property
    def category(self) -> InefficiencyCategory:
        return InefficiencyCategory.UNUSED_RESOURCE

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.GCP

    @property
    def target_resource_type(self) -> ResourceType:
        return ResourceType.GCP_GCS_BUCKET

    def evaluate(
        self,
        resource: CloudResource,
        metrics_provider: BaseMetricsProvider,
        pricing_provider: BasePricingProvider,
        **kwargs: Any
    ) -> Optional[Opportunity]:
        """Evaluate if a GCS bucket is inactive and/or empty."""
        if resource.resource_type != ResourceType.GCP_GCS_BUCKET:
            return None

        raw_meta = resource.raw_metadata or {}
        size_bytes = float(raw_meta.get("size_bytes", 0.0))
        
        lookback_days = kwargs.get("lookback_days", self._lookback_days)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=lookback_days)

        access_metric = metrics_provider.get_metric_summary(
            resource=resource,
            metric_name="access_count",
            start_time=start_time,
            end_time=end_time,
            statistic="Sum",
        )

        is_empty = size_bytes == 0
        total_operations = access_metric.total_value
        is_inactive = total_operations == 0

        if not (is_inactive or is_empty):
            return None

        pricing_details = pricing_provider.get_resource_pricing(resource)
        monthly_savings = pricing_details.monthly_cost

        if is_empty:
            risk_level = RiskLevel.VERY_LOW
            confidence = ConfidenceLevel.HIGH
        elif is_inactive and size_bytes > 0:
            risk_level = RiskLevel.LOW
            confidence = ConfidenceLevel.HIGH
        else:
            risk_level = RiskLevel.LOW
            confidence = ConfidenceLevel.MEDIUM

        bucket_name = resource.resource_id
        safe_bucket_name = re.sub(r"[^a-zA-Z0-9_-]", "", bucket_name)
        remediation_command = f"gsutil -m rm -r gs://{safe_bucket_name}"

        if is_empty:
            recommended_actions = [
                "Bucket is empty and incurring storage metadata costs.",
                "Delete the bucket immediately.",
                remediation_command,
            ]
        else:
            recommended_actions = [
                f"Bucket has no access activity in the past {lookback_days} days.",
                "Confirm with bucket owner if data is still required.",
                f"Delete the unused bucket to save ${monthly_savings:.2f}/month.",
                remediation_command,
            ]

        evaluated_metrics = {
            "access_count": access_metric,
        }

        metadata = {
            "size_bytes": size_bytes,
            "size_gib": round(size_bytes / (1024 ** 3), 4),
            "storage_class": raw_meta.get("storage_class"),
            "location": raw_meta.get("location"),
            "is_empty": is_empty,
            "is_inactive": is_inactive,
            "lookback_days_evaluated": lookback_days,
            "total_access_operations": total_operations,
        }

        return Opportunity(
            rule_id=self.rule_id,
            title=self.title,
            description=self.description,
            category=self.category,
            resource=resource,
            estimated_monthly_savings=monthly_savings,
            currency="USD",
            confidence_level=confidence,
            risk_level=risk_level,
            pricing_details=pricing_details,
            evaluated_metrics=evaluated_metrics,
            recommended_actions=recommended_actions,
            remediation_command=remediation_command,
            metadata=metadata,
        )
