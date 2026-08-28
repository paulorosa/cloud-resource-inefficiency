"""Tests for output formatters (JSON, Markdown, Text)."""

import json
from datetime import datetime, timezone

import pytest

from cloud_resource_inefficiency.core.enums import (
    CloudProvider,
    ConfidenceLevel,
    InefficiencyCategory,
    ResourceType,
    RiskLevel,
)
from cloud_resource_inefficiency.core.models import (
    CloudResource,
    Opportunity,
    ScanResult,
)
from cloud_resource_inefficiency.formatters.output import ScanResultFormatter


@pytest.fixture
def sample_scan_result() -> ScanResult:
    """Create a sample scan result for testing formatters."""
    resource = CloudResource(
        resource_id="vol-12345",
        name="test-volume",
        provider=CloudProvider.AWS,
        resource_type=ResourceType.AWS_EBS_VOLUME,
        region="us-east-1",
        account_id="123456789012",
        tags={"Environment": "Dev"},
        created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
        status="available",
        raw_metadata={"size_gib": 100},
    )

    opportunity = Opportunity(
        rule_id="AWS-EBS-001",
        resource=resource,
        category=InefficiencyCategory.UNATTACHED_STORAGE,
        estimated_monthly_savings=8.0,
        confidence_level=ConfidenceLevel.HIGH,
        risk_level=RiskLevel.LOW,
        recommended_actions=["Delete the volume"],
        remediation_command="aws ec2 delete-volume --volume-id vol-12345",
    )

    return ScanResult(
        opportunities=[opportunity],
        scanned_resources_count=10,
        start_time=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2024, 1, 1, 10, 5, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def empty_scan_result() -> ScanResult:
    """Create an empty scan result for testing formatters."""
    return ScanResult(
        opportunities=[],
        scanned_resources_count=10,
        start_time=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2024, 1, 1, 10, 5, 0, tzinfo=timezone.utc),
    )


class TestScanResultFormatterJSON:
    """Tests for JSON formatting."""

    def test_to_json_returns_valid_json(self, sample_scan_result: ScanResult) -> None:
        """to_json should return valid JSON string."""
        json_str = ScanResultFormatter.to_json(sample_scan_result)
        data = json.loads(json_str)  # Should not raise
        assert isinstance(data, dict)

    def test_to_json_includes_opportunities(self, sample_scan_result: ScanResult) -> None:
        """JSON should include opportunities."""
        json_str = ScanResultFormatter.to_json(sample_scan_result)
        data = json.loads(json_str)
        assert "opportunities" in data
        assert len(data["opportunities"]) == 1

    def test_to_json_includes_summary_fields(self, sample_scan_result: ScanResult) -> None:
        """JSON should include summary fields."""
        json_str = ScanResultFormatter.to_json(sample_scan_result)
        data = json.loads(json_str)
        assert "scanned_resources_count" in data
        assert data["scanned_resources_count"] == 10

    def test_to_json_with_custom_indent(self, sample_scan_result: ScanResult) -> None:
        """JSON should respect custom indent parameter."""
        json_str = ScanResultFormatter.to_json(sample_scan_result, indent=4)
        assert "    " in json_str  # 4-space indent

    def test_to_dict_returns_dictionary(self, sample_scan_result: ScanResult) -> None:
        """to_dict should return a dictionary."""
        result_dict = ScanResultFormatter.to_dict(sample_scan_result)
        assert isinstance(result_dict, dict)
        assert "opportunities" in result_dict


class TestScanResultFormatterText:
    """Tests for plain text formatting."""

    def test_to_text_summary_includes_header(self, sample_scan_result: ScanResult) -> None:
        """Text summary should include header."""
        text = ScanResultFormatter.to_text_summary(sample_scan_result)
        assert "CLOUD FINANCIAL INEFFICIENCY SCAN REPORT" in text

    def test_to_text_summary_includes_metrics(self, sample_scan_result: ScanResult) -> None:
        """Text summary should include key metrics."""
        text = ScanResultFormatter.to_text_summary(sample_scan_result)
        assert "Total Scanned Resources: 10" in text
        assert "Opportunities Found: 1" in text
        assert "Total Monthly Savings:" in text

    def test_to_text_summary_includes_opportunity_details(self, sample_scan_result: ScanResult) -> None:
        """Text summary should list opportunity details."""
        text = ScanResultFormatter.to_text_summary(sample_scan_result)
        assert "AWS-EBS-001" in text
        assert "vol-12345" in text

    def test_to_text_summary_for_empty_results(self, empty_scan_result: ScanResult) -> None:
        """Text summary should handle empty results."""
        text = ScanResultFormatter.to_text_summary(empty_scan_result)
        assert "No financial inefficiencies detected" in text

    def test_to_text_summary_truncates_long_resource_ids(self, sample_scan_result: ScanResult) -> None:
        """Text summary should truncate very long resource IDs."""
        # Create resource with very long ID
        sample_scan_result.opportunities[0].resource.resource_id = "a" * 50
        text = ScanResultFormatter.to_text_summary(sample_scan_result)
        # Should contain truncated version with "..."
        assert "..." in text


class TestScanResultFormatterMarkdown:
    """Tests for Markdown formatting."""

    def test_to_markdown_returns_string(self, sample_scan_result: ScanResult) -> None:
        """to_markdown should return a string."""
        md = ScanResultFormatter.to_markdown(sample_scan_result)
        assert isinstance(md, str)

    def test_to_markdown_includes_header(self, sample_scan_result: ScanResult) -> None:
        """Markdown should include H1 header."""
        md = ScanResultFormatter.to_markdown(sample_scan_result)
        assert "# Cloud Financial Inefficiency Scan Report" in md

    def test_to_markdown_includes_summary_section(self, sample_scan_result: ScanResult) -> None:
        """Markdown should include summary section."""
        md = ScanResultFormatter.to_markdown(sample_scan_result)
        assert "## Summary" in md
        assert "**Scanned Resources**:" in md
        assert "**Estimated Monthly Savings**:" in md

    def test_to_markdown_includes_table_for_opportunities(self, sample_scan_result: ScanResult) -> None:
        """Markdown should include opportunities table."""
        md = ScanResultFormatter.to_markdown(sample_scan_result)
        assert "## Opportunities Detail" in md
        assert "|" in md  # Markdown table delimiter

    def test_to_markdown_escapes_pipe_in_resource_name(self) -> None:
        """Markdown formatter should escape pipe characters in resource names."""
        resource = CloudResource(
            resource_id="vol-pipe|char",
            name="volume|with|pipes",
            provider=CloudProvider.AWS,
            resource_type=ResourceType.AWS_EBS_VOLUME,
            region="us-east-1",
            account_id="123456789012",
            tags={},
            created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            status="available",
            raw_metadata={},
        )

        opportunity = Opportunity(
            rule_id="TEST-001",
            resource=resource,
            category=InefficiencyCategory.UNATTACHED_STORAGE,
            estimated_monthly_savings=10.0,
            confidence_level=ConfidenceLevel.HIGH,
            risk_level=RiskLevel.LOW,
            recommended_actions=["Delete"],
            remediation_command="delete",
        )

        result = ScanResult(
            opportunities=[opportunity],
            scanned_resources_count=1,
            start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        md = ScanResultFormatter.to_markdown(result)
        # Pipes should be escaped as \|
        assert "\\|" in md

    def test_to_markdown_escapes_html_tags(self) -> None:
        """Markdown formatter should escape HTML tags for safety."""
        resource = CloudResource(
            resource_id="vol-<script>",
            name="volume<html>",
            provider=CloudProvider.AWS,
            resource_type=ResourceType.AWS_EBS_VOLUME,
            region="us-east-1",
            account_id="123456789012",
            tags={},
            created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            status="available",
            raw_metadata={},
        )

        opportunity = Opportunity(
            rule_id="TEST-001",
            resource=resource,
            category=InefficiencyCategory.UNATTACHED_STORAGE,
            estimated_monthly_savings=10.0,
            confidence_level=ConfidenceLevel.HIGH,
            risk_level=RiskLevel.LOW,
            recommended_actions=["Delete"],
            remediation_command="delete",
        )

        result = ScanResult(
            opportunities=[opportunity],
            scanned_resources_count=1,
            start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        md = ScanResultFormatter.to_markdown(result)
        # HTML tags should be escaped
        assert "&lt;" in md
        assert "&gt;" in md
        assert "<script>" not in md
        assert "<html>" not in md

    def test_to_markdown_for_empty_results(self, empty_scan_result: ScanResult) -> None:
        """Markdown should handle empty results."""
        md = ScanResultFormatter.to_markdown(empty_scan_result)
        assert "No opportunities found" in md

    def test_escape_md_cell_with_none(self) -> None:
        """_escape_md_cell should handle None values."""
        result = ScanResultFormatter._escape_md_cell(None)
        assert result == "-"

    def test_escape_md_cell_with_multiline_text(self) -> None:
        """_escape_md_cell should remove newlines."""
        text = "Line 1\nLine 2\rLine 3\r\nLine 4"
        result = ScanResultFormatter._escape_md_cell(text)
        # Should replace all newlines with spaces
        assert "\n" not in result
        assert "\r" not in result
        assert "Line 1 Line 2 Line 3 Line 4" in result


class TestScanResultFormatterEdgeCases:
    """Tests for edge cases and error handling."""

    def test_formatter_handles_large_savings(self) -> None:
        """Formatter should handle large savings amounts."""
        resource = CloudResource(
            resource_id="vol-large",
            name="expensive-volume",
            provider=CloudProvider.AWS,
            resource_type=ResourceType.AWS_EBS_VOLUME,
            region="us-east-1",
            account_id="123456789012",
            tags={},
            created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            status="available",
            raw_metadata={},
        )

        opportunity = Opportunity(
            rule_id="TEST-001",
            resource=resource,
            category=InefficiencyCategory.UNATTACHED_STORAGE,
            estimated_monthly_savings=999999.99,
            confidence_level=ConfidenceLevel.HIGH,
            risk_level=RiskLevel.LOW,
            recommended_actions=["Delete"],
            remediation_command="delete",
        )

        result = ScanResult(
            opportunities=[opportunity],
            scanned_resources_count=1,
            start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        text = ScanResultFormatter.to_text_summary(result)
        assert "999999.99" in text

    def test_formatter_handles_many_opportunities(self) -> None:
        """Formatter should handle many opportunities."""
        opportunities = []
        for i in range(100):
            resource = CloudResource(
                resource_id=f"vol-{i}",
                name=f"volume-{i}",
                provider=CloudProvider.AWS,
                resource_type=ResourceType.AWS_EBS_VOLUME,
                region="us-east-1",
                account_id="123456789012",
                tags={},
                created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
                status="available",
                raw_metadata={},
            )

            opportunity = Opportunity(
                rule_id="TEST-001",
                resource=resource,
                category=InefficiencyCategory.UNATTACHED_STORAGE,
                estimated_monthly_savings=10.0,
                confidence_level=ConfidenceLevel.HIGH,
                risk_level=RiskLevel.LOW,
                recommended_actions=["Delete"],
                remediation_command="delete",
            )
            opportunities.append(opportunity)

        result = ScanResult(
            opportunities=opportunities,
            scanned_resources_count=100,
            start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        md = ScanResultFormatter.to_markdown(result)
        assert "100" in md
        json_str = ScanResultFormatter.to_json(result)
        assert json.loads(json_str) is not None
