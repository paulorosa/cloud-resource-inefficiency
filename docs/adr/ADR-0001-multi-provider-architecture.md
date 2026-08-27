# ADR-0001: Multi-Provider Architecture with Strategy Pattern

## Status
Accepted

## Context

O projeto `cloud-resource-inefficiency` precisa suportar múltiplos provedores cloud (AWS, Azure, GCP) para fornecer uma solução unificada de detecção de oportunidades financeiras e ineficiências de custo. Cada provedor possui:

- **APIs distintas** para coleta de recursos (AWS EC2, Google Cloud SDK, Azure SDK)
- **Modelos de precificação diferentes** (por tipo de instância, região, etc.)
- **Sistemas de monitoramento heterogêneos** (CloudWatch, Cloud Monitoring, Azure Monitor)
- **Estruturas de autenticação específicas** (IAM roles, Service Accounts, DefaultAzureCredential)

A solução deve ser:
- **Extensível**: Fácil adicionar novos provedores sem modificar código existente
- **Testável**: Cada provedor deve ser testável isoladamente
- **Desacoplada**: Mudanças em um provedor não devem afetar outros

## Decision

Implementar o **Strategy Pattern** com interfaces abstratas base:

```python
# core/interfaces.py
class BaseResourceCollector(ABC):
    """Interface para coleta de recursos em um provedor cloud"""
    @abstractmethod
    def collect(self, region: str, **kwargs) -> List[CloudResource]: ...

class BaseMetricsProvider(ABC):
    """Interface para coleta de métricas em um provedor cloud"""
    @abstractmethod
    def get_metrics(self, resource: CloudResource, ...) -> MetricSummary: ...

class BasePricingProvider(ABC):
    """Interface para obtenção de preços em um provedor cloud"""
    @abstractmethod
    def get_pricing_details(self, resource: CloudResource, ...) -> PricingDetails: ...
```

Cada provedor implementa estas interfaces e registra-se em um `InefficiencyRegistry` central. Exemplos:

- **AWS**: `AWSEBSCollector extends BaseResourceCollector`
- **GCP**: `GCSCollector extends BaseResourceCollector`
- **Azure**: `AzureManagedDiskCollector extends BaseResourceCollector`

## Rationale

1. **Separação de Responsabilidades**: Cada provedor encapsula sua lógica específica
2. **Open/Closed Principle**: Aberto para extensão (novos provedores), fechado para modificação (código existente não muda)
3. **Polimorfismo**: `InefficiencyScanner` trabalha com interfaces abstratas, não com tipos concretos
4. **Testabilidade**: Fácil criar mocks de cada interface para testes unitários
5. **Reutilização**: Código comum pode ser abstraído em classes base quando apropriado

## Consequences

### Positive
- ✅ Adição de novo provedor cloud exige apenas nova implementação das interfaces (sem tocar código legado)
- ✅ Cada provedor pode ter sua própria lógica de autenticação, caching, resiliência
- ✅ Regras de detecção (rules) podem ser agnósticas ao provedor
- ✅ Testes unitários podem mockar cada provider isoladamente
- ✅ Suporta versionamento independente de SDKs por provedor (ex: atualizar boto3 sem afetar Google Cloud SDK)

### Negative
- ❌ Boilerplate inicial: Cada novo provedor requer implementação completa de todas as interfaces
- ❌ Possível duplicação de lógica comum entre provedores (resiliência, caching, parsing)
- ❌ Curva de aprendizado mais alta para novos desenvolvedores (precisa entender o padrão Strategy)
- ❌ Debugging mais complexo quando erros ocorrem em camadas abstratas

## Alternatives Considered

### 1. Monolithic Provider Switch
```python
def collect_resources(provider: CloudProvider, region: str) -> List[CloudResource]:
    if provider == CloudProvider.AWS:
        return collect_aws_resources(region)
    elif provider == CloudProvider.GCP:
        return collect_gcp_resources(region)
    elif provider == CloudProvider.AZURE:
        return collect_azure_resources(region)
```
**Rejeitado**: Viola Open/Closed Principle. Adicionar novo provedor requer modificação de todas as funções. Não é escalável.

### 2. Inheritance Hierarchy com Classe Base Única
```python
class CloudProvider:
    def collect_resources(self, region: str) -> List[CloudResource]: ...
    def get_metrics(self, ...) -> MetricSummary: ...
    def get_pricing(self, ...) -> PricingDetails: ...

class AWSProvider(CloudProvider): ...
class GCPProvider(CloudProvider): ...
```
**Rejeitado**: Menos flexível. Força todas as implementações a seguir uma ordem hierárquica rígida. Dificulta composição (ex: usar CloudWatchMetrics com GCPCollector).

### 3. Reflection/Dynamic Loading Puro
```python
# Auto-descoberta de classes em diretórios providers/*/
import importlib
import pkgutil

def auto_register_providers():
    for importer, modname, ispkg in pkgutil.iter_modules(providers.__path__):
        module = importlib.import_module(f"providers.{modname}")
        # Reflection magic...
```
**Rejeitado**: Muito implícito, difícil de debugar. Sem garantias de segurança sobre o que é carregado.

## Related Decisions

- **ADR-0002**: Registry Pattern para registrar e descobrir estratégias
- **ADR-0008**: Rule Evaluation Model usa as interfaces abstratas
- **ADR-0011**: Client Factories são específicas por provedor

## Implementation References

### Key Files
- `src/cloud_resource_inefficiency/core/interfaces.py` - Definição das interfaces abstratas
- `src/cloud_resource_inefficiency/providers/aws/collectors/ebs_collector.py` - Implementação AWS
- `src/cloud_resource_inefficiency/providers/gcp/collectors/gcs_collector.py` - Implementação GCP
- `src/cloud_resource_inefficiency/providers/azure/collectors/managed_disk_collector.py` - Implementação Azure

### Example Usage
```python
from cloud_resource_inefficiency import InefficiencyScanner, CloudProvider

scanner = InefficiencyScanner(
    providers=[CloudProvider.AWS, CloudProvider.GCP, CloudProvider.AZURE],
    regions=["us-east-1", "global", "eastus"]
)

# Scanner automaticamente usa a estratégia correta para cada provedor
result = scanner.scan()
```

## Notes

- O padrão Strategy foi escolhido especificamente para permitir troca de implementação em tempo de execução
- Cada provedor pode ter diferentes níveis de maturidade (ex: AWS está completo, Azure em alpha)
- A arquitetura permite futura evolução para **provider pools** ou **provider quotas** (limitar requisições por provedor)
