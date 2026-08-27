# ADR-0002: Registry-Based Component Management

## Status
Accepted

## Context

Com o Strategy Pattern (ADR-0001), múltiplas implementações de coletores, provedores de métricas e regras precisam ser **descobertas** e **conectadas** em tempo de execução.

O `InefficiencyScanner` precisa:
1. Encontrar o `BaseResourceCollector` correto para um `ResourceType` específico
2. Encontrar o `BaseMetricsProvider` correspondente ao `CloudProvider`
3. Encontrar o `BasePricingProvider` correspondente ao `CloudProvider`
4. Encontrar as `BaseInefficiencyRule` aplicáveis a um `ResourceType`

Sem um mecanismo centralizado de registro, seria necessário:
- Hardcoded imports em múltiplos locais
- Factory methods gigantes com lógica condicional
- Complexo para testes (mock todas as dependências manualmente)

## Decision

Implementar um **Registry Pattern** com classe `InefficiencyRegistry` centralizada:

```python
# core/registry.py
class InefficiencyRegistry:
    def __init__(self) -> None:
        self._collectors: Dict[ResourceType, BaseResourceCollector] = {}
        self._metrics_providers: Dict[CloudProvider, BaseMetricsProvider] = {}
        self._pricing_providers: Dict[CloudProvider, BasePricingProvider] = {}
        self._rules: Dict[str, BaseInefficiencyRule] = {}
        self._resource_type_to_rules: Dict[ResourceType, List[BaseInefficiencyRule]] = {}
    
    def register_collector(self, resource_type: ResourceType, collector: BaseResourceCollector) -> None:
        self._collectors[resource_type] = collector
    
    def register_rule(self, rule: BaseInefficiencyRule) -> None:
        self._rules[rule.rule_id] = rule
        # Manter índice por resource_type para lookup rápido
        if rule.target_resource_type not in self._resource_type_to_rules:
            self._resource_type_to_rules[rule.target_resource_type] = []
        self._resource_type_to_rules[rule.target_resource_type].append(rule)
    
    def get_collector(self, resource_type: ResourceType) -> Optional[BaseResourceCollector]:
        return self._collectors.get(resource_type)
    
    def get_rules_for_resource_type(self, resource_type: ResourceType) -> List[BaseInefficiencyRule]:
        return self._resource_type_to_rules.get(resource_type, [])
```

Um `default_registry` global é inicializado e exportado do módulo `core`:

```python
# core/__init__.py
default_registry = InefficiencyRegistry()

# Provedores auto-registram seus componentes:
# providers/aws/__init__.py
from cloud_resource_inefficiency.core import default_registry

def register_aws_provider(registry: InefficiencyRegistry = default_registry) -> None:
    registry.register_collector(
        ResourceType.AWS_EBS_VOLUME,
        AWSEBSCollector()
    )
    registry.register_metrics_provider(
        CloudProvider.AWS,
        AWSCloudWatchMetricsProvider()
    )
    # ... mais registros
```

## Rationale

1. **Single Responsibility**: Registry é o único responsável por descoberta e registro
2. **Flexibilidade**: Fácil trocar implementações em tempo de execução (ex: diferentes `AWSCloudWatchMetricsProvider` para diferentes regiões)
3. **Testabilidade**: Testes podem criar um `InefficiencyRegistry` limpo e registrar apenas os mocks necessários
4. **Desacoplamento**: `InefficiencyScanner` não conhece implementações concretas, apenas interfaces
5. **Auto-Registro**: Provedores registram-se quando importados (lazy loading possível)
6. **Performance**: Lookup O(1) via dicionários mapeados por tipo

## Consequences

### Positive
- ✅ Centralização de todas as descobertas de componentes em um único local
- ✅ Fácil adicionar/remover componentes sem modificar scanner
- ✅ Suporta múltiplos registries para diferentes cenários (produção, testes, staging)
- ✅ Permite debug e introspecção: `registry.get_all_rules()`, `registry.get_all_collectors()`
- ✅ Suporta padrão **Service Locator** quando apropriado

### Negative
- ❌ Global state (antipadrão em alguns contextos)
- ❌ Possível poluição do registry se múltiplos provedores registram o mesmo tipo
- ❌ Debugging pode ser complexo: "Por que essa regra não foi registrada?"
- ❌ Requer documentação clara sobre quando/como provedores devem registrar-se
- ❌ Circular imports potenciais se não gerenciados cuidadosamente

## Alternatives Considered

### 1. Dependency Injection Container (ex: `injector` library)
```python
from injector import Injector, inject

injector = Injector()
injector.bind(BaseResourceCollector, AWSEBSCollector())
```
**Rejeitado**: Over-engineered para este caso de uso. Adiciona dependência externa. Syntax mais complexo para time pequeno.

### 2. Factory Pattern Puro
```python
class ComponentFactory:
    @staticmethod
    def get_collector(resource_type: ResourceType) -> BaseResourceCollector:
        if resource_type == ResourceType.AWS_EBS_VOLUME:
            return AWSEBSCollector()
        elif resource_type == ResourceType.GCP_GCS_BUCKET:
            return GCSCollector()
```
**Rejeitado**: Não escala bem. Adicionar novo provedor requer modificação da factory. Sem caching de instâncias.

### 3. Importação Explícita em Scanner
```python
# engine/scanner.py
from providers.aws import register_aws_provider
from providers.gcp import register_gcp_provider
from providers.azure import register_azure_provider

# Na inicialização:
if CloudProvider.AWS in providers:
    register_aws_provider()
```
**Adotado Parcialmente**: Mantém registry, mas faz auto-registro condicional baseado em providers especificados (ver ADR-0001 e `InefficiencyScanner.scan()`).

## Related Decisions

- **ADR-0001**: Strategy Pattern define as interfaces que são registradas
- **ADR-0008**: Rule Evaluation Model usa o registry para descobrir regras aplicáveis

## Implementation References

### Key Files
- `src/cloud_resource_inefficiency/core/registry.py` - Implementação da classe `InefficiencyRegistry`
- `src/cloud_resource_inefficiency/core/__init__.py` - Export do `default_registry`
- `src/cloud_resource_inefficiency/providers/aws/__init__.py` - `register_aws_provider()`
- `src/cloud_resource_inefficiency/providers/gcp/__init__.py` - `register_gcp_provider()`
- `src/cloud_resource_inefficiency/providers/azure/__init__.py` - `register_azure_provider()`
- `src/cloud_resource_inefficiency/engine/scanner.py` - Uso do registry para descoberta

### Example Workflow
```
1. InefficiencyScanner.__init__(providers=[AWS, GCP])
   ├─ Detecta AWS em providers
   ├─ Chama register_aws_provider(default_registry)
   │  ├─ Registra AWSEBSCollector → ResourceType.AWS_EBS_VOLUME
   │  ├─ Registra AWSCloudWatchMetricsProvider → CloudProvider.AWS
   │  ├─ Registra AWSPricingProvider → CloudProvider.AWS
   │  └─ Registra InactiveDetachedEBSVolumeRule → default_registry
   └─ Detecta GCP em providers
      └─ Chama register_gcp_provider(default_registry)
         ├─ Registra GCSCollector → ResourceType.GCP_GCS_BUCKET
         ├─ Registra GCPMonitoringMetricsProvider → CloudProvider.GCP
         └─ ... e assim por diante

2. scanner.scan(resource_types=[ResourceType.AWS_EBS_VOLUME])
   ├─ Lookup: registry.get_collector(ResourceType.AWS_EBS_VOLUME)
   │  └─ Retorna AWSEBSCollector
   ├─ Lookup: registry.get_rules_for_resource_type(ResourceType.AWS_EBS_VOLUME)
   │  └─ Retorna [InactiveDetachedEBSVolumeRule]
   └─ Executa coleta e avaliação
```

## Notes

- O `default_registry` é importado como singleton, mas nada impede criar múltiplas instâncias para testes isolados
- Implementação atual verifica se componentes já estão registrados antes de registrar novamente (evita duplicação)
- Possível evolução: Adicionar suporte a **plugins dinâmicos** que registram-se automaticamente
