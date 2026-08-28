"""Google Cloud Client Factory with dependency injection and caching."""

import threading
from typing import Any, Dict, Optional, cast

from google.cloud import storage, monitoring_v3, logging_v2  # type: ignore[attr-defined]


class GCPClientFactory:
    """Factory for creating and reusing Google Cloud clients."""

    def __init__(
        self,
        project_id: Optional[str] = None,
        credentials: Optional[Any] = None,
    ) -> None:
        """
        Initialize GCP Client Factory.

        Args:
            project_id: GCP project ID. If None, uses default from environment.
            credentials: Google credentials object. If None, uses ADC (Application Default Credentials).
        """
        self.project_id = project_id
        self.credentials = credentials
        self._client_cache: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def get_storage_client(self) -> storage.Client:
        """Returns a cached or new Storage client."""
        cache_key = "storage"
        with self._lock:
            if cache_key not in self._client_cache:
                kwargs: Dict[str, Any] = {}
                if self.project_id:
                    kwargs["project"] = self.project_id
                if self.credentials:
                    kwargs["credentials"] = self.credentials
                self._client_cache[cache_key] = storage.Client(**kwargs)
            return cast(storage.Client, self._client_cache[cache_key])

    def get_monitoring_client(self) -> monitoring_v3.MetricServiceClient:
        """Returns a cached or new Monitoring (Metrics) client."""
        cache_key = "monitoring"
        with self._lock:
            if cache_key not in self._client_cache:
                kwargs: Dict[str, Any] = {}
                if self.credentials:
                    kwargs["credentials"] = self.credentials
                self._client_cache[cache_key] = monitoring_v3.MetricServiceClient(**kwargs)
            return cast(monitoring_v3.MetricServiceClient, self._client_cache[cache_key])

    def get_logging_client(self) -> logging_v2.Client:
        """Returns a cached or new Logging client."""
        cache_key = "logging"
        with self._lock:
            if cache_key not in self._client_cache:
                kwargs: Dict[str, Any] = {}
                if self.project_id:
                    kwargs["project"] = self.project_id
                if self.credentials:
                    kwargs["credentials"] = self.credentials
                self._client_cache[cache_key] = logging_v2.Client(**kwargs)  # type: ignore[no-untyped-call]
            return cast(logging_v2.Client, self._client_cache[cache_key])

    def __repr__(self) -> str:
        return f"<GCPClientFactory project={self.project_id} cached_clients={len(self._client_cache)}>"
