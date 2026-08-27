# Google Cloud Platform (GCP) Provider Documentation

## Overview

The GCP provider detects inefficient cloud storage resources in Google Cloud Storage (GCS) and provides actionable recommendations for cost optimization. The provider integrates with Google Cloud Logging and Cloud Monitoring to identify unused buckets and calculate accurate pricing based on storage class and data volume.

**[← Back to Main README](../../README.md)**

---

## GCP-GCS-001: Inactive GCS Bucket

### Rule Description

**Title:** Inactive GCS Bucket

**Rule ID:** `GCP-GCS-001`

**Category:** Unused Resource

GCS buckets often persist after applications are retired or data is no longer in active use. Without access activity or when empty, these buckets incur unnecessary storage charges. Inactive buckets should be deleted to eliminate ongoing costs.

### Detection Criteria

The GCP-GCS-001 rule identifies GCS buckets as inefficient based on the following criteria:

#### 1. **Bucket State Analysis**
- **Empty Buckets**: Buckets with 0 bytes of stored data
- **Inactive Buckets**: Buckets with zero access operations during the lookback period

#### 2. **Cloud Logging Integration**
The rule queries Google Cloud Logging to analyze bucket access activity:
- Retrieves audit logs for `protoPayload.resourceName` matching the bucket
- Counts total GCS operations (reads, writes, deletes) during the lookback window
- Default lookback period: **30 days** (configurable)
- Operation threshold: **0 operations** = inactive

#### 3. **Storage Class Analysis**
- Identifies the storage class (Standard, Nearline, Coldline, Archive)
- Used for accurate cost calculation
- Determines pricing rates per GB

#### 4. **Size Calculation**
- Measures bucket size in bytes by summing all blob sizes
- Converts to GiB and GB for reporting
- Distinguishes empty buckets from inactive but non-empty buckets

### Risk Level Logic

Risk levels are assigned based on bucket state and data presence:

| Scenario | Risk Level | Rationale |
|----------|-----------|-----------|
| Empty bucket (0 bytes) | **VERY_LOW** | Minimal data loss risk; cost impact is small metadata overhead |
| Inactive bucket (0 operations, size > 0) | **LOW** | Data loss risk exists; requires confirmation before deletion |
| Active bucket | **N/A** | Not flagged as inefficient |

### Confidence Level Explanation

Confidence reflects the reliability of the data used for decision-making:

| Data Source | Confidence | Notes |
|------------|-----------|-------|
| Cloud Logging data available | **HIGH** | Audit logs provide definitive proof of inactivity |
| Cloud Logging data unavailable | **MEDIUM** | Bucket metadata used; cannot confirm access patterns |
| Empty buckets | **HIGH** | Bucket size is authoritative; no ambiguity |

---

## GCS Pricing Information

### Standard Pricing Table

Pricing varies by storage class. The following table shows **monthly rates per GB** for data stored in GCS:

| Storage Class | Monthly Rate (USD/GB) | Access Speed | Best For |
|--------------|---------------------|--------------|----------|
| **Standard** | $0.020 | Immediate | Hot data, frequently accessed |
| **Nearline** | $0.010 | Within hours | Warm data, occasional access |
| **Coldline** | $0.004 | Within 24 hours | Cool data, rare access |
| **Archive** | $0.0036 | Within 12 hours | Cold data, long-term retention |

### Empty Bucket Metadata Overhead

Even empty buckets incur a monthly **metadata cost of $0.50 USD** to maintain bucket infrastructure and audit logs.

### Pricing Calculation Method

```
For empty buckets:
  Monthly Cost = $0.50 (metadata overhead)

For non-empty buckets:
  Monthly Cost = (Size in GB) × (Rate per GB for storage class)
  
Example (100 GB Standard):
  Monthly Cost = 100 GB × $0.020/GB = $2.00 USD
```

### Cost Breakdown

The pricing provider generates detailed breakdowns:
- **Storage cost**: Data storage charges
- **Metadata overhead**: Empty bucket infrastructure cost
- **Size (GB)**: Calculated from stored data
- **Storage class rate**: Per-GB monthly rate

---

## Complete Code Examples

### Example 1: Basic GCS Bucket Scanning

```python
from cloud_resource_inefficiency import (
    CloudProvider,
    InefficiencyScanner,
    ResourceType,
    ScanResultFormatter,
)

def main():
    print("Initializing Cloud Inefficiency Scanner for GCP...")
    
    # Initialize scanner for GCP
    scanner = InefficiencyScanner(
        providers=[CloudProvider.GCP],
        regions=["us-central1"],  # GCS is regional but buckets are global
    )

    print("Running scan for inactive GCS buckets...")
    
    # Execute scan with 30-day lookback
    result = scanner.scan(
        resource_types=[ResourceType.GCP_GCS_BUCKET],
        lookback_days=30,
    )

    # Display plain-text summary
    print(ScanResultFormatter.to_text_summary(result))

if __name__ == "__main__":
    main()
```

### Example 2: GCSCollector - Direct Bucket Collection

```python
from cloud_resource_inefficiency.providers.gcp.collectors import GCSCollector
from cloud_resource_inefficiency.providers.gcp.client_factory import GCPClientFactory

def collect_buckets():
    """Collect all GCS buckets in the project."""
    # Initialize client factory (uses Application Default Credentials)
    client_factory = GCPClientFactory(project_id="my-gcp-project")
    
    # Create collector
    collector = GCSCollector(client_factory=client_factory)
    
    # Collect buckets (region is ignored for GCS)
    buckets = collector.collect(region="global")
    
    for bucket in buckets:
        print(f"Bucket: {bucket.resource_id}")
        print(f"  Location: {bucket.raw_metadata.get('location')}")
        print(f"  Storage Class: {bucket.raw_metadata.get('storage_class')}")
        print(f"  Size (GiB): {bucket.raw_metadata.get('size_gib')}")
        print(f"  Versioning: {bucket.raw_metadata.get('versioning_enabled')}")
        print()

if __name__ == "__main__":
    collect_buckets()
```

### Example 3: Cloud Logging Metrics Analysis

```python
from datetime import datetime, timedelta, timezone
from cloud_resource_inefficiency.providers.gcp.metrics import GCPMonitoringMetricsProvider
from cloud_resource_inefficiency.core.models import CloudResource
from cloud_resource_inefficiency.core.enums import CloudProvider, ResourceType

def analyze_bucket_activity():
    """Analyze GCS bucket access activity using Cloud Logging."""
    
    # Initialize metrics provider
    metrics_provider = GCPMonitoringMetricsProvider()
    
    # Create a sample bucket resource
    bucket_resource = CloudResource(
        resource_id="my-test-bucket",
        name="my-test-bucket",
        provider=CloudProvider.GCP,
        resource_type=ResourceType.GCP_GCS_BUCKET,
        region="global",
        account_id="1234567890",
        tags={},
        created_at=datetime.now(timezone.utc),
        status="active",
        raw_metadata={
            "location": "us-central1",
            "storage_class": "Standard",
            "size_bytes": 1073741824,  # 1 GiB
        },
    )
    
    # Query metrics for last 30 days
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=30)
    
    access_metric = metrics_provider.get_metric_summary(
        resource=bucket_resource,
        metric_name="access_count",
        start_time=start_time,
        end_time=end_time,
        statistic="Sum",
    )
    
    print(f"Bucket: {bucket_resource.resource_id}")
    print(f"Period: {access_metric.period_days} days")
    print(f"Total Operations: {access_metric.total_value}")
    print(f"Average Daily Operations: {access_metric.average_value:.2f}")
    print(f"Source: {access_metric.additional_info.get('source')}")
    
    if access_metric.total_value == 0:
        print("Result: INACTIVE - No access operations detected")
    else:
        print(f"Result: ACTIVE - {int(access_metric.total_value)} operations")

if __name__ == "__main__":
    analyze_bucket_activity()
```

### Example 4: GCP Pricing Calculation

```python
from cloud_resource_inefficiency.providers.gcp.pricing import GCPPricingProvider
from cloud_resource_inefficiency.core.models import CloudResource
from cloud_resource_inefficiency.core.enums import CloudProvider, ResourceType
from datetime import datetime, timezone

def calculate_bucket_costs():
    """Calculate monthly costs for different bucket scenarios."""
    
    pricing_provider = GCPPricingProvider()
    
    # Scenario 1: Empty bucket
    empty_bucket = CloudResource(
        resource_id="empty-bucket",
        name="empty-bucket",
        provider=CloudProvider.GCP,
        resource_type=ResourceType.GCP_GCS_BUCKET,
        region="global",
        account_id="1234567890",
        tags={},
        created_at=datetime.now(timezone.utc),
        status="active",
        raw_metadata={
            "location": "us-central1",
            "storage_class": "Standard",
            "size_bytes": 0,
        },
    )
    
    empty_pricing = pricing_provider.get_resource_pricing(empty_bucket)
    print(f"Empty Bucket Cost: ${empty_pricing.monthly_cost} {empty_pricing.currency}/month")
    print(f"  Breakdown: {empty_pricing.cost_breakdown}")
    print()
    
    # Scenario 2: 100 GB Standard storage
    standard_bucket = CloudResource(
        resource_id="standard-bucket",
        name="standard-bucket",
        provider=CloudProvider.GCP,
        resource_type=ResourceType.GCP_GCS_BUCKET,
        region="global",
        account_id="1234567890",
        tags={},
        created_at=datetime.now(timezone.utc),
        status="active",
        raw_metadata={
            "location": "us-central1",
            "storage_class": "Standard",
            "size_bytes": 107374182400,  # 100 GB
        },
    )
    
    standard_pricing = pricing_provider.get_resource_pricing(standard_bucket)
    print(f"Standard 100GB Cost: ${standard_pricing.monthly_cost} {standard_pricing.currency}/month")
    print(f"  Breakdown: {standard_pricing.cost_breakdown}")
    print()
    
    # Scenario 3: 500 GB Archive storage
    archive_bucket = CloudResource(
        resource_id="archive-bucket",
        name="archive-bucket",
        provider=CloudProvider.GCP,
        resource_type=ResourceType.GCP_GCS_BUCKET,
        region="global",
        account_id="1234567890",
        tags={},
        created_at=datetime.now(timezone.utc),
        status="active",
        raw_metadata={
            "location": "us-central1",
            "storage_class": "Archive",
            "size_bytes": 536870912000,  # 500 GB
        },
    )
    
    archive_pricing = pricing_provider.get_resource_pricing(archive_bucket)
    print(f"Archive 500GB Cost: ${archive_pricing.monthly_cost} {archive_pricing.currency}/month")
    print(f"  Breakdown: {archive_pricing.cost_breakdown}")

if __name__ == "__main__":
    calculate_bucket_costs()
```

---

## Example Output Samples

### Text Format Output

```
Cloud Resource Inefficiency Scanner Report
===========================================

Provider: GCP
Scan Duration: 2024-01-15 10:30:00 UTC - 2024-01-15 10:35:30 UTC
Total Opportunities Found: 3
Total Estimated Monthly Savings: $127.50 USD

Opportunities:
--------------

1. Inactive GCS Bucket
   Rule ID: GCP-GCS-001
   Resource: dev-backup-bucket
   Location: us-central1
   Storage Class: Standard
   Size: 45.5 GiB (48,860 MB)
   Status: Inactive (0 operations in last 30 days)
   Estimated Monthly Savings: $45.50 USD
   Confidence: HIGH | Risk Level: LOW
   Recommended Actions:
     - Bucket has no access activity in the past 30 days.
     - Confirm with bucket owner if data is still required.
     - Delete the unused bucket to save $45.50/month.
   Remediation: gsutil -m rm -r gs://dev-backup-bucket

2. Empty GCS Bucket
   Rule ID: GCP-GCS-001
   Resource: test-bucket-legacy
   Location: us-east1
   Storage Class: Standard
   Size: 0 B (Empty)
   Status: Empty bucket
   Estimated Monthly Savings: $0.50 USD
   Confidence: HIGH | Risk Level: VERY_LOW
   Recommended Actions:
     - Bucket is empty and incurring storage metadata costs.
     - Delete the bucket immediately.
   Remediation: gsutil -m rm -r gs://test-bucket-legacy
```

### Markdown Format Output

| Rule | Resource | Location | Size | Operations (30d) | Monthly Savings | Risk | Action |
|------|----------|----------|------|------------------|-----------------|------|--------|
| GCP-GCS-001 | dev-backup-bucket | us-central1 | 45.5 GiB | 0 | $45.50 | LOW | Delete |
| GCP-GCS-001 | test-bucket-legacy | us-east1 | 0 B | 0 | $0.50 | VERY_LOW | Delete |
| GCP-GCS-001 | archive-old-data | europe-west1 | 256.0 GiB | 0 | $1.84 | LOW | Delete |

### JSON Format Output

```json
{
  "scan_summary": {
    "provider": "GCP",
    "timestamp": "2024-01-15T10:30:00Z",
    "total_opportunities": 3,
    "total_monthly_savings": 127.50,
    "currency": "USD"
  },
  "opportunities": [
    {
      "opportunity_id": "opp-gcp-gcs-001-abc123",
      "rule_id": "GCP-GCS-001",
      "resource_id": "dev-backup-bucket",
      "resource_type": "GCP_GCS_BUCKET",
      "provider": "GCP",
      "region": "us-central1",
      "estimated_monthly_savings": 45.50,
      "confidence_level": "HIGH",
      "risk_level": "LOW",
      "metadata": {
        "storage_class": "Standard",
        "size_bytes": 48860000000,
        "size_gib": 45.5,
        "is_inactive": true,
        "is_empty": false,
        "total_access_operations": 0,
        "lookback_days_evaluated": 30
      },
      "remediation_command": "gsutil -m rm -r gs://dev-backup-bucket",
      "recommended_actions": [
        "Bucket has no access activity in the past 30 days.",
        "Confirm with bucket owner if data is still required.",
        "Delete the unused bucket to save $45.50/month."
      ]
    }
  ]
}
```

---

## Authentication & Setup

### Prerequisites

- GCP project with active billing
- Appropriate IAM permissions
- Google Cloud CLI installed and configured

### Google Cloud SDK Installation

```bash
# Install gcloud SDK
curl https://sdk.cloud.google.com | bash

# Initialize and authenticate
gcloud init

# Set default project
gcloud config set project PROJECT_ID

# Authenticate application
gcloud auth application-default login
```

### Application Default Credentials (ADC)

The GCP provider uses **Application Default Credentials** for authentication:

```python
from cloud_resource_inefficiency.providers.gcp.client_factory import GCPClientFactory

# ADC automatically discovers credentials from:
# 1. GOOGLE_APPLICATION_CREDENTIALS environment variable (service account JSON)
# 2. gcloud CLI cached credentials (~/.config/gcloud/application_default_credentials.json)
# 3. Compute Engine, Cloud Run, or App Engine metadata service

factory = GCPClientFactory()  # Uses ADC automatically
```

### Required IAM Permissions

Grant the following roles to your service account or user:

```yaml
Minimum Permissions:
  - storage.buckets.list
  - storage.buckets.get
  - logging.logEntries.list
  - monitoring.timeSeries.list

Recommended Roles:
  - roles/storage.objectViewer
  - roles/logging.viewer
  - roles/monitoring.viewer
```

### Service Account Setup (Recommended for CI/CD)

```bash
# Create service account
gcloud iam service-accounts create cloud-resource-inefficiency \
  --display-name="Cloud Resource Inefficiency Scanner"

# Grant permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:cloud-resource-inefficiency@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

# Create and download key
gcloud iam service-accounts keys create key.json \
  --iam-account=cloud-resource-inefficiency@PROJECT_ID.iam.gserviceaccount.com

# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/key.json
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `PermissionDenied: 403 Forbidden` | Check IAM roles; ensure service account has required permissions |
| `DefaultCredentialsError` | Run `gcloud auth application-default login` |
| `Project not set` | Set project with `gcloud config set project PROJECT_ID` |
| `No Cloud Logging entries found` | Ensure Cloud Logging is enabled and has been collecting data |

---

## Testing & Validation

### Running GCP Tests

The project includes comprehensive tests for the GCP provider:

```bash
# Run all GCP tests
pytest tests/test_gcp_gcs.py -v

# Run specific test
pytest tests/test_gcp_gcs.py::test_inactive_bucket_detection -v

# Run with coverage
pytest tests/test_gcp_gcs.py --cov=src/cloud_resource_inefficiency/providers/gcp
```

### Test Coverage

**Test File:** `tests/test_gcp_gcs.py`

| Component | Tests |
|-----------|-------|
| GCSCollector | Bucket listing, metadata extraction, error handling |
| GCPMonitoringMetricsProvider | Cloud Logging queries, operation counting, time range handling |
| GCPPricingProvider | Empty bucket costs, storage class rates, pricing calculations |
| InactiveGCSBucketRule | Detection logic, risk/confidence levels, remediation commands |

### Expected Test Outcomes

- Inactive bucket detection works with 0 operations
- Empty bucket detection works with 0 bytes size
- Pricing calculations match expected rates
- Cloud Logging queries complete without errors
- Remediation commands are properly formatted

---

## Extended Resources

### Google Cloud Documentation

- [Google Cloud Storage Documentation](https://cloud.google.com/storage/docs)
- [Cloud Logging Documentation](https://cloud.google.com/logging/docs)
- [Cloud Monitoring Documentation](https://cloud.google.com/monitoring/docs)
- [GCS Pricing](https://cloud.google.com/storage/pricing)
- [Cloud Logging Query Syntax](https://cloud.google.com/logging/docs/view/logging-query-language)

### Related Architecture Decisions

- [ADR-0001: Multi-Provider Architecture](../../docs/adr/ADR-0001-multi-provider-architecture.md)
- [ADR-0004: Async-First Metrics Collection](../../docs/adr/ADR-0004-async-first-metrics-collection.md)
- [ADR-0012: Optional Azure Support](../../docs/adr/ADR-0012-optional-azure-support.md)

### Migration & Upgrade Notes

**From v0.1.0 to v0.2.0:**
- Cloud Logging query syntax updated for consistency
- Storage class normalization improved (case-insensitive)

**Deprecations:**
- None currently

### Quick Reference Commands

```bash
# List all buckets and their sizes
gsutil ls -L

# Get bucket metadata
gsutil stat gs://bucket-name

# Delete a bucket and all contents
gsutil -m rm -r gs://bucket-name

# View recent Cloud Logging entries for a bucket
gcloud logging read 'resource.type="gcs_bucket" AND resource.labels.bucket_name="bucket-name"' --limit=50

# Check bucket labels/tags
gsutil label get gs://bucket-name
```

---

**[← Back to Main README](../../README.md)**
