"""Minimal async client for the SolarWinds Information Service (SWIS) REST API.

Talks to ``POST /Query`` with bound parameters, per
https://github.com/trooperthorn/SolarWinds_OrionGuides/blob/main/docs/swis/rest-api.md.
Only the query interface is used: this integration is read-only.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import DEFAULT_TIMEOUT

_LOGGER = logging.getLogger(__name__)

BASE_PATH = "SolarWinds/InformationService/v3/Json"


class SwisError(Exception):
    """Base error talking to SWIS."""


class SwisAuthError(SwisError):
    """Invalid username/password (HTTP 401)."""


class SwisConnectionError(SwisError):
    """Could not reach the SWIS endpoint at all."""


class SwisClient:
    """Thin async wrapper around the SWIS REST /Query endpoint."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        username: str,
        password: str,
        *,
        port: int = 17774,
        verify_ssl: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self._session = session
        self._base_url = f"https://{host}:{port}/{BASE_PATH}"
        self._auth = aiohttp.BasicAuth(username, password)
        self._verify_ssl = verify_ssl
        self._timeout = aiohttp.ClientTimeout(connect=10, total=timeout)

    async def query(self, swql: str, **parameters: Any) -> list[dict[str, Any]]:
        """Run a SWQL query and return the result rows.

        Values passed as keyword arguments are bound as ``@name`` parameters
        rather than concatenated into the query text.
        """
        body: dict[str, Any] = {"query": swql}
        if parameters:
            body["parameters"] = parameters

        url = f"{self._base_url}/Query"
        try:
            async with self._session.post(
                url,
                json=body,
                auth=self._auth,
                ssl=self._verify_ssl,
                timeout=self._timeout,
            ) as resp:
                if resp.status == 401:
                    raise SwisAuthError("Invalid username or password")
                if resp.status != 200:
                    detail = await self._error_detail(resp)
                    raise SwisError(f"HTTP {resp.status} from SWIS: {detail}")
                payload = await resp.json(content_type=None)
        except SwisError:
            raise
        except (aiohttp.ClientConnectorError, asyncio.TimeoutError) as err:
            raise SwisConnectionError(str(err)) from err
        except aiohttp.ClientError as err:
            raise SwisError(str(err)) from err

        return (payload or {}).get("results", [])

    @staticmethod
    async def _error_detail(resp: aiohttp.ClientResponse) -> str:
        try:
            data = await resp.json(content_type=None)
            if isinstance(data, dict) and "Message" in data:
                return str(data["Message"])
        except (aiohttp.ContentTypeError, ValueError):
            pass
        return await resp.text()
