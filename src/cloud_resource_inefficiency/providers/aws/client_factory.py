"""Boto3 Client and Session factory with dependency injection and caching."""

import threading
from typing import Any, Dict, Optional
import boto3
from botocore.config import Config


class AWSClientFactory:
    """Factory for creating and reusing boto3 clients across regions and sessions."""

    def __init__(
        self,
        session: Optional[boto3.Session] = None,
        profile_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
        botocore_config: Optional[Config] = None,
    ) -> None:
        if session is not None:
            self._session = session
        elif profile_name:
            self._session = boto3.Session(profile_name=profile_name)
        elif aws_access_key_id and aws_secret_access_key:
            self._session = boto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
            )
        else:
            self._session = boto3.Session()

        self._config = botocore_config or Config(retries={"max_attempts": 3, "mode": "standard"})
        self._client_cache: Dict[str, Any] = {}
        self._lock = threading.Lock()

    @property
    def session(self) -> boto3.Session:
        return self._session

    def get_client(self, service_name: str, region_name: Optional[str] = None) -> Any:
        """Returns a cached or new boto3 client for the given service and region."""
        cache_key = f"{service_name}:{region_name or 'default'}"
        with self._lock:
            if cache_key not in self._client_cache:
                kwargs: Dict[str, Any] = {"config": self._config}
                if region_name:
                    kwargs["region_name"] = region_name
                self._client_cache[cache_key] = self._session.client(service_name, **kwargs)
            return self._client_cache[cache_key]

    def __repr__(self) -> str:
        return f"<AWSClientFactory session={id(self._session)} cached_clients={len(self._client_cache)}>"
