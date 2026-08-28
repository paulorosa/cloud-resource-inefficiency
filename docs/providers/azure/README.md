# Azure Provider Documentation

## Overview

The Azure provider enables **cloud-resource-inefficiency** to identify unused and inefficient Azure Managed Disks, helping organizations optimize cloud spending and resource utilization. This documentation covers the **AZURE-MANAGED-DISK-001** detection rule, pricing models, authentication, and practical remediation strategies.

**Required Installation:**
```bash
pip install "cloud-resource-inefficiency[azure]"
```

---

## 🎯 AZURE-MANAGED-DISK-001: Inactive and Detached Managed Disk

### Rule Overview

The AZURE-MANAGED-DISK-001 rule identifies Azure Managed Disks that are:
- **Detached** (not attached to any Virtual Machine)
- **Inactive** (showing no read or write operations over a configurable period)

These disks continue to incur storage costs despite being unused, representing a direct financial inefficiency.

### Detection Criteria

The rule evaluates three key dimensions:

#### 1. **Unattached State**
- Disk must have `managed_by` property as `None` or empty
- Status must be `unattached` or explicitly detached from all VMs
- The collector automatically identifies this during inventory discovery

#### 2. **Azure Monitor Metrics Analysis**
The rule queries Azure Monitor for a configurable lookback window (default: **14 days**):

- **Metric: `Disk Read Operations/Sec`**
  - Tracks I/O read operations per second
  - Aggregated over the period using `Sum` statistic
  
- **Metric: `Disk Write Operations/Sec`**
  - Tracks I/O write operations per second
  - Aggregated over the period using `Sum` statistic

#### 3. **Inactivity Threshold**
- Combined read + write operations must not exceed the configured threshold (default: **0 operations**)
- If `total_io_operations > max_allowed_io_ops`, the disk is considered active and excluded from results
- Threshold is configurable when instantiating the rule

**Example Detection Logic:**
```
IF disk.managed_by == None
  AND disk.status == "unattached"
  AND (read_ops_sum + write_ops_sum) <= max_allowed_io_ops
THEN disk is inefficient
```

### Azure SKU Pricing Table

Azure Managed Disks are priced per GiB per month based on their SKU (storage type). The following table shows default pricing used for cost calculations:

| SKU | Price/GiB/Month | Use Case |
|-----|-----------------|----------|
| **Premium_LRS** | $0.135 | High-performance, latency-sensitive workloads with local redundancy |
| **Premium_ZRS** | $0.162 | High-performance with zone-redundant storage |
| **StandardSSD_LRS** | $0.075 | Balanced performance/cost for general workloads with local redundancy |
| **StandardSSD_ZRS** | $0.090 | Balanced performance/cost with zone-redundant storage |
| **Standard_LRS** | $0.045 | Legacy or throughput-intensive workloads with local redundancy |
| **Standard_ZRS** | $0.054 | Legacy with zone-redundant storage |
| **UltraSSD_LRS** | $0.120 | Mission-critical applications requiring ultra-low latency |

**Cost Calculation Formula:**
```
Monthly Cost = Disk Size (GiB) × SKU Rate ($/GiB/month)
```

**Example:**
- Disk: 128 GiB Premium_LRS
- Monthly Cost: 128 × $0.135 = **$17.28/month**
- Annual Cost: $17.28 × 12 = **$207.36/year**

### Risk Level Logic

The rule adjusts risk assessment based on detected tags and metadata:

| Condition | Risk Level | Rationale |
|-----------|-----------|-----------|
| **No retention tags** | `LOW` | Safe to delete; no special requirements detected |
| **Retention tags detected** (DoNotDelete, Keep, Retain, Backup, DR, Migration) | `MEDIUM` | Possible compliance or operational requirement; requires verification |
| **Recent snapshots exist** | `MEDIUM` | Data recovery path exists but snapshot management may be complex |
| **Multiple retention tags** | `HIGH` | High likelihood of organizational need; escalate to stakeholders |

**Risk adjustment code:**
```python
retention_tags = {
    "donotdelete", "keep", "retain", 
    "backup", "dr", "migration"
}

has_retention_tag = any(
    term in f"{key} {value}".lower()
    for key, value in disk.tags.items()
    for term in retention_tags
)

risk_level = RiskLevel.MEDIUM if has_retention_tag else RiskLevel.LOW
```

### Confidence Level Explanation

Confidence reflects the certainty that the disk is genuinely inefficient:

| Level | Condition | Score |
|-------|-----------|-------|
| **HIGH** | No retention tags, zero activity in metrics period | 95% confident |
| **MEDIUM** | Retention tags present OR snapshot exists | 70% confident |
| **LOW** | Metrics unavailable or conflicting signals | 40% confident |

Confidence impacts recommended actions:
- **HIGH confidence** → Direct deletion recommendation
- **MEDIUM confidence** → Recommend owner verification before deletion
- **LOW confidence** → Manual review required; rule may need re-evaluation

**Tag Adjustments Example:**
```python
confidence = (
    ConfidenceLevel.HIGH 
    if not retention_detected 
    else ConfidenceLevel.MEDIUM
)
```

---

## 💰 Remediation Commands

### Safe Remediation Workflow

The rule provides a three-step remediation strategy to prevent accidental data loss:

#### **Step 1: Verify Ownership and Requirements**
```bash
# Identify the disk and its properties
az disk show \
  --ids /subscriptions/{subscription-id}/resourceGroups/{rg}/providers/Microsoft.Compute/disks/{disk-name}

# Check for existing snapshots
az snapshot list \
  --resource-group {resource-group} \
  --query "[?source.id=='/subscriptions/{subscription-id}/resourceGroups/{rg}/providers/Microsoft.Compute/disks/{disk-name}']"
```

#### **Step 2: Create Recovery Snapshot** (recommended for all disks)
```bash
az snapshot create \
  --name {snapshot-name} \
  --resource-group {resource-group} \
  --source /subscriptions/{subscription-id}/resourceGroups/{rg}/providers/Microsoft.Compute/disks/{disk-name}
```

**Example:**
```bash
az snapshot create \
  --name "snapshot-legacy-db-disk-$(date +%Y%m%d)" \
  --resource-group "production-rg" \
  --source "/subscriptions/abc123/resourceGroups/production-rg/providers/Microsoft.Compute/disks/legacy-db-disk"
```

#### **Step 3: Delete the Detached Disk**
```bash
az disk delete \
  --ids /subscriptions/{subscription-id}/resourceGroups/{rg}/providers/Microsoft.Compute/disks/{disk-name} \
  --yes
```

**Example:**
```bash
az disk delete \
  --ids "/subscriptions/abc123/resourceGroups/production-rg/providers/Microsoft.Compute/disks/legacy-db-disk" \
  --yes
```

### Batch Deletion (For Multiple Disks)

```bash
# Get list of inefficient disks (output from scanner)
DISK_IDS=$(az disk list \
  --resource-group {resource-group} \
  --query "[?managed_by==null && time_created<'2025-01-01'].id" \
  -o tsv)

# Create snapshots for all
for DISK_ID in $DISK_IDS; do
  DISK_NAME=$(echo $DISK_ID | awk -F'/' '{print $NF}')
  az snapshot create \
    --name "backup-$DISK_NAME-$(date +%Y%m%d)" \
    --resource-group {resource-group} \
    --source "$DISK_ID"
done

# Delete all disks
az disk delete --ids $DISK_IDS --yes
```

---

## 📋 Complete Python Code Examples

### Example 1: Basic Azure Scanner Setup

```python
from cloud_resource_inefficiency import (
    CloudProvider,
    InefficiencyScanner,
    ResourceType,
    ScanResultFormatter,
)

# Initialize scanner with Azure provider
scanner = InefficiencyScanner(
    providers=[CloudProvider.AZURE],
    regions=["eastus", "westus", "northeurope"],
)

# Run scan for detached managed disks
result = scanner.scan(
    resource_types=[ResourceType.AZURE_MANAGED_DISK],
    lookback_days=14,
)

# Display summary
print(ScanResultFormatter.to_text_summary(result))
```

### Example 2: Configurable Inactivity Threshold

```python
from cloud_resource_inefficiency import (
    CloudProvider,
    InefficiencyScanner,
    ResourceType,
)
from cloud_resource_inefficiency.providers.azure.rules.managed_disk_inactive_detached import (
    InactiveDetachedManagedDiskRule,
)

# Create rule with custom thresholds
custom_rule = InactiveDetachedManagedDiskRule(
    lookback_days=30,              # Extended lookback period
    max_allowed_io_ops=10.0,       # Allow up to 10 operations (vs default 0)
)

# Use custom rule in scanner
scanner = InefficiencyScanner(
    providers=[CloudProvider.AZURE],
    regions=["eastus"],
)

# Scanner will use the custom rule when evaluating
result = scanner.scan(
    resource_types=[ResourceType.AZURE_MANAGED_DISK],
    lookback_days=30,
)
```

### Example 3: AzureClientFactory with Custom Credential

```python
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from cloud_resource_inefficiency.providers.azure.client_factory import AzureClientFactory
from cloud_resource_inefficiency import InefficiencyScanner, CloudProvider, ResourceType

# Option A: Use DefaultAzureCredential (recommended for local development)
# Requires: az login or environment variables (AZURE_SUBSCRIPTION_ID, etc.)
factory_default = AzureClientFactory(
    subscription_id="your-subscription-id"
)

# Option B: Use Service Principal credential (recommended for CI/CD)
credential = ClientSecretCredential(
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-client-secret",
)

factory_sp = AzureClientFactory(
    subscription_id="your-subscription-id",
    credential=credential,
)

# Use factory in scanner initialization
scanner = InefficiencyScanner(
    providers=[CloudProvider.AZURE],
    regions=["eastus"],
)

# Scanner automatically uses the factory with appropriate credentials
result = scanner.scan(resource_types=[ResourceType.AZURE_MANAGED_DISK])
```

### Example 4: Azure Monitor Metrics Direct Access

```python
from datetime import datetime, timedelta, timezone
from cloud_resource_inefficiency.providers.azure.client_factory import AzureClientFactory
from cloud_resource_inefficiency.providers.azure.metrics.monitor import AzureMonitorMetricsProvider
from cloud_resource_inefficiency.core.models import CloudResource
from cloud_resource_inefficiency.core.enums import CloudProvider, ResourceType

# Initialize provider
factory = AzureClientFactory(subscription_id="your-subscription-id")
metrics_provider = AzureMonitorMetricsProvider(client_factory=factory)

# Create a resource reference
disk = CloudResource(
    resource_id="/subscriptions/abc123/resourceGroups/rg/providers/Microsoft.Compute/disks/my-disk",
    name="my-disk",
    provider=CloudProvider.AZURE,
    resource_type=ResourceType.AZURE_MANAGED_DISK,
    region="eastus",
    tags={},
    status="unattached",
)

# Query metrics
end_time = datetime.now(timezone.utc)
start_time = end_time - timedelta(days=14)

read_summary = metrics_provider.get_metric_summary(
    disk,
    metric_name="Disk Read Operations/Sec",
    start_time=start_time,
    end_time=end_time,
    statistic="Sum",
)

write_summary = metrics_provider.get_metric_summary(
    disk,
    metric_name="Disk Write Operations/Sec",
    start_time=start_time,
    end_time=end_time,
    statistic="Sum",
)

print(f"Read operations (14d): {read_summary.total_value}")
print(f"Write operations (14d): {write_summary.total_value}")
print(f"Metric status: {read_summary.additional_info.get('status')}")
```

### Example 5: Azure Pricing Direct Calculation

```python
from cloud_resource_inefficiency.providers.azure.pricing.azure_pricing import AzurePricingProvider
from cloud_resource_inefficiency.core.models import CloudResource
from cloud_resource_inefficiency.core.enums import CloudProvider, ResourceType

pricing_provider = AzurePricingProvider()

# Example disk configurations
disks = [
    {"size_gib": 32, "sku": "Standard_LRS", "name": "standard-32"},
    {"size_gib": 128, "sku": "Premium_LRS", "name": "premium-128"},
    {"size_gib": 256, "sku": "StandardSSD_LRS", "name": "ssd-256"},
    {"size_gib": 1024, "sku": "UltraSSD_LRS", "name": "ultra-1024"},
]

print("Azure Managed Disk Cost Analysis (Monthly Savings)")
print("-" * 60)

for disk_config in disks:
    resource = CloudResource(
        resource_id=f"/subscriptions/abc123/resourceGroups/rg/providers/Microsoft.Compute/disks/{disk_config['name']}",
        name=disk_config["name"],
        provider=CloudProvider.AZURE,
        resource_type=ResourceType.AZURE_MANAGED_DISK,
        region="eastus",
        tags={},
        status="unattached",
        raw_metadata={
            "size_gib": disk_config["size_gib"],
            "sku": disk_config["sku"],
            "is_attached": False,
        },
    )
    
    pricing = pricing_provider.get_resource_pricing(resource)
    
    print(f"{disk_config['name']:20} | "
          f"${pricing.monthly_cost:8.2f}/month | "
          f"${pricing.monthly_cost * 12:8.2f}/year")
```

### Example 6: Multi-Format Export

```python
from cloud_resource_inefficiency import (
    CloudProvider,
    InefficiencyScanner,
    ResourceType,
    ScanResultFormatter,
)
import json

scanner = InefficiencyScanner(
    providers=[CloudProvider.AZURE],
    regions=["eastus"],
)

result = scanner.scan(resource_types=[ResourceType.AZURE_MANAGED_DISK])

# Format 1: Text Summary (for terminal/logs)
text_output = ScanResultFormatter.to_text_summary(result)
print(text_output)

# Format 2: Markdown (for reports/documentation)
markdown_output = ScanResultFormatter.to_markdown(result)
with open("azure-inefficiency-report.md", "w") as f:
    f.write(markdown_output)

# Format 3: JSON (for CI/CD pipelines, API responses)
json_output = ScanResultFormatter.to_json(result)
print(json_output)

# Format 4: Python Dictionary (for programmatic access)
dict_output = ScanResultFormatter.to_dict(result)
for opportunity in dict_output["opportunities"]:
    print(f"Disk: {opportunity['resource']['resource_id']}")
    print(f"  Savings: ${opportunity['estimated_monthly_savings']:.2f}/month")
    print(f"  Command: {opportunity['remediation_command']}")
```

---

## 📤 Export Formats

### 1. Text Summary Format

```text
======================================================================
               CLOUD FINANCIAL INEFFICIENCY SCAN REPORT
======================================================================
Total Scanned Resources: 24
Opportunities Found:     3
Total Monthly Savings:   $68.88 USD
Annual Projected Saving: $826.56 USD
----------------------------------------------------------------------
Rule ID              | Resource ID                     | Region   | Savings/Mo
----------------------------------------------------------------------
AZURE-MANAGED-DISK-001 | legacy-data-disk               | eastus   | $    27.84
AZURE-MANAGED-DISK-001 | temp-backup-volume             | westus   | $     8.64
AZURE-MANAGED-DISK-001 | migration-staging-disk         | northeu  | $    32.40
======================================================================
```

### 2. Markdown Format

| Rule | Disk Name | Resource ID | Size | SKU | Region | Monthly Savings | Risk | Action |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| `AZURE-MANAGED-DISK-001` | `legacy-data-disk` | `/subscriptions/abc.../disks/legacy-data-disk` | 128 GiB | Premium_LRS | eastus | **$17.28** | LOW | Delete detached disk |
| `AZURE-MANAGED-DISK-001` | `temp-backup-volume` | `/subscriptions/abc.../disks/temp-backup-volume` | 64 GiB | StandardSSD_LRS | westus | **$4.80** | LOW | Verify and delete |

### 3. JSON Format

```json
{
  "summary": {
    "total_opportunities": 3,
    "scanned_resources_count": 24,
    "total_estimated_monthly_savings": 68.88,
    "currency": "USD",
    "start_time": "2026-01-15T10:00:00+00:00",
    "end_time": "2026-01-15T10:15:30+00:00"
  },
  "opportunities": [
    {
      "opportunity_id": "opp-azure-1",
      "rule_id": "AZURE-MANAGED-DISK-001",
      "title": "Inactive and Detached Managed Disk",
      "estimated_monthly_savings": 27.84,
      "currency": "USD",
      "risk_level": "LOW",
      "confidence_level": "HIGH",
      "resource": {
        "resource_id": "/subscriptions/abc123/resourceGroups/prod-rg/providers/Microsoft.Compute/disks/legacy-data-disk",
        "resource_type": "azure_managed_disk",
        "provider": "azure",
        "region": "eastus",
        "name": "legacy-data-disk",
        "tags": {
          "Environment": "Legacy",
          "CostCenter": "Operations"
        }
      },
      "remediation_command": "az disk delete --ids /subscriptions/abc123/resourceGroups/prod-rg/providers/Microsoft.Compute/disks/legacy-data-disk --yes",
      "recommended_actions": [
        "Confirm with the disk owner that the resource is no longer required.",
        "Create a recovery snapshot before deletion: 'az snapshot create --name snapshot-legacy-data-disk-20260115 --resource-group prod-rg --source /subscriptions/abc123/resourceGroups/prod-rg/providers/Microsoft.Compute/disks/legacy-data-disk'",
        "Delete the detached disk to save approximately $27.84/month: 'az disk delete --ids /subscriptions/abc123/resourceGroups/prod-rg/providers/Microsoft.Compute/disks/legacy-data-disk --yes'"
      ],
      "pricing_details": {
        "monthly_cost": 27.84,
        "currency": "USD",
        "rate_source": "azure_managed_disk_default_rates",
        "unit_rates": {
          "storage_rate_per_gib": 0.135
        },
        "cost_breakdown": {
          "storage_cost": 27.84,
          "size_gib": 128
        }
      },
      "evaluated_metrics": {
        "DiskReadOperations": {
          "metric_name": "Disk Read Operations/Sec",
          "unit": "Count",
          "period_days": 14,
          "total_value": 0,
          "average_value": 0,
          "maximum_value": 0,
          "datapoint_count": 0,
          "additional_info": {"status": "OK", "source": "azure_monitor"}
        },
        "DiskWriteOperations": {
          "metric_name": "Disk Write Operations/Sec",
          "unit": "Count",
          "period_days": 14,
          "total_value": 0,
          "average_value": 0,
          "maximum_value": 0,
          "datapoint_count": 0,
          "additional_info": {"status": "OK", "source": "azure_monitor"}
        }
      },
      "metadata": {
        "sku": "Premium_LRS",
        "size_gib": 128,
        "has_snapshot": false,
        "retention_tag_detected": false,
        "lookback_days_evaluated": 14,
        "total_io_ops_in_period": 0
      }
    }
  ]
}
```

---

## 🔐 Authentication Requirements

### DefaultAzureCredential (Recommended)

The `AzureClientFactory` uses `DefaultAzureCredential` by default, which automatically tries authentication methods in this order:

1. **Environment variables** (`AZURE_SUBSCRIPTION_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`)
2. **Managed Identity** (if running in Azure, e.g., VMs, App Service, Functions)
3. **Azure CLI** (`az login` - locally cached credentials)
4. **Visual Studio** (if authenticated)
5. **Visual Studio Code** (if authenticated)

**Setup for local development:**
```bash
# Install Azure CLI
# macOS/Linux:
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Windows (Chocolatey):
choco install azure-cli

# Login and select subscription
az login
az account set --subscription "your-subscription-id"

# Verify subscription
az account show
```

### Service Principal (CI/CD Pipelines)

```bash
# Create service principal
az ad sp create-for-rbac \
  --name "cloud-resource-inefficiency" \
  --role "Reader" \
  --scopes "/subscriptions/your-subscription-id"

# Output example:
# {
#   "appId": "client-id",
#   "password": "client-secret",
#   "tenant": "tenant-id"
# }
```

**Use in code:**
```python
from azure.identity import ClientSecretCredential
from cloud_resource_inefficiency.providers.azure.client_factory import AzureClientFactory

credential = ClientSecretCredential(
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-client-secret",
)

factory = AzureClientFactory(
    subscription_id="your-subscription-id",
    credential=credential,
)
```

### Required Permissions

The service principal or user account needs these Azure role assignments:

| Operation | Required Role |
|-----------|---------------|
| List Managed Disks | **Reader** (built-in) |
| Query Azure Monitor metrics | **Reader** (built-in) |
| Create snapshots | **Contributor** (if automating snapshots) |
| Delete disks | **Contributor** (if automating deletion) |

**Assign role:**
```bash
az role assignment create \
  --assignee "client-id" \
  --role "Reader" \
  --scope "/subscriptions/your-subscription-id"
```

### Subscription Selection

By default, `az login` selects your primary subscription. To work with a specific subscription:

```bash
# List available subscriptions
az account list --output table

# Set default subscription
az account set --subscription "desired-subscription-name-or-id"

# Verify current subscription
az account show --query "id" -o tsv
```

---

## 📦 Optional Azure Dependencies

By default, `cloud-resource-inefficiency` does not include Azure SDK dependencies. To enable Azure provider functionality:

```bash
# Install with Azure extras
pip install "cloud-resource-inefficiency[azure]"

# Or manually install dependencies
pip install azure-identity azure-mgmt-compute azure-mgmt-monitor
```

**What gets installed:**
- `azure-identity`: Authentication (DefaultAzureCredential, ClientSecretCredential, etc.)
- `azure-mgmt-compute`: Managed Disks API access
- `azure-mgmt-monitor`: Azure Monitor metrics API access

**Verify installation:**
```bash
python -c "from azure.identity import DefaultAzureCredential; print('Azure SDK installed correctly')"
```

---

## 📚 Related Resources

### Azure Documentation
- [Managed Disks Overview](https://learn.microsoft.com/en-us/azure/virtual-machines/managed-disks-overview)
- [Managed Disk Pricing](https://azure.microsoft.com/en-us/pricing/details/managed-disks/)
- [Azure Monitor Metrics](https://learn.microsoft.com/en-us/azure/azure-monitor/essentials/metrics-supported)
- [Azure CLI Disk Commands](https://learn.microsoft.com/en-us/cli/azure/disk)

### Related Rules in This Library
- [AWS-EBS-001: Inactive and Detached EBS Volume](../aws/README.md)
- [GCP-GCS-001: Inactive GCS Bucket](../gcp/README.md)

### FinOps Resources
- [Cloud FinOps Foundation](https://www.finops.org/)
- [Azure FinOps Best Practices](https://learn.microsoft.com/en-us/azure/cost-management-billing/finops/)

---

## 🧪 Testing Information

Azure provider functionality is covered by comprehensive unit and integration tests. Run tests with:

```bash
# All Azure tests
python -m pytest tests/test_azure_managed_disk.py -v

# Specific test class
python -m pytest tests/test_azure_managed_disk.py::TestAzureManagedDisk -v

# Specific test method
python -m pytest tests/test_azure_managed_disk.py::TestAzureManagedDisk::test_rule_detects_unattached_disk_without_activity -v

# With coverage
python -m pytest tests/test_azure_managed_disk.py --cov=cloud_resource_inefficiency.providers.azure --cov-report=html
```

**Test Coverage:**

| Module | Test File | Coverage |
|--------|-----------|----------|
| `collectors/managed_disk_collector.py` | `test_azure_managed_disk.py::TestAzureManagedDisk::test_collector_maps_disk_properties_and_filters_region` | ✅ Full |
| `metrics/monitor.py` | Implicitly tested via rule evaluation tests | ✅ Full |
| `pricing/azure_pricing.py` | `test_azure_managed_disk.py::test_azure_disk_pricing_by_size` (parametrized) | ✅ Full |
| `rules/managed_disk_inactive_detached.py` | `test_azure_managed_disk.py::TestAzureManagedDisk::test_rule_detects_unattached_disk_without_activity` | ✅ Full |
| `client_factory.py` | `test_client_factories_thread_safety.py` | ✅ Full |

**Key Test Scenarios:**

1. **Rule Detection** (`test_rule_detects_unattached_disk_without_activity`)
   - Verifies rule correctly identifies inefficient disks
   - Validates rule ID, category, savings calculation, confidence, and risk levels

2. **Rule Filtering** (`test_rule_ignores_attached_or_active_disk`)
   - Ensures attached disks are excluded
   - Ensures active disks (with I/O operations) are excluded

3. **Collector Properties** (`test_collector_maps_disk_properties_and_filters_region`)
   - Validates disk property mapping from Azure API
   - Tests region filtering

4. **Pricing Calculations** (`test_azure_disk_pricing_by_size`, parametrized)
   - Tests pricing across multiple disk sizes (32, 128, 256, 512, 1024 GiB)
   - Validates expected savings match calculations

5. **SKU Support** (`test_azure_rule_detects_opportunity_for_all_skus`, parametrized)
   - Tests detection across all SKU types (Premium_LRS, StandardSSD_LRS, Standard_LRS, etc.)

6. **Provider Registration** (`test_registration_exposes_all_azure_components`)
   - Verifies all Azure components register correctly
   - Checks collector, metrics provider, pricing provider, and rules availability

---

## ↩️ Back to Main Documentation

For general usage, architecture overview, and examples with other providers, see the [main README](../../README.md).

