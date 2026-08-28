# ADR-0010: Python 3.9+ with Type Hints

## Status
Accepted

## Context

Python foi historicamente uma linguagem **dinamicamente tipada**:
```python
# Sem type hints (passado)
def get_metrics(resource, metric_names, lookback_days):
    # Tipo de resource? De metric_names? Retorna o quê?
    return client.get_metric_statistics(...)
```

Problemas sem type hints:
- Erros descobertos em runtime (ex: AttributeError em produção)
- IDE não consegue fazer autocomplete
- Refactoring é perigoso (mudar assinatura quebra callers silenciosamente)
- Documentação informal (docstrings)

Type hints (PEP 484) resolvem:
```python
# Com type hints
def get_metrics(
    resource: CloudResource,
    metric_names: List[str],
    lookback_days: int
) -> MetricSummary:
    \"\"\"Type information explícita\"\"\"
    return client.get_metric_statistics(...)
```

Benefícios:
1. **Type Checking**: mypy `--strict` detecta erros antes de deploy
2. **IDE Support**: Autocomplete, refactoring seguro
3. **Documentação**: Tipos são documentação viva
4. **Refactoring**: Mudanças quebram early (CI/CD, não produção)

## Decision

Adotar **Python 3.9+** com **100% type hints** verificados por **mypy --strict**:

### Versões Suportadas
```toml
# pyproject.toml
requires-python = ">=3.9"

classifiers = [
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
```

Python 3.9 porque:
- Generics embutidos: `list[str]` ao invés de `List[str]` (3.9+)
- Dict merge operator: `dict1 | dict2` (3.9+)
- Type hints em decoradores (3.10+) é nice-to-have, não mandatory

### Type Hints em Todos os Locais
```python
# ✅ Bom: Type hints completos
from typing import Optional, Dict, List, Any
from datetime import datetime

class CloudResource:
    def __init__(
        self,
        resource_id: str,
        resource_type: ResourceType,
        region: str,
        tags: Dict[str, str] | None = None,
    ) -> None:\n        self.resource_id = resource_id\n        self.resource_type = resource_type\n        self.region = region\n        self.tags = tags or {}\n    \n    def get_tag(self, key: str, default: str | None = None) -> str | None:\n        return self.tags.get(key, default)\n\n# ✅ Bom: Function type hints\ndef collect_resources(\n    region: str,\n    resource_type: ResourceType,\n) -> list[CloudResource]:\n    \"\"\"Coleta recursos de um tipo específico em uma região.\"\"\"\n    # ...\n    return resources\n\n# ✅ Bom: Lambda com type hints (typing.Callable)\nfrom typing import Callable\n\nfilter_func: Callable[[CloudResource], bool] = lambda r: r.region == \"us-east-1\"\nfiltered = [r for r in resources if filter_func(r)]\n\n# ❌ Ruim: Sem type hints\ndef collect_resources(region, resource_type):\n    return resources\n\n# ❌ Ruim: Tipos parciais\ndef collect_resources(region: str, resource_type) -> list:  # resource_type sem tipo\n    return resources\n```\n\n### CI/CD com mypy --strict\n```bash\n# .github/workflows/type-check.yml\n- name: Run mypy type checker\n  run: |\n    pip install mypy\n    mypy --strict src/\n```\n\n### mypy Config\n```ini\n# mypy.ini ou [tool.mypy] em pyproject.toml\n[mypy]\npython_version = 3.9\nwarn_return_any = True\nwarn_unused_configs = True\ndisallow_untyped_defs = True  # Strict\ndisallow_incomplete_defs = True\ndisallow_untyped_decorators = True\nno_implicit_optional = True\nwarn_redundant_casts = True\nwarn_unused_ignores = True\nwarn_no_return = True\n```\n\n## Rationale\n\n1. **Error Prevention**: Erros detectados em CI/CD, não em produção\n2. **IDE/Editor Support**: Autocomplete, inline documentation, refactoring\n3. **Self-Documenting**: Código é documentado pelos tipos\n4. **Performance**: Sem runtime overhead (type hints são removidos em bytecode)\n5. **Maintainability**: Refactorings seguros, menos regressões\n6. **Industry Standard**: Projetos modernos usam type hints (FastAPI, Django, etc.)\n\n## Consequences\n\n### Positive\n- ✅ Erros descobertos antes de runtime\n- ✅ IDE autocomplete funciona perfeitamente\n- ✅ Refactoring seguro (mypy detecta chamadas inválidas)\n- ✅ Código auto-documentado (tipos como documentação)\n- ✅ Integração com ferramentas (pylint, pydantic, FastAPI)\n- ✅ Profissionalismo (expectativa em projetos sérios)\n\n### Negative\n- ❌ Verbosidade: Mais código para escrever\n- ❌ Learning curve: Desenvolvedores precisa aprender typing\n- ❌ Boilerplate: Imports de typing são chatos\n- ❌ Performance em desenvolvimento: mypy checking adiciona tempo ao CI\n- ❌ Some edge cases: mypy às vezes tem bugs ou requer workarounds\n\n## Alternatives Considered\n\n### 1. Type Hints Opcionais (Gradual Typing)\n```python\n# type hints em alguns arquivos, não em todos\ndef collect_resources(region: str):  # Sem return type\n    return resources\n```\n**Rejeitado**: Inconsistência. Metade do código tipado, metade não. Confuso.\n\n### 2. Apenas Type Comments (PEP 484 Pre-Syntax)\n```python\ndef collect_resources(\n    region,  # type: str\n    resource_type,  # type: ResourceType\n):  # type: (...) -> list[CloudResource]\n    return resources\n```\n**Rejeitado**: Verboso, obsoleto (syntax 3.5+). Prefer to native syntax.\n\n### 3. Runtime Type Checking com Pydantic\n```python\nfrom pydantic import BaseModel\n\nclass CollectRequest(BaseModel):\n    region: str\n    resource_type: ResourceType\n\ndef collect_resources(req: CollectRequest) -> list[CloudResource]:\n    # Runtime validation\n    return resources\n```\n**Adotado Parcialmente**: Pydantic é ótimo para API validation, mas overkill para lógica interna.\n\n### 4. Sem Type Hints (Dynamic Typing Puro)\n```python\ndef collect_resources(region, resource_type):\n    return resources\n```\n**Rejeitado**: Erros descobertos em runtime. Refactoring perigoso.\n\n## Related Decisions\n\n- **ADR-0003**: DTOs que são type-hint-friendly\n- **ADR-0014**: CI/CD que valida tipos com mypy\n- **ADR-0015**: Property-Based Testing complementa type checking\n\n## Implementation References\n\n### Key Files\n- `src/cloud_resource_inefficiency/core/interfaces.py` - Type hints em interfaces\n- `src/cloud_resource_inefficiency/core/models.py` - Type hints em DTOs\n- `src/cloud_resource_inefficiency/engine/scanner.py` - Type hints em orchestration\n- `mypy.ini` - Configuração mypy --strict\n- `.github/workflows/type-check.yml` - CI/CD type checking\n\n### Type Hints em Prática\n\n```python\n# core/models.py\nfrom dataclasses import dataclass\nfrom datetime import datetime\nfrom enum import Enum\nfrom typing import Dict, List, Optional\n\nclass ResourceType(Enum):\n    AWS_EBS_VOLUME = \"aws_ebs_volume\"\n    GCP_GCS_BUCKET = \"gcp_gcs_bucket\"\n    AZURE_MANAGED_DISK = \"azure_managed_disk\"\n\n@dataclass\nclass CloudResource:\n    resource_id: str\n    resource_type: ResourceType\n    provider: CloudProvider\n    region: str\n    tags: Dict[str, str]\n    \n    def get_tag(self, key: str, default: Optional[str] = None) -> Optional[str]:\n        return self.tags.get(key, default)\n\n# interfaces.py\nfrom abc import ABC, abstractmethod\nfrom typing import Any, List\n\nclass BaseResourceCollector(ABC):\n    @abstractmethod\n    def collect(self, region: str, **kwargs: Any) -> List[CloudResource]:\n        \"\"\"Coleta recursos do cloud provider\"\"\"\n        pass\n```\n\n### mypy --strict Output\n```bash\n$ mypy --strict src/\nsuccess: no issues found in 45 files\n```\n\n## Notes\n\n- **Python 3.9 Idiomático**: Use `list[str]` ao invés de `List[str]` (3.9+)\n- **Optional**: Use `X | None` ao invés de `Optional[X]` (3.10+)\n- **Type Narrowing**: mypy é smart sobre type guards:\n  ```python\n  if isinstance(resource, CloudResource):\n      print(resource.region)  # mypy sabe que resource é CloudResource aqui\n  ```\n- **Ignoring Type Errors**: Use `# type: ignore` apenas como último recurso\n- **TypeVar para Generics**: Para funções que trabalham com múltiplos tipos\n  ```python\n  T = TypeVar('T', CloudResource, Opportunity)\n  def process(item: T) -> T:\n      return item\n  ```\n"