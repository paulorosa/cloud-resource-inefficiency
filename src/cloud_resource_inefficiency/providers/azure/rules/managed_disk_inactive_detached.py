"""Detection rule for inactive and detached Azure Managed Disks."""

from datetime import datetime, timedelta, timezone
import re
from typing import Any, Optional

from cloud_resource_inefficiency.core.enums import (
    CloudProvider, ConfidenceLevel, InefficiencyCategory, ResourceType, RiskLevel,
)
from cloud_resource_inefficiency.core.interfaces import BaseMetricsProvider, BasePricingProvider
from cloud_resource_inefficiency.core.models import CloudResource, Opportunity
from cloud_resource_inefficiency.core.rule import BaseInefficiencyRule


class InactiveDetachedManagedDiskRule(BaseInefficiencyRule):
    """Finds unattached Managed Disks with no recent read or write activity."""

    def __init__(self, lookback_days: int = 14, max_allowed_io_ops: float = 0.0) -> None:
        self._lookback_days = lookback_days
        self._max_allowed_io_ops = max_allowed_io_ops

    @property
    def rule_id(self) -> str:
        return "AZURE-MANAGED-DISK-001"

    @property
    def title(self) -> str:
        return "Inactive and Detached Managed Disk"

    @property
    def description(self) -> str:
        return "Managed Disks that are detached and have no recent read or write activity continue to incur storage costs."

    @property
    def category(self) -> InefficiencyCategory:
        return InefficiencyCategory.UNATTACHED_STORAGE

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.AZURE

    @property
    def target_resource_type(self) -> ResourceType:
        return ResourceType.AZURE_MANAGED_DISK

    def evaluate(
        self, resource: CloudResource, metrics_provider: BaseMetricsProvider,
        pricing_provider: BasePricingProvider, **kwargs: Any
    ) -> Optional[Opportunity]:
        if resource.resource_type != self.target_resource_type:
            return None
        metadata = resource.raw_metadata or {}
        if resource.status not in (None, "unattached") and metadata.get("is_attached", True):
            return None
        if metadata.get("is_attached", False) or metadata.get("managed_by"):
            return None

        lookback_days = kwargs.get("lookback_days", self._lookback_days)
        max_allowed_io = kwargs.get("max_allowed_io_ops", self._max_allowed_io_ops)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=lookback_days)
        read = metrics_provider.get_metric_summary(resource, "Disk Read Operations/Sec", start_time, end_time, "Sum")
        write = metrics_provider.get_metric_summary(resource, "Disk Write Operations/Sec", start_time, end_time, "Sum")
        if read.additional_info.get("status") == "ERROR" or write.additional_info.get("status") == "ERROR":
            return None
        total_io = read.total_value + write.total_value
        if total_io > max_allowed_io:
            return None

        pricing = pricing_provider.get_resource_pricing(resource)
        retention = any(
            term in f"{key} {value}".lower()
            for key, value in resource.tags.items()
            for term in ("donotdelete", "keep", "retain", "backup", "dr", "migration")
        )
        has_snapshot = bool(metadata.get("snapshot_id"))
        risk = RiskLevel.MEDIUM if retention else RiskLevel.LOW
        confidence = ConfidenceLevel.MEDIUM if retention else ConfidenceLevel.HIGH
        disk_id = resource.resource_id
        safe_id = disk_id if re.match(r"^/subscriptions/[0-9a-fA-F-]+/resourceGroups/[\w.-]+/providers/Microsoft.Compute/disks/[\w.-]+$", disk_id) else re.sub(r"[^\w./-]", "", disk_id)
        actions = [f"Confirm with the disk owner that '{safe_id}' is no longer required."]
        if not has_snapshot:
            actions.append(f"Create a recovery snapshot before deletion: 'az snapshot create --name <snapshot-name> --resource-group <resource-group> --source {safe_id}'")
        actions.append(f"Delete the detached disk to save approximately ${pricing.monthly_cost:.2f}/month: 'az disk delete --ids {safe_id} --yes'")
        return Opportunity(
            rule_id=self.rule_id, title=self.title, description=self.description,
            category=self.category, resource=resource, estimated_monthly_savings=pricing.monthly_cost,
            currency=pricing.currency, confidence_level=confidence, risk_level=risk,
            pricing_details=pricing, evaluated_metrics={"DiskReadOperations": read, "DiskWriteOperations": write},
            recommended_actions=actions, remediation_command=f"az disk delete --ids {safe_id} --yes",
            metadata={"sku": metadata.get("sku"), "size_gib": metadata.get("size_gib"), "has_snapshot": has_snapshot,
                      "retention_tag_detected": retention, "lookback_days_evaluated": lookback_days,
                      "total_io_ops_in_period": total_io},
        )