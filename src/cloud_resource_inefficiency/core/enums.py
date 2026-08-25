"""Enums for cloud providers, resource types, risk and confidence levels."""

from enum import Enum


class CloudProvider(str, Enum):
    """Supported cloud providers."""
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class ResourceType(str, Enum):
    """Supported cloud resource types."""
    # AWS
    AWS_EBS_VOLUME = "aws_ebs_volume"
    AWS_EC2_INSTANCE = "aws_ec2_instance"
    AWS_EIP = "aws_eip"
    AWS_RDS_INSTANCE = "aws_rds_instance"
    AWS_NAT_GATEWAY = "aws_nat_gateway"

    # Azure (extensible)
    AZURE_MANAGED_DISK = "azure_managed_disk"
    AZURE_VM = "azure_vm"
    AZURE_PUBLIC_IP = "azure_public_ip"

    # GCP (extensible)
    GCP_PERSISTENT_DISK = "gcp_persistent_disk"
    GCP_COMPUTE_INSTANCE = "gcp_compute_instance"
    GCP_STATIC_IP = "gcp_static_ip"


class InefficiencyCategory(str, Enum):
    """Categorization of financial inefficiency."""
    UNUSED_RESOURCE = "Unused Resource"
    IDLE_RESOURCE = "Idle Resource"
    OVERPROVISIONED = "Overprovisioned Resource"
    UNATTACHED_STORAGE = "Unattached Storage"
    LEGACY_GENERATION = "Legacy Generation"


class RiskLevel(str, Enum):
    """Risk assessment for performing the remediation."""
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ConfidenceLevel(str, Enum):
    """Confidence level of the detection."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
