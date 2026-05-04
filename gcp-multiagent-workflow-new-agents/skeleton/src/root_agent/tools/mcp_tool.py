import logging
from typing import Optional, Dict, Any

import requests

logger = logging.getLogger(__name__)


class MCPTool:
    """Minimal MCP tool for calling MCP server endpoints.

    This is a lightweight HTTP client wrapper that uses the MCP server config
    produced by `agent_config_generator.py`.
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.server_url = config.get("server_url", "")
        self.api_key = config.get("api_key") or config.get("api_key_env")
        # base_path and health_path are optional
        self.base_path = config.get("base_path", "")
        self.health_path = config.get("health_path", "")
        # ensure server_url has no trailing slash
        if self.server_url.endswith("/"):
            self.server_url = self.server_url[:-1]

    def _build_url(self, path: str) -> str:
        if not path:
            path = ""
        # If path is an absolute URL, return as-is
        if path.startswith("http://") or path.startswith("https://"):
            return path

        # Use provided base_path if available
        base = self.base_path or ""
        # Normalize slashes
        if base and not base.startswith("/"):
            base = "/" + base
        if base.endswith("/"):
            base = base[:-1]

        if path and not path.startswith("/"):
            path = "/" + path

        return f"{self.server_url}{base}{path}"

    def headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            # If api_key is actually the name of an env var, calling code should
            # resolve it; here we accept either the key itself or None.
            h["Authorization"] = f"Bearer {self.api_key}"
        if extra:
            h.update(extra)
        return h

    def health(self, timeout: int = 5) -> Dict[str, Any]:
        url = None
        if self.health_path:
            url = self._build_url(self.health_path)
        else:
            # Fallback to base + /health
            url = self._build_url("/health")

        try:
            r = requests.get(url, headers=self.headers(), timeout=timeout)
            return {"status_code": r.status_code, "text": r.text}
        except Exception as e:
            logger.warning(f"MCPTool.health() failed for {self.name}: {e}")
            return {"status_code": None, "error": str(e)}

    def request(self, method: str, path: str = "", json: Optional[Any] = None, timeout: int = 10) -> Dict[str, Any]:
        url = self._build_url(path)
        try:
            r = requests.request(method.upper(), url, headers=self.headers(), json=json, timeout=timeout)
            return {"status_code": r.status_code, "json": (r.json() if r.content else None), "text": r.text}
        except Exception as e:
            logger.warning(f"MCPTool.request() failed for {self.name} {method} {path}: {e}")
            return {"status_code": None, "error": str(e)}
