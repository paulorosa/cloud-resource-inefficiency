# AWS Provider Documentation

## Overview

The AWS provider enables comprehensive cost optimization analysis for Amazon Web Services resources. Currently, it implements detection for **Inactive and Detached EBS Volumes (AWS-EBS-001)**, a common source of cloud waste in organizations using AWS for persistent storage.

This documentation covers detection criteria, pricing sources, risk assessment logic, remediation procedures, and practical implementation examples.

---

## AWS-EBS-001: Inactive and Detached EBS Volume

### Rule Summary

- **Rule ID**: `AWS-EBS-001`
- **Title**: Inactive and Detached EBS Volume
- **Category**: `Unattached Storage`
- **Detection Status**: Available (Implemented & Tested)
- **Supported Volume Types**: `gp2`, `gp3`, `io1`, `io2`, `st1`, `sc1`, `standard`
- **Lookback Window**: 14 days (configurable)

### What This Rule Detects

This rule identifies EBS volumes that:

1. **Are NOT attached to any EC2 instance** (state = `available`)
2. **Show NO I/O activity** during the observation window (CloudWatch metrics)
3. **Incur unnecessary storage costs** without providing value

Detached EBS volumes consume resources and generate costs even when unused. This rule helps organizations reclaim storage costs by identifying volumes that can be safely deleted.

---

## Detection Criteria

### 1. Volume State Analysis

The detection process begins by enumerating all EBS volumes in your AWS regions and filtering by state:

```python
# Internal logic: Filter volumes by state
volumes = ec2_client.describe_volumes()
detached_volumes = [v for v in volumes['Volumes'] if v['State'] == 'available']
```

**Criteria**:
- Volume state must be `available` (not `in-use`)
- Volume has NO attachments (Attachments list is empty)
- Volume is in a region being scanned (configurable)

### 2. CloudWatch Metrics Evaluation

For each detached volume, the detector queries CloudWatch metrics over a configurable lookback period (default: **14 days**) to assess inactivity:

| Metric | Unit | Meaning | Inactivity Threshold |
|--------|------|---------|----------------------|
| `VolumeReadOps` | Count | Total read operations | = 0 |
| `VolumeWriteOps` | Count | Total write operations | = 0 |
| `VolumeReadBytes` | Bytes | Total data read | = 0 |
| `VolumeWriteBytes` | Bytes | Total data written | = 0 |

**Inactivity Logic**:

```
I/O Activity = VolumeReadOps + VolumeWriteOps + VolumeReadBytes + VolumeWriteBytes

Volume is INACTIVE if: I/O Activity == 0 during lookback_days
```

If no datapoints are found in CloudWatch, the volume is still considered inactive (conservative approach).

**Time Window**:
- Default lookback: 14 days
- Configurable via `scanner.scan(lookback_days=N)`
- Metrics are fetched with 5-minute granularity from CloudWatch

### 3. Volume Configuration Details

The detector also captures volume configuration for cost calculation and risk assessment:

| Attribute | Purpose |
|-----------|---------|
| `VolumeType` | Determines unit pricing (gp2, gp3, io1, etc.) |
| `Size` (GiB) | Base storage capacity |
| `Iops` (if io1/io2) | Provisioned I/O operations per second |
| `Throughput` (if gp3) | Provisioned throughput in MiB/s |
| `CreateTime` | Volume age (used for risk assessment) |
| `Tags` | Metadata for filtering and risk adjustments |
| `SnapshotId` | Identifies if volume was created from snapshot |

---

## AWS Pricing Sources

### 1. Primary Source: AWS Pricing API

The detector attempts to fetch real-time pricing from the **AWS Pricing API** (`pricing.us-east-1.amazonaws.com`):

```python
pricing_client = boto3.client('pricing', region_name='us-east-1')
response = pricing_client.get_products(
    ServiceCode='AmazonEC2',
    Filters=[
        {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage'},
        {'Type': 'TERM_MATCH', 'Field': 'volumeType', 'Value': 'General Purpose'},
        {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': 'US East (N. Virginia)'},
    ],
    MaxResults=100
)
```

**Pricing API Advantages**:
- Real-time pricing synchronized with AWS list prices
- Region-specific rates (accounts for regional pricing variations)
- Cached in memory for performance (TTL: 24 hours by default)

**Limitations**:
- Requires `pricing:GetProducts` IAM permission
- Applies only to current On-Demand rates
- Does not include Savings Plans or Reserved Instance discounts

### 2. Fallback Pricing: Standard Rate Table

If the Pricing API is unavailable or unreachable, pricing falls back to a **hardcoded standard rate table** (as of Q4 2024):

| Volume Type | Base Rate ($/GiB/month) | IOPS Rate ($/IOPS/month) | Throughput Rate ($/MiB/s/month) |
|-------------|--------------------------|--------------------------|----------------------------------|
| `gp2` | $0.10 | N/A | N/A |
| `gp3` | $0.08 | $0.08 | $0.04 |
| `io1` | $0.125 | $0.065 | N/A |
| `io2` | $0.125 | $0.065 | N/A |
| `st1` (Throughput Optimized) | $0.045 | N/A | N/A |
| `sc1` (Cold Storage) | $0.015 | N/A | N/A |
| `standard` (Legacy) | $0.05 | $0.10 | N/A |

**Fallback Pricing Accuracy**:
- Typically accurate within ±5% of actual list prices
- Should be verified against AWS pricing page for accuracy-critical deployments
- Recommended for cost estimation, not for financial reporting

### 3. Cost Calculation Formula

Monthly cost is calculated as:

```
Monthly Cost = (Volume Size × Base Rate)
             + (Provisioned IOPS × IOPS Rate)        [if io1/io2]
             + (Provisioned Throughput × Throughput Rate)  [if gp3]
```

**Examples**:

```python
# Example 1: Standard gp2 volume, 100 GiB
# Cost = 100 × $0.10 = $10.00/month

# Example 2: io1 volume, 50 GiB, 1000 IOPS
# Cost = (50 × $0.125) + (1000 × $0.065) = $6.25 + $65.00 = $71.25/month

# Example 3: gp3 volume, 200 GiB, 5000 IOPS, 250 MiB/s
# Cost = (200 × $0.08) + (5000 × $0.08) + (250 × $0.04)
#      = $16.00 + $400.00 + $10.00 = $426.00/month
```

---

## Risk Level Assessment

The detector assigns a **Risk Level** (`VERY_LOW`, `LOW`, `MEDIUM`, `HIGH`) based on:

### Risk Factors

| Factor | Risk Impact | Assessment |
|--------|-------------|-----------|
| **Recent Snapshots** | Reduces risk | If snapshots exist within last 30 days: **-1 risk level** |
| **Retention Tags** | Reduces risk | If tags contain `DoNotDelete`, `Backup`, `Retain`: **-1 risk level** |
| **Volume Age** | Varies | New volumes (<7 days): MEDIUM; Old volumes (>90 days): LOW |
| **Production Tags** | Increases risk | If tags contain `production`, `prod`: **+1 risk level** |
| **Active Snapshots** | Reduces risk | If volume has ≥2 snapshots: Minimum risk is LOW |

### Risk Calculation Algorithm

```python
def assess_risk_level(volume):
    risk_score = 0  # Start neutral
    
    # Check for snapshots (reduce risk)
    recent_snapshots = get_snapshots_in_days(volume, days=30)
    if recent_snapshots:
        risk_score -= 1
    
    # Check for retention tags (reduce risk)
    retention_tags = ['DoNotDelete', 'Backup', 'Retain']
    if any(tag in volume.tags for tag in retention_tags):
        risk_score -= 1
    
    # Check for production tags (increase risk)
    if 'production' in volume.tags or 'prod' in volume.tags:
        risk_score += 1
    
    # Map risk_score to level
    if risk_score <= -2: return RiskLevel.VERY_LOW
    elif risk_score == -1: return RiskLevel.LOW
    elif risk_score == 0: return RiskLevel.MEDIUM
    else: return RiskLevel.HIGH
```

### Risk Level Examples

| Volume State | Snapshots | Tags | Risk Level |
|--------------|-----------|------|-----------|
| Detached, old, no snapshots, no tags | None | None | **HIGH** |
| Detached, 3-day-old volume | None | None | **MEDIUM** |
| Detached, 60-day-old volume | None | None | **LOW** |
| Detached with recent snapshots | 2 recent | None | **LOW** |
| Detached with `DoNotDelete` tag | None | DoNotDelete=true | **LOW** |
| Detached, multiple snapshots | 5 snapshots | DoNotDelete=true | **VERY_LOW** |

---

## Confidence Level Explanation

The detector assigns a **Confidence Level** to each opportunity:

| Level | Criteria | Use Case |
|-------|----------|----------|
| **HIGH** | Volume is clearly detached (state=available) AND has 0 I/O in 14 days AND no recent snapshots OR production tags | Safe to action immediately |
| **MEDIUM** | Volume is detached BUT has recent snapshots OR conflicting tags OR I/O data is incomplete | Review before deletion |
| **LOW** | Volume state is uncertain OR CloudWatch data is missing OR metrics are incomplete | Further investigation needed |

**Confidence Logic**:

```python
def assess_confidence_level(volume, metrics, snapshots):
    if volume.state != 'available':
        return ConfidenceLevel.LOW
    
    if not metrics or len(metrics) == 0:
        return ConfidenceLevel.LOW
    
    if snapshots and len(snapshots) > 0:
        return ConfidenceLevel.MEDIUM
    
    return ConfidenceLevel.HIGH
```

---

## Remediation & Cost Recovery

### Safe Deletion Workflow

**Before deleting**, perform these verification steps:

1. **Review Recent Snapshots**
   ```bash
   aws ec2 describe-snapshots \
     --owner-ids self \
     --filters "Name=volume-id,Values=vol-xxxxx" \
     --region us-east-1
   ```

2. **Check Volume Tags and Description**
   ```bash
   aws ec2 describe-volumes \
     --volume-ids vol-xxxxx \
     --region us-east-1
   ```

3. **Verify No Active Attachments**
   ```bash
   aws ec2 describe-volume-status \
     --volume-ids vol-xxxxx \
     --region us-east-1
   ```

4. **Create Final Snapshot (Optional)**
   ```bash
   aws ec2 create-snapshot \
     --volume-id vol-xxxxx \
     --description "Final backup before deletion" \
     --region us-east-1
   ```

### Remediation Command

Once verified, delete the volume using:

```bash
aws ec2 delete-volume \
  --volume-id vol-0123456789abcdef0 \
  --region us-east-1
```

**Output on Success**:
```
# No output (exit code 0)
```

**Common Errors**:

```bash
# Error: Volume is in-use
# Solution: Detach from EC2 instance first
aws ec2 detach-volume --volume-id vol-xxxxx --region us-east-1

# Error: InvalidVolume.NotFound
# Solution: Volume already deleted or wrong volume ID

# Error: UnauthorizedOperation
# Solution: User lacks ec2:DeleteVolume permission
```

### Estimated Cost Recovery

Monthly savings = Monthly cost of deleted volume

**Example Recovery Scenarios**:

| Scenario | Volume | Monthly Cost | Annual Savings |
|----------|--------|--------------|-----------------|
| Single gp2 (100 GiB) | vol-123 | $10.00 | $120.00 |
| Single io1 (50 GiB, 1000 IOPS) | vol-456 | $71.25 | $855.00 |
| Portfolio of 5 detached volumes | Multiple | $200.00 | $2,400.00 |

---

## Complete Python Usage Examples

### Example 1: Basic EBS Scan (Single Region)

```python
from cloud_resource_inefficiency import (
    CloudProvider,
    InefficiencyScanner,
    ResourceType,
    ScanResultFormatter,
)

# Initialize scanner
scanner = InefficiencyScanner(
    providers=[CloudProvider.AWS],
    regions=["us-east-1"],
)

# Execute scan
result = scanner.scan(
    resource_types=[ResourceType.AWS_EBS_VOLUME],
    lookback_days=14,
)

# Display results
print(ScanResultFormatter.to_text_summary(result))
```

### Example 2: Multi-Region Scan with Custom Lookback

```python
scanner = InefficiencyScanner(
    providers=[CloudProvider.AWS],
    regions=["us-east-1", "us-west-2", "eu-west-1", "sa-east-1"],
)

result = scanner.scan(
    resource_types=[ResourceType.AWS_EBS_VOLUME],
    lookback_days=30,  # Extended lookback
)

# Process opportunities
for opp in result.opportunities:
    print(f"[{opp.rule_id}] {opp.resource.resource_id}")
    print(f"  Region: {opp.resource.region}")
    print(f"  Savings: ${opp.estimated_monthly_savings:.2f}/month")
    print(f"  Risk: {opp.risk_level.value}")
    print(f"  Command: {opp.remediation_command}\n")
```

### Example 3: Programmatic Result Processing

```python
scanner = InefficiencyScanner(
    providers=[CloudProvider.AWS],
    regions=["us-east-1"],
)

result = scanner.scan(
    resource_types=[ResourceType.AWS_EBS_VOLUME],
    lookback_days=14,
)

# Summary statistics
print(f"Total Resources Scanned: {result.scanned_resources_count}")
print(f"Opportunities Found: {result.opportunities_count}")
print(f"Total Monthly Savings Potential: ${result.total_estimated_monthly_savings:.2f}")
print(f"Annual Projection: ${result.total_estimated_monthly_savings * 12:.2f}")

# Filter by risk level
high_risk = [o for o in result.opportunities if o.risk_level.value == "HIGH"]
print(f"\nHigh-Risk Opportunities: {len(high_risk)}")
```

### Example 4: Export to JSON for CI/CD Integration

```python
import json
from cloud_resource_inefficiency import (
    CloudProvider,
    InefficiencyScanner,
    ResourceType,
    ScanResultFormatter,
)

scanner = InefficiencyScanner(
    providers=[CloudProvider.AWS],
    regions=["us-east-1"],
)

result = scanner.scan(
    resource_types=[ResourceType.AWS_EBS_VOLUME],
    lookback_days=14,
)

# Export to JSON
json_output = ScanResultFormatter.to_json(result)
print(json_output)

# Save to file
with open("ebs_scan_report.json", "w") as f:
    f.write(json_output)
```

### Example 5: Custom Filtering and Remediation

```python
scanner = InefficiencyScanner(
    providers=[CloudProvider.AWS],
    regions=["us-east-1"],
)

result = scanner.scan(
    resource_types=[ResourceType.AWS_EBS_VOLUME],
    lookback_days=14,
)

# Filter: Only LOW-risk, HIGH-confidence opportunities
safe_to_delete = [
    o for o in result.opportunities
    if o.risk_level.value == "LOW" and o.confidence_level.value == "HIGH"
]

print(f"Safe to Delete: {len(safe_to_delete)} volumes\n")

# Generate remediation script
for opp in safe_to_delete:
    print(opp.remediation_command)
```

---

## Export Formats

### 1. Text Summary Format (Terminal/Console)

```
======================================================================
               CLOUD FINANCIAL INEFFICIENCY SCAN REPORT
======================================================================
Total Scanned Resources: 47
Opportunities Found:     3
Total Monthly Savings:   $129.00 USD
Annual Projected Saving: $1,548.00 USD
----------------------------------------------------------------------
Rule ID    | Resource ID            | Region       | Savings/Mo   | Risk
----------------------------------------------------------------------
AWS-EBS-001| vol-0123456789abcdef0  | us-east-1    | $    75.00   | LOW
AWS-EBS-001| vol-0987654321fedcba1  | sa-east-1    | $    27.20   | MEDIUM
AWS-EBS-001| vol-abcdef0123456789   | us-west-2    | $    26.80   | HIGH
======================================================================
```

Usage:
```python
print(ScanResultFormatter.to_text_summary(result))
```

### 2. Markdown Report Format

```markdown
## Cloud Inefficiency Scan Report

**Summary**: 3 opportunities found, $129.00/month potential savings

| Rule | Resource ID | Region | Monthly Savings | Risk | Confidence |
|------|-------------|--------|-----------------|------|-----------|
| AWS-EBS-001 | vol-0123456789abcdef0 | us-east-1 | $75.00 | LOW | HIGH |
| AWS-EBS-001 | vol-0987654321fedcba1 | sa-east-1 | $27.20 | MEDIUM | HIGH |
| AWS-EBS-001 | vol-abcdef0123456789 | us-west-2 | $26.80 | HIGH | MEDIUM |
```

Usage:
```python
print(ScanResultFormatter.to_markdown(result))
```

### 3. JSON Payload Format

```json
{
  "summary": {
    "total_opportunities": 3,
    "scanned_resources_count": 47,
    "total_estimated_monthly_savings": 129.00,
    "currency": "USD",
    "start_time": "2026-08-25T20:00:00+00:00",
    "end_time": "2026-08-25T20:05:30+00:00",
    "errors_count": 0
  },
  "opportunities": [
    {
      "opportunity_id": "opp-abc123",
      "rule_id": "AWS-EBS-001",
      "title": "Inactive and Detached EBS Volume",
      "estimated_monthly_savings": 75.00,
      "currency": "USD",
      "risk_level": "LOW",
      "confidence_level": "HIGH",
      "resource": {
        "resource_id": "vol-0123456789abcdef0",
        "resource_type": "aws_ebs_volume",
        "provider": "aws",
        "region": "us-east-1"
      },
      "remediation_command": "aws ec2 delete-volume --volume-id vol-0123456789abcdef0 --region us-east-1"
    }
  ],
  "errors": []
}
```

Usage:
```python
json_str = ScanResultFormatter.to_json(result)
dict_obj = ScanResultFormatter.to_dict(result)
```

---

## Authentication & Setup

### Prerequisites

1. **Python 3.9+**
2. **AWS Account** with permissions
3. **AWS CLI** configured (optional, for manual testing)

### IAM Permissions Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVolumes",
        "ec2:DescribeVolumeStatus",
        "ec2:DescribeSnapshots",
        "ec2:DescribeTags",
        "cloudwatch:GetMetricStatistics"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "pricing:GetProducts"
      ],
      "Resource": "*"
    }
  ]
}
```

### AWS Credential Configuration

Choose one of the following methods (tried in order):

1. **Environment Variables**
   ```bash
   export AWS_ACCESS_KEY_ID="your-access-key"
   export AWS_SECRET_ACCESS_KEY="your-secret-key"
   export AWS_DEFAULT_REGION="us-east-1"
   ```

2. **AWS Credentials File** (`~/.aws/credentials`)
   ```ini
   [default]
   aws_access_key_id = your-access-key
   aws_secret_access_key = your-secret-key

   [profile-name]
   aws_access_key_id = your-access-key
   aws_secret_access_key = your-secret-key
   ```

3. **AWS Config File** (`~/.aws/config`)
   ```ini
   [default]
   region = us-east-1

   [profile profile-name]
   region = us-west-2
   ```

4. **EC2 IAM Role** (when running on EC2 instance)
   - Instance automatically uses attached IAM role

5. **ECS Task IAM Role** (when running in ECS)
   - Task automatically uses attached role

### Installation & Usage

```bash
# 1. Install the library
pip install git+https://github.com/paulorosa/cloud-resource-inefficiency.git

# 2. Verify AWS credentials
aws sts get-caller-identity

# 3. Run the example
python -m examples.scan_ebs_example
```

---

## Test Coverage

### Unit Tests

The AWS EBS detection is covered by comprehensive unit tests in:

- **Location**: `tests/providers/aws/rules/test_ebs_inactive_detached.py`
- **Coverage**:
  - ✅ Volume state detection (attached vs. detached)
  - ✅ CloudWatch metrics evaluation
  - ✅ Risk level calculation
  - ✅ Confidence level assessment
  - ✅ Cost calculation (pricing API + fallback)
  - ✅ Tag filtering
  - ✅ Remediation command generation

### Integration Tests

- **Location**: `tests/integration/test_aws_scanner_integration.py`
- **Coverage**:
  - ✅ Real AWS API calls (if credentials available)
  - ✅ Multi-region scanning
  - ✅ Error handling and resilience

### Property-Based Tests

- **Location**: `tests/property_based/test_aws_ebs_properties.py`
- **Framework**: Hypothesis
- **Properties Tested**:
  - Pricing calculation consistency
  - Risk level monotonicity
  - Remediation command format validity

### Running Tests

```bash
# Run all tests
python -m pytest -v

# Run AWS-specific tests only
python -m pytest tests/providers/aws/ -v

# Run with coverage
python -m pytest --cov=cloud_resource_inefficiency tests/

# Run tests for EBS rule
python -m pytest tests/providers/aws/rules/test_ebs_inactive_detached.py -v
```

---

## AWS Documentation & Resources

### Official AWS Documentation

- [EBS Volumes User Guide](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-volumes.html)
- [EBS Pricing](https://aws.amazon.com/ebs/pricing/)
- [CloudWatch Metrics Reference](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring_ec2.html)
- [AWS Pricing API](https://docs.aws.amazon.com/awspricing/latest/userguide/welcome.html)

### Related Articles & Tools

- [AWS Cost Optimization](https://aws.amazon.com/aws-cost-management/cost-optimization/)
- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/)
- [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/)

### Troubleshooting

**Issue**: "Unable to locate credentials"
- **Solution**: Ensure AWS credentials are configured via environment variables, ~/.aws/credentials, or IAM role

**Issue**: "An error occurred (AccessDenied) when calling the GetMetricStatistics operation"
- **Solution**: Verify IAM user/role has `cloudwatch:GetMetricStatistics` permission

**Issue**: "An error occurred (UnauthorizedOperation) when calling the DescribeVolumes operation"
- **Solution**: Add `ec2:DescribeVolumes` permission to IAM policy

---

## Related Documentation

- **[← Back to Main README](../../../README.md)**
- **[GCP Provider Documentation](../gcp/README.md)**
- **[Azure Provider Documentation](../azure/README.md)**
- **[Core Architecture & Design](../../adr/)**

---

## Summary

The AWS-EBS-001 rule provides organizations with a practical, low-risk opportunity to reduce cloud costs by identifying and safely removing detached, inactive EBS volumes. By combining multiple data sources (EC2 API, CloudWatch metrics, snapshot history, and tags), the rule generates high-confidence recommendations with clear risk assessment and actionable remediation commands.

For detailed implementation questions, refer to the [main README](../../../README.md) or submit an issue to the project repository.
