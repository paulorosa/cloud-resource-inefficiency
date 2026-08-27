# ADR-0003: Immutable Data Transfer Objects with Dataclasses

## Status
Accepted

## Context

O projeto manipula dados que fluem entre componentes:
- `CloudResource`: Metadados sobre um recurso cloud (ID, region, tags, etc.)
- `MetricSummary`: Agregações de métricas (I/O ops, latência, etc.)
- `PricingDetails`: Dados de precificação (hourly_rate, monthly_cost, etc.)
- `Opportunity`: Oportunidade de economia (rule_id, savings, risk_level, etc.)
- `ScanResult`: Resultado final de um scan

Estes dados são:
1. **Compartilhados entre múltiplos componentes** (scanner, formatadores, exportadores)
2. **Serializados** para JSON, Markdown, texto
3. **Potencialmente modificados acidentalmente** se mutáveis

Sem imutabilidade, riscos:
- Estado compartilhado corrompido entre threads
- Bugs difíceis de rastrear (modificações inesperadas)
- Serialização inconsistente

## Decision

Usar **`@dataclass`** do Python (padrão library, sem dependências) com `frozen=True` para dados críticos:

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

@dataclass(frozen=True)
class CloudResource:
    """Representação imutável de um recurso cloud"""
    resource_id: str
    resource_type: ResourceType
    provider: CloudProvider
    region: str
    tags: Dict[str, str] = field(default_factory=dict)
    
    def get_tag(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self.tags.get(key, default)

@dataclass(frozen=True)
class Opportunity:
    """Representação imutável de uma oportunidade de economia"""
    opportunity_id: str
    rule_id: str
    title: str
    estimated_monthly_savings: float
    risk_level: RiskLevel
    confidence_level: ConfidenceLevel
    resource: CloudResource
    remediation_command: str

@dataclass
class ScanResult:
    """Resultado mutável de um scan (construído incrementalmente)"""
    opportunities: List[Opportunity] = field(default_factory=list)
    scanned_resources_count: int = 0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    errors: List[Dict[str, Any]] = field(default_factory=list)
```

## Rationale

1. **Segurança por Design**: `frozen=True` impede modificações acidentais após construção
2. **Sem Dependências Externas**: `@dataclass` é parte da stdlib (Python 3.7+)
3. **Type Safety**: Type hints integrados, facilita mypy `--strict`
4. **Serialização Trivial**: `@dataclass` funciona perfeito com `json.dumps()`, `asdict()`
5. **Performance**: Dataclasses compiladas em C são tão rápidas quanto classes manuais
6. **Hashability**: DTOs imutáveis podem ser chaves em dicionários/sets (quando apropriado)
7. **Comparação Automática**: `__eq__` gerado automaticamente (perfeito para testes)
8. **Representação Legível**: `__repr__` gerado automaticamente (melhor debugging)

## Consequences

### Positive
- ✅ Impossibilidade de modificar DTOs após criação (thread-safe)
- ✅ Código mais legível e seguro
- ✅ Testes mais simples: comparação direta com objetos esperados
- ✅ Serialização trivial para JSON/dict
- ✅ Melhor performance de cache (DTOs imutáveis são hashable)
- ✅ Type hints + mypy = detecção de erros em tempo de compilação

### Negative
- ❌ Mutabilidade precisa ser explícita em tipos container (lists, dicts)
- ❌ Modificação requer criar nova instância (mais alocações de memória)
- ❌ Debugging pode ser menos direto se nested structures forem complexas
- ❌ `field(default_factory=dict)` é verbose comparado com `None`

## Alternatives Considered

### 1. Named Tuples
```python
from typing import NamedTuple

class CloudResource(NamedTuple):
    resource_id: str
    resource_type: ResourceType
    provider: CloudProvider
    region: str
    tags: Dict[str, str] = {}
```
**Rejeitado**: Menos flexível que dataclasses. Sem suporte direto para métodos com lógica complexa. Syntax menos intuitiva para novos desenvolvedores.

### 2. Pydantic Models
```python
from pydantic import BaseModel

class CloudResource(BaseModel):
    resource_id: str
    resource_type: ResourceType
    # ... com validação automática
    
    class Config:
        frozen = True
```
**Rejeitado**: Adiciona dependência externa (`pydantic`). Over-engineered para este caso (validação não é necessária em DTOs internos). Serialização json adiciona overhead.

### 3. Classes Manuais com `__slots__`
```python
class CloudResource:
    __slots__ = ['resource_id', 'resource_type', ...]
    
    def __init__(self, resource_id: str, ...):
        self.resource_id = resource_id
        # ...
```
**Rejeitado**: Boilerplate excessivo. Não ganha performance significativa. Sem `__eq__` gerado.

### 4. Sem Imutabilidade (Mutable Classes)
```python
class CloudResource:
    def __init__(self, resource_id: str, ...):
        self.resource_id = resource_id
        self.resource_type = resource_type
        # ... sem frozen
```
**Rejeitado**: Violaria thread-safety. Erros silenciosos de mutação. Testes mais complexos.

## Related Decisions

- **ADR-0010**: Type Hints que decoram os DTOs
- **ADR-0009**: Output Formatters que serializam DTOs

## Implementation References

### Key Files
- `src/cloud_resource_inefficiency/core/models.py` - Definição de todos os DTOs
  - `CloudResource(frozen=True)`
  - `MetricSummary(frozen=True)`
  - `PricingDetails(frozen=True)`
  - `Opportunity(frozen=True)`
  - `ScanResult` (mutável, construído incrementalmente)

### Example Usage
```python
# Criação
resource = CloudResource(
    resource_id="vol-12345",
    resource_type=ResourceType.AWS_EBS_VOLUME,
    provider=CloudProvider.AWS,
    region="us-east-1",
    tags={"Environment": "prod"}
)

# Acesso seguro
env = resource.get_tag("Environment")  # "prod"

# Serialização automática
import json
from dataclasses import asdict
json_str = json.dumps(asdict(resource))

# Comparação (testing)
assert resource == expected_resource

# Tentativa de modificação falha
try:
    resource.resource_id = "vol-99999"  # FrozenInstanceError
except Exception as e:
    print(f"Imutabilidade protegida: {e}")
```

### Estrutura de Dados
```
CloudResource (frozen)
├─ resource_id: str
├─ resource_type: ResourceType
├─ provider: CloudProvider
├─ region: str
├─ tags: Dict[str, str]
└─ get_tag(key: str, default: Optional[str]) -> Optional[str]

Opportunity (frozen)
├─ opportunity_id: str
├─ rule_id: str
├─ title: str
├─ estimated_monthly_savings: float
├─ risk_level: RiskLevel
├─ confidence_level: ConfidenceLevel
├─ resource: CloudResource (referência)
└─ remediation_command: str

ScanResult (mutável, construído)
├─ opportunities: List[Opportunity]
├─ scanned_resources_count: int
├─ start_time: datetime
├─ end_time: datetime
└─ errors: List[Dict[str, Any]]
```

## Notes

- **Mutabilidade de Collections**: Mesmo com `frozen=True`, o dict/list *interno* pode ser mutado:
  ```python
  resource.tags['NewKey'] = 'NewValue'  # Funciona! (não recomendado)
  ```
  Solução: Usar `MappingProxyType` ou `tuple` se imutabilidade total for requerida (performance trade-off).

- **Evolução Futura**: Se for necessário mutar dados, usar pattern **Builder** ou **copy.replace()** (Python 3.10+):
  ```python
  updated_opp = dataclasses.replace(opp, estimated_monthly_savings=opp.estimated_monthly_savings * 1.1)
  ```
