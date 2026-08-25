"""
Example: Scanning for Inactive and Detached EBS Volumes using cloud-resource-inefficiency.
"""

from cloud_resource_inefficiency import (
    CloudProvider,
    InefficiencyScanner,
    ResourceType,
    ScanResultFormatter,
)


def main():
    print("Initializing Cloud Inefficiency Scanner...")
    # Initialize the scanner for AWS in desired regions
    scanner = InefficiencyScanner(
        providers=[CloudProvider.AWS],
        regions=["us-east-1", "sa-east-1"],
    )

    print("Running scan for inactive and detached EBS volumes...")
    # Execute the scan with a 14-day lookback window for CloudWatch metrics
    result = scanner.scan(
        resource_types=[ResourceType.AWS_EBS_VOLUME],
        lookback_days=14,
    )

    # 1. Plain-text summary
    print(ScanResultFormatter.to_text_summary(result))

    # 2. Markdown summary
    print("\n--- Markdown Report ---")
    print(ScanResultFormatter.to_markdown(result))

    # 3. Accessing structured data
    for opp in result.opportunities:
        print(f"\nOpportunity ID: {opp.opportunity_id}")
        print(f"Rule: {opp.title} ({opp.rule_id})")
        print(f"Volume: {opp.resource.resource_id} | Region: {opp.resource.region}")
        print(f"Estimated Monthly Savings: ${opp.estimated_monthly_savings:.2f} {opp.currency}")
        print(f"Confidence: {opp.confidence_level.value} | Risk Level: {opp.risk_level.value}")
        print(f"Remediation Command: {opp.remediation_command}")


if __name__ == "__main__":
    main()
