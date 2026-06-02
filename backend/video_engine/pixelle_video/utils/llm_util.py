# Copyright (C) 2025 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
LLM utility functions for model discovery and connection testing.

Uses the standard OpenAI-compatible /v1/models endpoint.
"""

import ipaddress
import http.client
import json
import os
import socket
import ssl
from dataclasses import dataclass
from typing import List, Tuple
from urllib.parse import urlparse

import httpx
from loguru import logger


ALLOW_PRIVATE_GATEWAY_URLS = os.getenv("MODEL_GATEWAY_ALLOW_PRIVATE_URLS", "").lower() in {"1", "true", "yes"}


@dataclass(frozen=True)
class _ValidatedGatewayUrl:
    base_url: str
    scheme: str
    hostname: str
    port: int
    address: str
    path: str


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, address: str, server_hostname: str, *args, **kwargs):
        super().__init__(address, *args, **kwargs)
        self._server_hostname = server_hostname

    def connect(self) -> None:
        sock = socket.create_connection((self.host, self.port), self.timeout, self.source_address)
        context = self._context or ssl.create_default_context()
        self.sock = context.wrap_socket(sock, server_hostname=self._server_hostname)


def _validate_gateway_base_url(base_url: str) -> _ValidatedGatewayUrl:
    value = (base_url or "").strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Invalid model gateway URL")
    if parsed.username or parsed.password:
        raise ValueError("Model gateway URL must not include credentials")
    if parsed.params or parsed.query or parsed.fragment:
        raise ValueError("Model gateway URL must not include params, query, or fragment")
    if parsed.scheme != "https" and not ALLOW_PRIVATE_GATEWAY_URLS:
        raise ValueError("Model gateway URL must use HTTPS")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("Model gateway host cannot be resolved") from exc
    addresses = sorted({info[4][0] for info in infos})
    if not addresses:
        raise ValueError("Model gateway host cannot be resolved")
    usable_addresses: list[str] = []
    for address in addresses:
        try:
            ip = ipaddress.ip_address(address)
        except ValueError as exc:
            raise ValueError("Model gateway host resolved to an invalid address") from exc
        if ALLOW_PRIVATE_GATEWAY_URLS or ip.is_global:
            usable_addresses.append(address)
    if not usable_addresses:
        raise ValueError("Model gateway host resolves to a non-public address")
    return _ValidatedGatewayUrl(
        base_url=value,
        scheme=parsed.scheme,
        hostname=parsed.hostname,
        port=port,
        address=usable_addresses[0],
        path=parsed.path.rstrip("/"),
    )


def _host_header(hostname: str, port: int, scheme: str) -> str:
    host = f"[{hostname}]" if ":" in hostname and not hostname.startswith("[") else hostname
    default_port = 443 if scheme == "https" else 80
    return host if port == default_port else f"{host}:{port}"


def _gateway_request_url(gateway: _ValidatedGatewayUrl, path: str) -> str:
    return f"{gateway.scheme}://{_host_header(gateway.hostname, gateway.port, gateway.scheme)}{path}"


def _request_gateway_json(gateway: _ValidatedGatewayUrl, path: str, headers: dict[str, str], timeout: float) -> dict:
    request_url = _gateway_request_url(gateway, path)
    request = httpx.Request("GET", request_url)
    try:
        if gateway.scheme == "https":
            conn = _PinnedHTTPSConnection(gateway.address, gateway.hostname, gateway.port, timeout=timeout)
        else:
            conn = http.client.HTTPConnection(gateway.address, gateway.port, timeout=timeout)
        try:
            conn.request("GET", path, headers={**headers, "Host": _host_header(gateway.hostname, gateway.port, gateway.scheme)})
            response = conn.getresponse()
            body = response.read()
        finally:
            conn.close()
    except socket.timeout as exc:
        raise httpx.TimeoutException("Connection timeout", request=request) from exc
    except (OSError, http.client.HTTPException) as exc:
        raise httpx.ConnectError("Connection failed", request=request) from exc
    httpx_response = httpx.Response(response.status, content=body, request=request)
    httpx_response.raise_for_status()
    return json.loads(body.decode("utf-8"))


def fetch_available_models(api_key: str, base_url: str, timeout: float = 10.0) -> List[str]:
    """
    Fetch available models from an OpenAI-compatible API endpoint.
    
    Uses the standard GET /v1/models endpoint with Bearer token authentication.
    
    Args:
        api_key: The API key for authentication
        base_url: The base URL of the API (e.g., https://api.openai.com/v1)
        timeout: Request timeout in seconds
    
    Returns:
        List of model IDs available from the API
    
    Raises:
        httpx.HTTPStatusError: If the API returns an error status code
        httpx.RequestError: If there's a network error
    """
    # Normalize base_url - ensure it ends with /v1 or similar
    gateway = _validate_gateway_base_url(base_url)
    
    # Build the models endpoint URL
    # Handle cases where base_url might or might not include /v1
    if gateway.path.endswith("/v1"):
        models_path = f"{gateway.path}/models"
    else:
        models_path = f"{gateway.path}/v1/models"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    logger.debug(f"Fetching models from: {_gateway_request_url(gateway, models_path)}")
    
    data = _request_gateway_json(gateway, models_path, headers, timeout)
    models = [model["id"] for model in data.get("data", [])]
        
    # Sort models alphabetically for better UX
    models.sort()
        
    logger.debug(f"Fetched {len(models)} models")
    return models


def test_llm_connection(api_key: str, base_url: str, timeout: float = 10.0) -> Tuple[bool, str, int]:
    """
    Test the LLM API connection by attempting to fetch the models list.
    
    Args:
        api_key: The API key for authentication
        base_url: The base URL of the API
        timeout: Request timeout in seconds
    
    Returns:
        Tuple of (success: bool, message: str, model_count: int)
        - success: True if connection succeeded
        - message: Human-readable status message
        - model_count: Number of models available (0 if failed)
    """
    try:
        models = fetch_available_models(api_key, base_url, timeout)
        return True, f"Connection successful! {len(models)} models available.", len(models)
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        if status_code == 401:
            return False, "Authentication failed: Invalid API Key", 0
        elif status_code == 403:
            return False, "Access forbidden: Check your API Key permissions", 0
        elif status_code == 404:
            return False, "API endpoint not found: Check your Base URL", 0
        else:
            return False, f"API error: HTTP {status_code}", 0
    except httpx.ConnectError:
        return False, "Connection failed: Cannot reach the server", 0
    except httpx.TimeoutException:
        return False, "Connection timeout: Server did not respond in time", 0
    except Exception as e:
        logger.error(f"LLM connection test error: {e}")
        return False, f"Error: {str(e)}", 0
