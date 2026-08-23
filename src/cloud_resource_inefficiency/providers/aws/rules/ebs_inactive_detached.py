"""Detection rule for Inactive and Detached EBS Volumes (CER-0066)."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from cloud_resource_inefficiency.core.enums import CloudProvider, ConfidenceLevel, InefficiencyCategory, ResourceType, RiskLevel
from cloud_resource_inefficiency.core.interfaces import BaseMetricsProvider, BasePricingProvider
from cloud_resource_inefficiency.core.models import CloudResource, Opportunity
from cloud_resource_inefficiency.core.rule import BaseInefficiencyRule


class InactiveDetachedEBSVolumeRule(BaseInefficiencyRule):
    """
    Identifies detached (unattached) EBS volumes with zero or negligible I/O
    activity over a lookback window (PointFive CER-0066).
    """

    def __init__(
        self,
        lookback_days: int = 14,
        max_allowed_io_ops: float = 0.0,
    ) -> None:
        self._lookback_days = lookback_days
        self._max_allowed_io_ops = max_allowed_io_ops

    @property
    def rule_id(self) -> str:
        return "CER-0066"

    @property
    def title(self) -> str:
        return "Inactive and Detached EBS Volume"

    @property
    def description(self) -> str:
        return (
            "EBS volumes frequently remain detached ('available') after EC2 instances "
            "are terminated or reconfigured. When detached volumes show no read or write "
            "activity, they incur unnecessary ongoing storage costs without serving active workloads."
        )

    @property
    def category(self) -> InefficiencyCategory:
        return InefficiencyCategory.UNATTACHED_STORAGE

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.AWS

    @property
    def target_resource_type(self) -> ResourceType:
        return ResourceType.AWS_EBS_VOLUME

    def evaluate(
        self,
        resource: CloudResource,
        metrics_provider: BaseMetricsProvider,
        pricing_provider: BasePricingProvider,
        **kwargs: Any
    ) -> Optional[Opportunity]:
        """
        Evaluate if an EBS volume is detached and inactive.
        """
        if resource.resource_type != ResourceType.AWS_EBS_VOLUME:
            return None

        # 1. Attachment Check: Volume must be available/unattached
        raw_meta = resource.raw_metadata or {}
        status = resource.status or raw_meta.get("status")
        is_attached = raw_meta.get("is_attached", False)
        attachments = raw_meta.get("attachments", [])

        if status != "available" or is_attached or len(attachments) > 0:
            # Volume is currently attached to an instance or in a transitioning state
            return None

        # 2. Activity / Metrics Check: Lookback window for I/O operations
        lookback_days = kwargs.get("lookback_days", self._lookback_days)
        max_allowed_io = kwargs.get("max_allowed_io_ops", self._max_allowed_io_ops)

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=lookback_days)

        read_ops_summary = metrics_provider.get_metric_summary(
            resource=resource,
            metric_name="VolumeReadOps",
            start_time=start_time,
            end_time=end_time,
            statistic="Sum",
        )

        write_ops_summary = metrics_provider.get_metric_summary(
            resource=resource,
            metric_name="VolumeWriteOps",
            start_time=start_time,
            end_time=end_time,
            statistic="Sum",
        )

        total_io_ops = read_ops_summary.total_value + write_ops_summary.total_value
        if total_io_ops > max_allowed_io:
            # Volume had read/write activity recently
            return None

        # 3. Calculate Financial Opportunity / Pricing
        pricing_details = pricing_provider.get_resource_pricing(resource)
        monthly_savings = pricing_details.monthly_cost

        # 4. Risk Assessment & Preservation Tags Check
        has_snapshot = bool(raw_meta.get("snapshot_id"))
        
        # Check for preservation tags (e.g. DoNotDelete, Retain, Backup)
        retention_intent = False
        for tag_k, tag_v in resource.tags.items():
            k_lower = tag_k.lower()
            v_lower = str(tag_v).lower()
            if any(term in k_lower or term in v_lower for term in ["donotdelete", "keep", "retain", "backup", "dr"]):
                retention_intent = True
                break

        if retention_intent:
            risk_level = RiskLevel.MEDIUM
            confidence = ConfidenceLevel.MEDIUM
        elif has_snapshot:
            risk_level = RiskLevel.LOW
            confidence = ConfidenceLevel.HIGH
        else:
            risk_level = RiskLevel.LOW
            confidence = ConfidenceLevel.HIGH

        # 5. Build Recommendations and CLI remediation commands
        vol_id = resource.resource_id
        region = resource.region

        recommended_actions = [
            f"Confirm with volume owner if data in volume '{vol_id}' is still required.",
            f"Create a safety snapshot before deleting: 'aws ec2 create-snapshot --volume-id {vol_id} --region {region} --description \"Backup before deletion of unused volume\"'",
            f"Delete the unattached volume to save approximately ${monthly_savings:.2f}/month: 'aws ec2 delete-volume --volume-id {vol_id} --region {region}'",
        ]

        remediation_command = f"aws ec2 delete-volume --volume-id {vol_id} --region {region}"

        evaluated_metrics = {
            "VolumeReadOps": read_ops_summary,
            "VolumeWriteOps": write_ops_summary,
        }

        metadata = {
            "cer_code": "CER-0066",
            "pointfive_reference": "https://hub.pointfive.co/inefficiencies/inactive-and-detached-ebs-volume",
            "volume_type": raw_meta.get("volume_type"),
            "size_gib": raw_meta.get("size_gib"),
            "iops": raw_meta.get("iops"),
            "throughput": raw_meta.get("throughput"),
            "has_snapshot": has_snapshot,
            "snapshot_id": raw_meta.get("snapshot_id"),
            "retention_tag_detected": retention_intent,
            "lookback_days_evaluated": lookback_days,
            "total_io_ops_in_period": total_io_ops,
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
