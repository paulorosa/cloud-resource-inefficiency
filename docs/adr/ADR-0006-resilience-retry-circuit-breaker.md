# ADR-0006: Resilience with Retry and Circuit Breaker

## Status
Accepted

## Context

Chamadas às APIs cloud frequentemente falham temporariamente:
- **Transient Errors**: Throttling (429), temporary unavailability (503), timeouts
- **Retryable**: Estes erros desaparecem se tentarmos novamente
- **Sem Retry**: Scan falha prematuramente
- **Com Retry Cego**: Possível amplificar problema (cascata de falhas)

Exemplos de falhas reais:
```
AWS CloudWatch: "ThrottlingException: Rate exceeded"
GCP Monitoring: "RESOURCE_EXHAUSTED: 429 Too Many Requests"
Azure Monitor: "503 Service Unavailable"
```

Padrões de resiliência:
1. **Retry com Exponential Backoff**: Tenta 3x com espera crescente
2. **Circuit Breaker**: Se muitas falhas consecutivas, para de tentar (falha rápido)

Sem circuit breaker:
```
Falha 1: retry após 0.1s ❌
Falha 2: retry após 0.2s ❌
Falha 3: retry após 0.4s ❌
Falha 4: retry após 0.8s ❌
Falha 5: retry após 1.6s ❌
... 100 falhas depois, scan ainda tentando...
```

Com circuit breaker:
```
Falha 1: retry após 0.1s ❌
Falha 2: retry após 0.2s ❌
Falha 3: retry após 0.4s ❌
Falha 4: retry após 0.8s ❌
Falha 5: CIRCUIT OPEN ⛔ Falha rápido, economiza tempo e recursos
```

## Decision

Implementar **Exponential Backoff + Circuit Breaker** sem dependências externas:

### Exponential Backoff (em BaseResourceCollector, BaseMetricsProvider, BasePricingProvider)
```python
# core/resilience.py
def retry_with_backoff(func: Callable, max_attempts: int = 3, initial_delay: float = 0.1) -> Any:
    """Executa func com retry e exponential backoff"""
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except (TimeoutError, ConnectionError, ThrottlingError) as e:
            last_exception = e
            if attempt < max_attempts:
                delay = initial_delay * (2 ** (attempt - 1))  # 0.1s, 0.2s, 0.4s
                logger.warning(f"Retry attempt {attempt}/{max_attempts} após {delay}s: {e}")
                time.sleep(delay)
            else:
                logger.error(f"Falha após {max_attempts} tentativas: {e}")
    
    raise last_exception
```

### Circuit Breaker
```python
# core/resilience.py
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold  # Abrir após 5 falhas
        self.recovery_timeout = recovery_timeout  # Tentar novamente após 60s
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED -> OPEN -> HALF_OPEN -> CLOSED
        self._lock = threading.Lock()
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        with self._lock:
            if self.state == "OPEN":
                # Circuito aberto, falha rápido
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    # Tentar recovery
                    self.state = "HALF_OPEN"
                    logger.info("CircuitBreaker: Tentando recovery...")
                else:
                    raise CircuitBreakerException("Circuito aberto, falhe rápido")
        
        try:
            result = func(*args, **kwargs)
            
            with self._lock:
                if self.state == "HALF_OPEN":
                    # Recovery bem-sucedido
                    self.state = "CLOSED"
                    self.failure_count = 0
                    logger.info("CircuitBreaker: Recuperado, circuito fechado")
            
            return result
        
        except Exception as e:
            with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"
                    logger.error(f"CircuitBreaker: Aberto após {self.failure_count} falhas")
            
            raise
```

### Uso integrado em providers
```python
# providers/aws/metrics/cloudwatch.py
class AWSCloudWatchMetricsProvider(BaseMetricsProvider):
    def __init__(self):
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
    
    def get_metrics(self, resource: CloudResource, ...) -> MetricSummary:
        def fetch():
            client = self.client_factory.get_client('cloudwatch', resource.region)
            response = client.get_metric_statistics(...)
            return self._parse_metrics(response)
        
        # 1. Circuit Breaker
        return self.circuit_breaker.call(
            # 2. Retry com backoff
            lambda: retry_with_backoff(fetch, max_attempts=3)
        )
```

Estados do Circuit Breaker:
```
CLOSED (normal)
  ↓ (5+ falhas)
OPEN (falha rápido)
  ↓ (após 60s)
HALF_OPEN (testando recovery)
  ↓ (sucesso)
CLOSED (normal)
```

## Rationale

1. **Sem Dependências**: Implementação própria, usa apenas stdlib
2. **Resiliência Verificada**: Padrão battle-tested em production systems
3. **Fail-Fast**: Circuit breaker evita desperdício de recursos em falhas sistemáticas
4. **Retry Inteligente**: Exponential backoff evita amplificar problemas
5. **Observabilidade**: Logging claro sobre tentativas e estados
6. **Thread-Safe**: Locks garantem consistência em ambientes multi-threaded

## Consequences

### Positive
- ✅ Aplicação tolera falhas transientes automaticamente
- ✅ Evita cascata de falhas (fail-fast economiza tempo)
- ✅ Recuperação automática quando serviço volta online
- ✅ Logging claro para troubleshooting
- ✅ Sem dependência de bibliotecas externas

### Negative
- ❌ Pode mascarar erros reais (falha de autenticação será retried)
- ❌ Delay adicional em cada retry (usuário percebe latência aumentada)
- ❌ Circuit breaker pode ficar "travado" se threshold é muito baixo
- ❌ Debugging complexo: "Por que falhou após 3 tentativas?"
- ❌ Métricas de erro podem ser imprecisas (tentativa 1 vs tentativa 3)

## Alternatives Considered

### 1. Retry com Jitter (Melhor que Exponential Backoff Puro)
```python
import random
delay = initial_delay * (2 ** attempt) + random.uniform(0, 1)
# Evita "thundering herd" quando múltiplos clientes retentam ao mesmo tempo
```
**Adotado Parcialmente**: Pode ser adicionado como otimização futura se jitter for necessário (ex: batches de requisições).

### 2. Apenas Retry, Sem Circuit Breaker
```python
def get_metrics(self, resource: CloudResource, ...) -> MetricSummary:
    return retry_with_backoff(
        lambda: self.client.get_metrics(...),
        max_attempts=3
    )
```
**Rejeitado Parcialmente**: Funciona para falhas transientes, mas sem circuit breaker permite cascata de falhas. Em larga escala (1000s de recursos), sem circuit breaker o scan todo falha.

### 3. Polly Pattern (C# style)
```python
from pybreaker import CircuitBreaker
circuit_breaker = CircuitBreaker(listeners=[...])

@circuit_breaker
def get_metrics(...):
    return client.get_metrics(...)
```
**Rejeitado**: Dependência externa (`pybreaker`). Implementação própria fornece mais controle.

### 4. Sem Resiliência (Fail Fast)
```python
def get_metrics(self, resource: CloudResource, ...) -> MetricSummary:
    return self.client.get_metrics(...)  # Se falhar, falha
```
**Rejeitado**: Scan falha em qualquer erro transiente. Experiência ruim para usuário.

## Related Decisions

- **ADR-0004**: Async-First complementa retry (async pode fazer retry em background)
- **ADR-0005**: Caching complementa resilience (cache hit evita falha)

## Implementation References

### Key Files
- `src/cloud_resource_inefficiency/core/resilience.py`
  - `CircuitBreakerException: Exception`
  - `CircuitBreaker: class` com estados CLOSED/OPEN/HALF_OPEN
  - `retry_with_backoff(func, max_attempts, initial_delay): def`
- `src/cloud_resource_inefficiency/providers/aws/metrics/cloudwatch.py`
  - `AWSCloudWatchMetricsProvider` usa `CircuitBreaker` e `retry_with_backoff`
- `src/cloud_resource_inefficiency/providers/gcp/metrics/monitoring.py`
  - `GCPMonitoringMetricsProvider` usa `CircuitBreaker` e `retry_with_backoff`
- `src/cloud_resource_inefficiency/providers/aws/pricing/aws_pricing.py`
  - `AWSPricingProvider` usa `CircuitBreaker` para AWS Pricing API

### Configuração Padrão
```python
# Retry: 3 tentativas, exponential backoff 0.1s -> 0.2s -> 0.4s
retry_with_backoff(func, max_attempts=3, initial_delay=0.1)

# Circuit Breaker: Abrir após 5 falhas, tentar recovery após 60s
CircuitBreaker(failure_threshold=5, recovery_timeout=60)
```

### Exemplo de Execução
```python
try:
    metrics = cloudwatch_provider.get_metrics(resource, lookback_days=14)
except Exception as e:
    # Sem circuit breaker: Falha imediata
    # Com circuit breaker: Falha rápido se circuito aberto, ou falha após 3 retries
    logger.error(f"Falha ao obter métricas: {e}")
```

## Notes

- **Que erros são retryable?** Apenas errors transientes (timeout, 503, 429). Erros permanentes (401, 404) NÃO devem ser retried indefinidamente
- **Threshold do Circuit Breaker**: 5 falhas é conservador. Aumentar se falsos positivos forem comuns
- **Recovery Timeout**: 60 segundos é razoável. Aumentar se serviços levam mais tempo para recuperar
- **Observabilidade**: Adicionar métricas (Prometheus) para: retry_count, circuit_breaker_state, failure_rate
