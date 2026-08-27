"""Factory for lazily creating Azure management clients."""

import threading
from typing import Any, Dict, Optional


class AzureClientFactory:
    """Creates Azure clients using DefaultAzureCredential unless supplied."""

    def __init__(self, subscription_id: Optional[str] = None, credential: Optional[Any] = None) -> None:
        self.subscription_id = subscription_id
        self.credential = credential
        self._client_cache: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def _get_credential(self) -> Any:
        if self.credential is None:
            from azure.identity import DefaultAzureCredential

            self.credential = DefaultAzureCredential()
        return self.credential

    def get_compute_client(self) -> Any:
        if not self.subscription_id:
            raise ValueError("Azure subscription_id is required")
        with self._lock:
            if "compute" not in self._client_cache:
                from azure.mgmt.compute import ComputeManagementClient

                self._client_cache["compute"] = ComputeManagementClient(
                    self._get_credential(), self.subscription_id
                )
            return self._client_cache["compute"]

    def get_monitor_client(self) -> Any:
        if not self.subscription_id:
            raise ValueError("Azure subscription_id is required")
        with self._lock:
            if "monitor" not in self._client_cache:
                from azure.mgmt.monitor import MonitorManagementClient

                self._client_cache["monitor"] = MonitorManagementClient(
                    self._get_credential(), self.subscription_id
                )
            return self._client_cache["monitor"]