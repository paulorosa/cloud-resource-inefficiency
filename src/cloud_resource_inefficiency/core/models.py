"""Core data models and Data Transfer Objects (DTOs)."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from .enums import CloudProvider, ConfidenceLevel, InefficiencyCategory, ResourceType, RiskLevel


@dataclass
class CloudResource:
    """Standardized representation of a cloud resource."""
    resource_id: str
    name: Optional[str]
    provider: CloudProvider
    resource_type: ResourceType
    region: str
    account_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    status: Optional[str] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def get_tag(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Convenience method to retrieve tag case-insensitively."""
        for k, v in self.tags.items():
            if k.lower() == key.lower():
                return v
        return default


@dataclass
class MetricSummary:
    """Summary of metric evaluations for a resource."""
    metric_name: str
    unit: str
    period_days: int
    total_value: float
    average_value: float
    maximum_value: float
    datapoint_count: int
    additional_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "unit": self.unit,
            "period_days": self.period_days,
            "total_value": self.total_value,
            "average_value": self.average_value,
            "maximum_value": self.maximum_value,
            "datapoint_count": self.datapoint_count,
            "additional_info": self.additional_info,
        }


@dataclass
class PricingDetails:
    """Details on calculated resource cost and unit rates."""
    monthly_cost: float
    currency: str = "USD"
    rate_source: str = "default_rates"
    unit_rates: Dict[str, float] = field(default_factory=dict)
    cost_breakdown: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "monthly_cost": round(self.monthly_cost, 4),
            "currency": self.currency,
            "rate_source": self.rate_source,
            "unit_rates": self.unit_rates,
            "cost_breakdown": {k: round(v, 4) for k, v in self.cost_breakdown.items()},
        }


@dataclass
class Opportunity:
    """Represents an identified financial efficiency opportunity."""
    rule_id: str
    title: str
    description: str
    category: InefficiencyCategory
    resource: CloudResource
    estimated_monthly_savings: float
    currency: str = "USD"
    confidence_level: ConfidenceLevel = ConfidenceLevel.HIGH
    risk_level: RiskLevel = RiskLevel.LOW
    pricing_details: Optional[PricingDetails] = None
    evaluated_metrics: Dict[str, MetricSummary] = field(default_factory=dict)
    recommended_actions: List[str] = field(default_factory=list)
    remediation_command: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    opportunity_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "rule_id": self.rule_id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "resource": {
                "resource_id": self.resource.resource_id,
                "name": self.resource.name,
                "provider": self.resource.provider.value,
                "resource_type": self.resource.resource_type.value,
                "region": self.resource.region,
                "account_id": self.resource.account_id,
                "status": self.resource.status,
                "tags": self.resource.tags,
            },
            "estimated_monthly_savings": round(self.estimated_monthly_savings, 2),
            "currency": self.currency,
            "confidence_level": self.confidence_level.value,
            "risk_level": self.risk_level.value,
            "pricing_details": self.pricing_details.to_dict() if self.pricing_details else None,
            "evaluated_metrics": {k: v.to_dict() for k, v in self.evaluated_metrics.items()},
            "recommended_actions": self.recommended_actions,
            "remediation_command": self.remediation_command,
            "metadata": self.metadata,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class ScanResult:
    """Aggregated scan results containing all detected opportunities."""
    opportunities: List[Opportunity] = field(default_factory=list)
    scanned_resources_count: int = 0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    errors: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def total_estimated_monthly_savings(self) -> float:
        """Returns total estimated monthly savings across all opportunities."""
        return sum(opp.estimated_monthly_savings for opp in self.opportunities)

    @property
    def opportunities_count(self) -> int:
        """Returns the number of detected opportunities."""
        return len(self.opportunities)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": {
                "total_opportunities": self.opportunities_count,
                "scanned_resources_count": self.scanned_resources_count,
                "total_estimated_monthly_savings": round(self.total_estimated_monthly_savings, 2),
                "currency": "USD",
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "errors_count": len(self.errors),
            },
            "opportunities": [opp.to_dict() for opp in self.opportunities],
            "errors": self.errors,
        }
