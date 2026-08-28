# ADR-0009: Multi-Format Output for Scan Results

## Status
Accepted

## Context

Resultado de um scan precisa ser consumido por **múltiplos públicos**:
- **Humanos (DevOps/SRE)**: Querem resumo legível no terminal
- **CI/CD Pipelines**: Querem JSON estruturado para parsing
- **Dashboards**: Querem Markdown renderizável ou JSON
- **Ferramentas de Export**: Querem CSV, Parquet, etc.

Sem abstração:
```python
# Anti-pattern
if output_format == "text":
    print_text(result)
elif output_format == "json":
    print(json.dumps(result))
elif output_format == "markdown":
    print_markdown(result)
# ... crescimento descontrolado
```

Com abstração elegante:
```python
# Padrão recomendado
formatter = ScanResultFormatter()
output = formatter.to_text_summary(result)  # ou to_json, to_markdown, etc.
```

## Decision

Implementar **`ScanResultFormatter`** com múltiplos métodos de formatação:

```python
# formatters/output.py
from dataclasses import asdict
from typing import Dict, Any

class ScanResultFormatter:
    \"\"\"Formatador de resultados com suporte a múltiplos formatos\"\"\"
    
    @staticmethod
    def to_text_summary(result: ScanResult) -> str:
        \"\"\"Retorna resumo em texto ASCII formatado para terminal\"\"\"
        lines = [
            \"=\" * 70,
            \"CLOUD FINANCIAL INEFFICIENCY SCAN REPORT\".center(70),
            \"=\" * 70,
            f\"Total Scanned Resources: {result.scanned_resources_count}\",
            f\"Opportunities Found: {len(result.opportunities)}\",
            f\"Total Monthly Savings: ${sum(o.estimated_monthly_savings for o in result.opportunities):.2f} USD\",
            f\"Annual Projected Saving: ${sum(o.estimated_monthly_savings * 12 for o in result.opportunities):.2f} USD\",
            \"-\" * 70,
            \"Rule ID | Resource ID | Region | Savings/Mo | Risk\",
            \"-\" * 70,
        ]
        
        for opp in sorted(result.opportunities, key=lambda o: o.estimated_monthly_savings, reverse=True):\n            lines.append(\n                f\"{opp.rule_id:<15} | {opp.resource.resource_id:<20} | \"\n                f\"{opp.resource.region:<10} | ${opp.estimated_monthly_savings:>10.2f} | {opp.risk_level.value:<6}\"\n            )\n        \n        lines.append(\"=\" * 70)\n        return \"\\n\".join(lines)\n    \n    @staticmethod\n    def to_markdown(result: ScanResult) -> str:\n        \"\"\"Retorna relatório completo em Markdown\"\"\"
        md = f\"\"\"# Cloud Financial Inefficiency Scan Report\n\n## Summary\n\n| Metric | Value |\n|--------|-------|\n| Total Resources Scanned | {result.scanned_resources_count} |\n| Opportunities Found | {len(result.opportunities)} |\n| Total Monthly Savings | ${sum(o.estimated_monthly_savings for o in result.opportunities):.2f} USD |\n| Annual Projected Saving | ${sum(o.estimated_monthly_savings * 12 for o in result.opportunities):.2f} USD |\n| Scan Duration | {(result.end_time - result.start_time).total_seconds():.2f}s |\n\n## Opportunities\n\n| Rule | Resource ID | Name | Region | Monthly Savings | Risk | Confidence | Action |\n|------|-------------|------|--------|-----------------|------|------------|--------|\n\"\"\"\n        \n        for opp in sorted(result.opportunities, key=lambda o: o.estimated_monthly_savings, reverse=True):\n            md += f\"| `{opp.rule_id}` | `{opp.resource.resource_id}` | {opp.resource.get_tag('Name', '-')} | \"\n            md += f\"`{opp.resource.region}` | **${opp.estimated_monthly_savings:.2f}** | {opp.risk_level.value} | \"\n            md += f\"{opp.confidence_level.value} | {self._sanitize_markdown(opp.title)} |\\n\"\n        \n        if result.errors:\n            md += f\"\\n## Errors ({len(result.errors)})\\n\\n\"\n            for err in result.errors:\n                md += f\"- **{err.get('resource_type', 'Unknown')}** in `{err.get('region', 'Unknown')}`: {err.get('error', 'Unknown error')}\\n\"\n        \n        return md\n    \n    @staticmethod\n    def to_json(result: ScanResult) -> str:\n        \"\"\"Retorna estrutura JSON para integração com pipelines\"\"\"
        data = {\n            \"summary\": {\n                \"total_opportunities\": len(result.opportunities),\n                \"scanned_resources_count\": result.scanned_resources_count,\n                \"total_estimated_monthly_savings\": sum(\n                    o.estimated_monthly_savings for o in result.opportunities\n                ),\n                \"currency\": \"USD\",\n                \"start_time\": result.start_time.isoformat(),\n                \"end_time\": result.end_time.isoformat(),\n                \"scan_duration_seconds\": (\n                    result.end_time - result.start_time\n                ).total_seconds(),\n                \"errors_count\": len(result.errors),\n            },\n            \"opportunities\": [\n                {\n                    \"opportunity_id\": opp.opportunity_id,\n                    \"rule_id\": opp.rule_id,\n                    \"title\": opp.title,\n                    \"estimated_monthly_savings\": opp.estimated_monthly_savings,\n                    \"currency\": opp.currency,\n                    \"risk_level\": opp.risk_level.value,\n                    \"confidence_level\": opp.confidence_level.value,\n                    \"resource\": asdict(opp.resource),\n                    \"remediation_command\": opp.remediation_command,\n                }\n                for opp in result.opportunities\n            ],\n            \"errors\": result.errors,\n        }\n        import json\n        return json.dumps(data, indent=2)\n    \n    @staticmethod\n    def to_dict(result: ScanResult) -> Dict[str, Any]:\n        \"\"\"Retorna dicionário Python (antes de JSON serialization)\"\"\"
        return json.loads(ScanResultFormatter.to_json(result))\n    \n    @staticmethod\n    def _sanitize_markdown(text: str) -> str:\n        \"\"\"Escapa caracteres especiais Markdown para evitar quebras de layout\"\"\"
        replacements = {\n            \"|\": \"\\\\|\",\n            \"\\n\": \" \",\n            \"[\": \"\\\\[\",\n            \"]\": \"\\\\]\",\n        }\n        for old, new in replacements.items():\n            text = text.replace(old, new)\n        return text\n```\n\n## Rationale\n\n1. **Separação de Responsabilidades**: Formatting é separado de lógica de scan\n2. **Extensibilidade**: Fácil adicionar novos formatos (CSV, XML, etc.)\n3. **Testabilidade**: Cada formatter pode ser testado isoladamente\n4. **Sem Coupling**: ScanResult não conhece como será formatado\n5. **Consumidor Agnostic**: Mesmo resultado pode ser consumido em múltiplos contextos\n\n## Consequences\n\n### Positive\n- ✅ Mesmos dados exportáveis em múltiplos formatos\n- ✅ Humanamente legível no terminal, machine-readable em JSON\n- ✅ Markdown renderizável em GitHub, Confluence, Notion\n- ✅ JSON estruturado para CI/CD pipelines (pytest, GitHub Actions)\n- ✅ Fácil adicionar novos formatos sem modificar scan engine\n\n### Negative\n- ❌ Múltiplos formatadores significam múltiplo teste\n- ❌ Sanitização de Markdown/XML pode ser complexa (injeção de caracteres)\n- ❌ Performance: Converter para JSON grande pode ser lento\n- ❌ Manutenção: Mudança em ScanResult requer atualizar todos os formatadores\n\n## Alternatives Considered\n\n### 1. Jinja2 Templates\n```python\nfrom jinja2 import Template\n\ntemplate_text = Template(\"\"\"\nScan Results:\n{% for opp in opportunities %}\n  - {{ opp.title }}: ${{ opp.savings }}\n{% endfor %}\n\"\"\")\n\noutput = template_text.render(opportunities=result.opportunities)\n```\n**Rejeitado**: Over-engineered. Templates introduzem dependência externa e learning curve.\n\n### 2. Single Format Strategy (JSON Only)\n```python\noutput = json.dumps(asdict(result))\n# Consumer transforma JSON em formato desejado\n```\n**Rejeitado**: Menos ergonômico. Cada consumer precisaria fazer parsing. Texto legível seria muito menor.\n\n### 3. Adapter Pattern (Separar em Múltiplas Classes)\n```python\nclass TextFormatter(BaseFormatter):\n    def format(self, result: ScanResult) -> str: ...\n\nclass JSONFormatter(BaseFormatter):\n    def format(self, result: ScanResult) -> str: ...\n```\n**Rejeitado Parcialmente**: Mais OOP puro, mas overkill para este caso. Adotado como `ScanResultFormatter` com múltiplos métodos.\n\n## Related Decisions\n\n- **ADR-0003**: DTOs imutáveis facilitam serialização\n- **ADR-0008**: Rules output Opp que são formatadas\n\n## Implementation References\n\n### Key Files\n- `src/cloud_resource_inefficiency/formatters/output.py`\n  - `ScanResultFormatter` classe\n  - Métodos: `to_text_summary()`, `to_markdown()`, `to_json()`, `to_dict()`\n\n### Usage Example\n```python\nfrom cloud_resource_inefficiency import InefficiencyScanner, ScanResultFormatter\n\nscanner = InefficiencyScanner(...)\nresult = scanner.scan(...)\n\n# Diferentes formatos\nprint(ScanResultFormatter.to_text_summary(result))  # Terminal\nwith open(\"report.md\", \"w\") as f:\n    f.write(ScanResultFormatter.to_markdown(result))  # Markdown file\nwith open(\"report.json\", \"w\") as f:\n    f.write(ScanResultFormatter.to_json(result))  # JSON file\n```\n\n### Output Examples\n\n**Text Summary**:\n```\n======================================================================\n               CLOUD FINANCIAL INEFFICIENCY SCAN REPORT\n======================================================================\nTotal Scanned Resources: 150\nOpportunities Found: 5\nTotal Monthly Savings: $102.40 USD\nAnnual Projected Saving: $1,228.80 USD\n----------------------------------------------------------------------\n```\n\n**Markdown**:\n```markdown\n# Cloud Financial Inefficiency Scan Report\n\n## Summary\n\n| Metric | Value |\n|--------|-------|\n| Total Resources Scanned | 150 |\n| Opportunities Found | 5 |\n```\n\n**JSON**:\n```json\n{\n  \"summary\": {\n    \"total_opportunities\": 5,\n    \"scanned_resources_count\": 150,\n    \"total_estimated_monthly_savings\": 102.40\n  },\n  \"opportunities\": [...]\n}\n```\n\n## Notes\n\n- **Sanitização**: Markdown sanitization é importante para evitar quebra de tabelas (pipe characters, newlines)\n- **Performance**: Para resultados muito grandes (1M+ opportunities), JSON pode ser lento. Considerar JSONL (one JSON per line) futuramente\n- **Streaming**: Possível evolução futura - retornar generator ao invés de string para grandes datasets\n"