# ADR-0007: Centralized Logging and Configuration

## Status
Accepted

## Context

Aplicação precisa de flexibilidade operacional:
- **Logging**: Diferentes níveis em dev (DEBUG) vs prod (WARNING)
- **Configuração**: Quais provedores ativar, quais regiões scannear, timeouts customizados
- **Troubleshooting**: Logs detalhados para debugar falhas em produção

Abordagens:
1. **Hardcoded**: Difícil debugar, requer recompile
2. **Command-line args**: `python -m scanner --provider aws --regions us-east-1 sa-east-1`
3. **Config files**: YAML/JSON com configurações nomeadas
4. **Environment variables**: Containerization-friendly (Docker, Kubernetes)

Melhor abordagem: **Combinação** de todas (flexibility máxima).

## Decision

Implementar **3 camadas de configuração** com precedência:

### 1. Environment Variables (Mais Alta Precedência)
```bash
# ~/.bashrc ou .env
export CRI_LOG_LEVEL=DEBUG
export CRI_PROVIDERS=aws,gcp
export CRI_REGIONS=us-east-1,sa-east-1,us-west-2
export CRI_LOOKBACK_DAYS=14
export CRI_AWS_REGION_OVERRIDE=us-east-1
export CRI_TIMEOUT_SECONDS=30
```

### 2. Config File (Média Precedência)
```yaml
# config.yaml (ou ~/.config/cloud-resource-inefficiency/config.yaml)
logging:
  level: DEBUG
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

scan:
  providers:
    - aws
    - gcp
  regions:
    - us-east-1
    - sa-east-1
  lookback_days: 14
  timeout_seconds: 30

aws:
  profile: default
  region_override: null

gcp:
  project_id: my-gcp-project
```

### 3. Application Defaults (Mais Baixa Precedência)
```python
# config.py
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_PROVIDERS = [CloudProvider.AWS]
DEFAULT_REGIONS = ["us-east-1"]
DEFAULT_LOOKBACK_DAYS = 14
DEFAULT_TIMEOUT_SECONDS = 30
```

### Implementação
```python
# logging_config.py
import logging
import os
import yaml
from pathlib import Path

class Config:
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or self._find_config_file()
        self._env_vars = os.environ
        self._file_config = self._load_config_file() if self.config_file else {}
    
    def _find_config_file(self) -> Optional[Path]:
        """Procura config.yaml em: ./, ~/.config/, /etc/"""
        candidates = [
            Path("config.yaml"),
            Path.home() / ".config" / "cloud-resource-inefficiency" / "config.yaml",
            Path("/etc") / "cloud-resource-inefficiency" / "config.yaml",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None
    
    def _load_config_file(self) -> Dict:
        if not self.config_file:
            return {}
        with open(self.config_file) as f:
            return yaml.safe_load(f) or {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Precedência: env vars > config file > default"""
        env_key = f"CRI_{key.upper()}"
        
        # 1. Environment variable (highest priority)
        if env_key in self._env_vars:
            return self._parse_value(self._env_vars[env_key])
        
        # 2. Config file
        if key in self._file_config:
            return self._file_config[key]
        
        # 3. Default (lowest priority)
        return default
    
    @staticmethod
    def _parse_value(val: str) -> Any:
        """Converte string env var para tipo apropriado"""
        if val.lower() in ("true", "yes", "1"):
            return True
        elif val.lower() in ("false", "no", "0"):
            return False
        elif val.isdigit():
            return int(val)
        else:
            return val

# Inicializar logging
def configure_logging(config: Config) -> None:
    log_level = config.get("log_level", DEFAULT_LOG_LEVEL)
    log_format = config.get("log_format", DEFAULT_LOG_FORMAT)
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
    )
    
    # Reduzir verbosidade de bibliotecas third-party
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("azure").setLevel(logging.WARNING)
```

### Uso
```python
# main.py
from config import Config
from logging_config import configure_logging

config = Config(config_file="config.yaml")
configure_logging(config)

scanner = InefficiencyScanner(
    providers=config.get("providers", [CloudProvider.AWS]),
    regions=config.get("regions", ["us-east-1"]),
)

result = scanner.scan(
    lookback_days=config.get("lookback_days", 14),
)
```

## Rationale

1. **Flexibilidade**: Múltiplas formas de configurar (CLI, env vars, files)
2. **Docker-Friendly**: Env vars são padrão em containerização
3. **Não Breaking**: Defaults sensatos mantêm compatibilidade
4. **Centralized**: Um único lugar para entender toda configuração
5. **Logging Granular**: DEBUG em dev, WARNING em prod, tudo controlável

## Consequences

### Positive
- ✅ Fácil configurar em diferentes ambientes (dev, staging, prod)
- ✅ Troubleshooting facilitado (aumentar log level sem recompile)
- ✅ Docker/Kubernetes friendly (env vars)
- ✅ Backward compatible (defaults funcionam sem config)
- ✅ Segurança: Env vars não commitadas no Git

### Negative
- ❌ Configuração pode estar espalhada em múltiplos lugares (confuso)
- ❌ Debugging: "Por que meu config não foi carregado?"
- ❌ Ordem de precedência precisa ser documentada
- ❌ Versionamento de config files pode ser complexo

## Alternatives Considered

### 1. Config File ÚNICO (YAML/JSON)
```yaml
# config.yaml (estrutura)
logging:
  level: DEBUG
scan:
  providers: [aws, gcp]
```
**Rejeitado Parcialmente**: Bom, mas sem env vars é difícil em containerização. Adotado como complemento a env vars.

### 2. TOML Config
```toml
# Inspired by Cargo.toml, pyproject.toml
[logging]
level = "DEBUG"

[scan]
providers = ["aws", "gcp"]
```
**Rejeitado**: YAML é mais legível para este caso. TOML é melhor para programmatic config.

### 3. Apenas Environment Variables
```bash
export CRI_LOG_LEVEL=DEBUG
export CRI_PROVIDERS=aws,gcp
```
**Rejeitado Parcialmente**: Funciona para containerização, mas é verboso para local dev. Adotado como camada 1.

### 4. Dataclass Configuration (Type-Safe)
```python
from dataclasses import dataclass

@dataclass
class ScanConfig:
    log_level: str = "INFO"
    providers: List[CloudProvider] = field(default_factory=lambda: [CloudProvider.AWS])
    regions: List[str] = field(default_factory=lambda: ["us-east-1"])
```
**Adotado Parcialmente**: Type-safe, mas sem integração fácil com env vars. Pode ser adicionado futuramente.

## Related Decisions

- **ADR-0010**: Type Hints em configuração
- **ADR-0014**: GitHub Actions usa configuração via env vars

## Implementation References

### Key Files
- `src/cloud_resource_inefficiency/logging_config.py`
  - Setup de logging centralizado
  - `configure_logging(config: Config) -> None`
- `src/cloud_resource_inefficiency/config.py`
  - Classe `Config` com precedência env vars > file > defaults
- `examples/config.yaml`
  - Exemplo de config file

### Config File Location Priority
1. `./config.yaml` (working directory)
2. `~/.config/cloud-resource-inefficiency/config.yaml` (user home)
3. `/etc/cloud-resource-inefficiency/config.yaml` (system)
4. Defaults embutidos na aplicação

### Environment Variables (Prefix: `CRI_`)
```
CRI_LOG_LEVEL=DEBUG
CRI_PROVIDERS=aws,gcp,azure
CRI_REGIONS=us-east-1,sa-east-1,us-west-2
CRI_LOOKBACK_DAYS=14
CRI_TIMEOUT_SECONDS=30
CRI_AWS_PROFILE=production
CRI_GCP_PROJECT_ID=my-project
```

## Example: Initialization in Code
```python
import os
from pathlib import Path
from cloud_resource_inefficiency import InefficiencyScanner, CloudProvider
from cloud_resource_inefficiency.config import Config
from cloud_resource_inefficiency.logging_config import configure_logging

# Opção 1: Auto-detect config file
config = Config()

# Opção 2: Explicit config file
config = Config(config_file=Path("/etc/cri/config.yaml"))

# Configure logging
configure_logging(config)

# Create scanner
scanner = InefficiencyScanner(
    providers=[CloudProvider.AWS, CloudProvider.GCP],
    regions=config.get("regions", ["us-east-1"]),
)

# Scan
result = scanner.scan(
    lookback_days=config.get("lookback_days", 14),
)
```

## Notes

- **Segurança**: Credentials NUNCA devem ser hardcoded. Usar IAM roles (AWS), Service Accounts (GCP), ManagedIdentity (Azure)
- **Logging em Produção**: Considerar enviar logs para centralized system (CloudWatch, Stackdriver, Application Insights)
- **Validation**: Config should be validated na inicialização (valores inválidos detectados early)
- **Auto-Reload**: Possível evolução futura - recarregar config sem restart
