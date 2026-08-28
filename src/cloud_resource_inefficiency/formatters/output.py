"""Formatters for scan results and opportunities."""

import json
from typing import Any, Dict

from cloud_resource_inefficiency.core.models import ScanResult


class ScanResultFormatter:
    """Utility to format ScanResult into various representations (JSON, Markdown, Text)."""

    @staticmethod
    def to_json(result: ScanResult, indent: int = 2) -> str:
        """Format ScanResult into a pretty JSON string."""
        return json.dumps(ScanResultFormatter.to_dict(result), indent=indent, default=str)

    @staticmethod
    def to_dict(result: ScanResult) -> Dict[str, Any]:
        """Convert ScanResult into a dictionary."""
        data = result.to_dict()
        data.update({
            "scanned_resources_count": result.scanned_resources_count,
            "opportunities_count": result.opportunities_count,
            "total_estimated_monthly_savings": result.total_estimated_monthly_savings,
        })
        return data

    @staticmethod
    def to_text_summary(result: ScanResult) -> str:
        """Generate a concise plain-text summary."""
        lines = [
            "=" * 70,
            "               CLOUD FINANCIAL INEFFICIENCY SCAN REPORT",
            "=" * 70,
            f"Total Scanned Resources: {result.scanned_resources_count}",
            f"Opportunities Found: {result.opportunities_count}",
            f"Total Monthly Savings:   ${result.total_estimated_monthly_savings:,.2f} USD",
            f"Annual Projected Saving: ${result.total_estimated_monthly_savings * 12:,.2f} USD",
            "-" * 70,
        ]

        if not result.opportunities:
            lines.append("No financial inefficiencies detected! All resources look efficient.")
        else:
            lines.append(f"{'Rule ID':<10} | {'Resource ID':<22} | {'Region':<12} | {'Savings/Mo':<12} | {'Risk':<8}")
            lines.append("-" * 70)
            for opp in result.opportunities:
                res_id = opp.resource.resource_id
                if len(res_id) > 20:
                    res_id = res_id[:17] + "..."
                lines.append(
                    f"{opp.rule_id:<10} | {res_id:<22} | {opp.resource.region:<12} | "
                    f"${opp.estimated_monthly_savings:>9.2f} | {opp.risk_level.value:<8}"
                )

        lines.append("=" * 70)
        return "\n".join(lines)

    @staticmethod
    def _escape_md_cell(text: Any) -> str:
        """Sanitizes text for safe inclusion inside Markdown table cells."""
        if text is None:
            return "-"
        s = str(text).replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
        s = s.replace("|", "\\|")
        # Prevent HTML injection while maintaining readability
        s = s.replace("<", "&lt;").replace(">", "&gt;")
        return s.strip()

    @staticmethod
    def to_markdown(result: ScanResult) -> str:
        """Generate a GitHub-flavored Markdown report."""
        md = [
            "# Cloud Financial Inefficiency Scan Report",
            "",
            "## Summary",
            "",
            f"- **Scanned Resources**: {result.scanned_resources_count}",
            f"- **Identified Opportunities**: {result.opportunities_count}",
            f"- **Estimated Monthly Savings**: **${result.total_estimated_monthly_savings:,.2f} USD**",
            f"- **Projected Annual Savings**: **${result.total_estimated_monthly_savings * 12:,.2f} USD**",
            "",
            "## Opportunities Detail",
            "",
        ]

        if not result.opportunities:
            md.append("*No opportunities found. All evaluated resources are actively utilized.*")
        else:
            md.extend([
                "| Rule | Resource ID | Name | Region | Monthly Savings | Risk Level | Confidence | Action |",
                "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
            ])
            for opp in result.opportunities:
                rule_id = ScanResultFormatter._escape_md_cell(opp.rule_id)
                res_id = ScanResultFormatter._escape_md_cell(opp.resource.resource_id)
                name = ScanResultFormatter._escape_md_cell(opp.resource.name)
                region = ScanResultFormatter._escape_md_cell(opp.resource.region)
                action = (
                    ScanResultFormatter._escape_md_cell(opp.recommended_actions[0])
                    if opp.recommended_actions
                    else "-"
                )
                md.append(
                    f"| `{rule_id}` | `{res_id}` | {name} | `{region}` | "
                    f"**${opp.estimated_monthly_savings:.2f}** | {opp.risk_level.value} | {opp.confidence_level.value} | {action} |"
                )

        return "\n".join(md)
