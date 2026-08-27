# ADR-0008: Rule Evaluation Model - Opportunity Detection

## Status
Accepted

## Context

Detecção de ineficiências requer **lógica específica** para cada oportunidade:
- AWS EBS: Verificar I/O operations em CloudWatch, calcular economia
- GCS: Verificar access logs, bucket size
- Azure Disk: Verificar read/write ops no Monitor

Cada regra (rule) requer:
1. **Critério de Avaliação**: Dados do recurso + métricas = Oportunidade?
2. **Cálculo de Economia**: Tarifa × Volume = Poupança mensal
3. **Avaliação de Risco**: Snapshots? Tags de retenção? Backups recentes?
4. **Nível de Confiança**: High/Medium/Low baseado em dados disponíveis

Sem um padrão, cada regra seria:
- Hardcoded no scanner
- Misturada com lógica de coleta/formatação
- Difícil testar isoladamente

## Decision

Implementar **Strategy Pattern** para regras com interface `BaseInefficiencyRule`:

```python
# core/rule.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

class BaseInefficiencyRule(ABC):
    """Interface para detecção de ineficiências"""
    
    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Identificador único (ex: 'AWS-EBS-001')"""
        pass
    
    @property
    @abstractmethod
    def title(self) -> str:
        """Título legível (ex: 'Inactive and Detached EBS Volume')"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Descrição detalhada do critério"""
        pass
    
    @property
    @abstractmethod
    def category(self) -> InefficiencyCategory:
        """Categoria (ex: UNATTACHED_STORAGE)"""
        pass
    
    @property
    @abstractmethod
    def target_resource_type(self) -> ResourceType:
        """Tipo de recurso que esta regra avalia"""
        pass
    
    @abstractmethod
    def evaluate(
        self,
        resource: CloudResource,
        metrics_provider: BaseMetricsProvider,
        pricing_provider: BasePricingProvider,
        lookback_days: int = 14,
        **kwargs: Any,
    ) -> Optional[Opportunity]:
        """
        Avalia se recurso é uma oportunidade.
        
        Retorna:
            Opportunity se critério atendido, None caso contrário
        """
        pass
```

### Exemplo: AWS EBS Rule
```python
# providers/aws/rules/ebs_inactive_detached.py
class InactiveDetachedEBSVolumeRule(BaseInefficiencyRule):
    rule_id = "AWS-EBS-001"
    title = "Inactive and Detached EBS Volume"
    description = "EBS volumes not attached to instances with zero I/O operations"
    category = InefficiencyCategory.UNATTACHED_STORAGE
    target_resource_type = ResourceType.AWS_EBS_VOLUME
    
    def evaluate(
        self,
        resource: CloudResource,
        metrics_provider: BaseMetricsProvider,
        pricing_provider: BasePricingProvider,
        lookback_days: int = 14,
        max_allowed_io_ops: float = 0.0,
        **kwargs: Any,
    ) -> Optional[Opportunity]:
        \"\"\"\n        Critérios:\n        1. Volume em estado 'available' (não anexado)\n        2. Zero I/O operations nos últimos lookback_days\n        3. Calcular economia mensal\n        \"\"\"\n        \n        # 1. Verificar se está desanexado\n        if not self._is_detached(resource):\n            return None\n        \n        # 2. Verificar métricas de I/O\n        try:\n            metrics = metrics_provider.get_metrics(\n                resource=resource,\n                metric_names=[\"VolumeReadOps\", \"VolumeWriteOps\"],\n                lookback_days=lookback_days,\n            )\n        except Exception as e:\n            logger.warning(f\"Failed to get metrics for {resource.resource_id}: {e}\")\n            return None  # Falha de permissão = não gerar falso positivo\n        \n        total_ops = metrics.read_ops + metrics.write_ops\n        if total_ops > max_allowed_io_ops:\n            return None  # Ativo, não é oportunidade\n        \n        # 3. Calcular economia\n        pricing = pricing_provider.get_pricing_details(\n            resource=resource,\n            volume_type=resource.get_tag(\"VolumeType\", \"gp2\"),\n        )\n        monthly_savings = pricing.monthly_cost\n        \n        # 4. Avaliar risco\n        risk_level = self._assess_risk(resource, metrics)\n        confidence_level = self._assess_confidence(resource, metrics)\n        \n        # 5. Retornar oportunidade\n        return Opportunity(\n            opportunity_id=f\"opp-{uuid.uuid4()}\",\n            rule_id=self.rule_id,\n            title=self.title,\n            estimated_monthly_savings=monthly_savings,\n            currency=\"USD\",\n            risk_level=risk_level,\n            confidence_level=confidence_level,\n            resource=resource,\n            remediation_command=f\"aws ec2 delete-volume --volume-id {resource.resource_id} --region {resource.region}\",\n        )\n    \n    def _is_detached(self, resource: CloudResource) -> bool:\n        # Lógica específica de detecção\n        return resource.get_tag(\"AttachmentState\") == \"available\"\n    \n    def _assess_risk(self, resource: CloudResource, metrics: MetricSummary) -> RiskLevel:\n        # Lógica de risco: snapshots recentes? tags de backup?\n        if resource.get_tag(\"DoNotDelete\") or resource.get_tag(\"Backup\"):\n            return RiskLevel.HIGH\n        return RiskLevel.LOW\n    \n    def _assess_confidence(self, resource: CloudResource, metrics: MetricSummary) -> ConfidenceLevel:\n        # Confiança baseada em qualidade de dados\n        if metrics.data_points >= 7:  # Pelo menos uma semana de dados\n            return ConfidenceLevel.HIGH\n        return ConfidenceLevel.MEDIUM\n```

### Registro
```python
# providers/aws/__init__.py
def register_aws_provider(registry: InefficiencyRegistry = default_registry) -> None:\n    # ... registrar collectors, metrics, pricing ...\n    registry.register_rule(InactiveDetachedEBSVolumeRule())\n```

### Execução no Scanner
```python
# engine/scanner.py\nfor rule in rules:  # rules para este resource_type\n    try:\n        opp = rule.evaluate(\n            resource=resource,\n            metrics_provider=metrics_provider,\n            pricing_provider=pricing_provider,\n            lookback_days=lookback_days,\n        )\n        if opp:\n            all_opportunities.append(opp)\n    except Exception as exc:\n        logger.error(f\"Error evaluating rule {rule.rule_id}: {exc}\")\n        errors.append({...})\n```\n\n## Rationale\n\n1. **Separação de Responsabilidades**: Cada regra é independente\n2. **Extensibilidade**: Adicionar nova regra = implementar interface + registrar\n3. **Testabilidade**: Cada regra testada isoladamente com mocks\n4. **Determinismo**: Regras sem side effects, saída previsível\n5. **Auditabilidade**: Cada oportunidade rastreável para qual regra a detectou\n\n## Consequences\n\n### Positive\n- ✅ Fácil adicionar novas regras sem modificar scanner\n- ✅ Cada regra pode ser testada isoladamente\n- ✅ Regras agnósticas ao formato de saída\n- ✅ Possível paralelizar avaliação de múltiplas regras\n- ✅ Histórico de qual regra gerou cada oportunidade\n\n### Negative\n- ❌ Boilerplate: Cada regra requer classe + implementação de interface\n- ❌ Debugging: Erros em regras podem ser silenciosos (caught e logged)\n- ❌ Complexidade: Lógica de risco/confiança pode ser complicada\n- ❌ Manutenção: Regras precisam ser atualizadas quando critérios mudam\n\n## Alternatives Considered\n\n### 1. Funções Lambda (Simpler)\n```python\ndef inactive_ebs_rule(resource, metrics_provider, pricing_provider):\n    if not is_detached(resource):\n        return None\n    # ... avaliação\n    return Opportunity(...)\n\nrules = [inactive_ebs_rule, ...]\nfor rule in rules:\n    opp = rule(resource, metrics_provider, pricing_provider)\n```\n**Rejeitado**: Sem type hints, sem estrutura. Difícil debugar qual função é qual.\n\n### 2. Dicionários de Configuração\n```python\nrules = [\n    {\n        \"id\": \"AWS-EBS-001\",\n        \"title\": \"Inactive EBS\",\n        \"check\": lambda r: r.get_tag(\"AttachmentState\") == \"available\",\n        \"calculate_savings\": lambda r, p: ...,\n    },\n    ...\n]\n```\n**Rejeitado**: Sem type checking, difícil rastrear qual dict é qual.\n\n### 3. Declarativo (YAML/JSON)\n```yaml\nrules:\n  - id: AWS-EBS-001\n    type: EBS_VOLUME\n    checks:\n      - field: attachment_state\n        operator: equals\n        value: available\n      - metric: io_ops\n        operator: less_than\n        value: 0\n```\n**Rejeitado**: Menos flexível que código imperativo. Cálculos complexos não conseguem ser expressados.\n\n## Related Decisions\n\n- **ADR-0001**: Strategy Pattern que habilita regras\n- **ADR-0002**: Registry Pattern registra regras\n- **ADR-0009**: Output Formatters formatam oportunidades geradas por regras\n\n## Implementation References\n\n### Key Files\n- `src/cloud_resource_inefficiency/core/rule.py`\n  - `BaseInefficiencyRule` interface\n- `src/cloud_resource_inefficiency/providers/aws/rules/ebs_inactive_detached.py`\n  - `InactiveDetachedEBSVolumeRule` implementação\n- `src/cloud_resource_inefficiency/providers/gcp/rules/gcs_inactive.py`\n  - `InactiveGCSBucketRule` implementação\n- `src/cloud_resource_inefficiency/providers/azure/rules/managed_disk_inactive.py`\n  - `InactiveDetachedManagedDiskRule` implementação\n\n### Rule Lifecycle\n```\n1. Rule registrada em registry (via register_aws_provider)\n2. Scanner descobre regra via registry.get_rules_for_resource_type()\n3. Scanner chama rule.evaluate() para cada recurso\n4. Rule retorna Opportunity (ou None)\n5. Scanner coleta todas as oportunidades\n6. Oportunidades formatadas e reportadas\n```\n\n## Notes\n\n- **Regra vs Detector vs Analyzer**: Neste projeto, termo \"rule\" é sinônimo de \"detector\" ou \"analyzer\"\n- **Múltiplas Regras por Resource Type**: Um resource type pode ter múltiplas regras (ex: AWS EBS pode ter regras para inativo, não encriptado, snapshots antigos, etc.)\n- **Ordem de Avaliação**: Regras são avaliadas sequencialmente. Se desempenho for problema, paralelizar com thread pool\n"