"""Minimal in-process ASGI test client (no third-party dependencies).

The project's runtime dependencies intentionally exclude ``httpx`` (which
Starlette's ``TestClient`` requires), so this module implements a tiny
ASGI caller on top of the plain ASGI protocol:

* builds an ``http`` scope for each request;
* feeds the request body through the ASGI ``receive`` callable;
* collects the response through the ASGI ``send`` callable;
* provides ``get`` / ``post_json`` / ``post_multipart`` helpers mirroring
  the usual test-client API.

The multipart encoder below builds a standards-compliant
``multipart/form-data`` body (fields + files), which is what the
``POST /api/v1/models`` upload endpoint expects.
"""

from __future__ import annotations

import asyncio
import json as _json
import uuid
from typing import Any
from urllib.parse import urlencode


class ASGIResponse:
    """One collected HTTP response."""

    def __init__(self, status: int, headers: list[tuple[bytes, bytes]], body: bytes) -> None:
        self.status = status
        self._headers = headers
        self.body = body

    @property
    def text(self) -> str:
        """The response body decoded as UTF-8."""
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        """Parse the response body as JSON."""
        return _json.loads(self.body.decode("utf-8"))

    def headers(self) -> dict[str, str]:
        """Lower-cased header name -> value (first value wins)."""
        result: dict[str, str] = {}
        for key, value in self._headers:
            name = key.decode("latin-1").lower()
            if name not in result:
                result[name] = value.decode("latin-1")
        return result

    def header(self, name: str) -> str | None:
        """Return one header value (case-insensitive) or None."""
        return self.headers().get(name.lower())


def build_multipart(fields: dict[str, str | None], files: dict[str, tuple[str, bytes, str]]) -> tuple[bytes, str]:
    """Build a ``multipart/form-data`` body.

    Args:
        fields: form fields (None values are skipped).
        files: file parts as ``{name: (filename, content, content_type)}``.

    Returns:
        ``(body_bytes, content_type_header)``.
    """
    boundary = f"----archeoboundary{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        if value is None:
            continue
        chunks.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n'
            f"\r\n"
            f"{value}\r\n".encode("utf-8")
        )
    for name, (filename, content, content_type) in files.items():
        chunks.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n"
            f"\r\n".encode("utf-8")
            + content
            + b"\r\n"
        )
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


class ASGIClient:
    """Synchronous test client driving an ASGI app directly."""

    def __init__(self, app: Any) -> None:
        self.app = app

    # ------------------------------------------------------------------ #
    # Core
    # ------------------------------------------------------------------ #
    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        query: str | None = None,
    ) -> ASGIResponse:
        """Perform one request against the ASGI app and return the response."""
        full_path = path
        if query:
            full_path = f"{path}?{query}"
        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method.upper(),
            "scheme": "http",
            "path": full_path,
            "raw_path": full_path.encode("utf-8"),
            "query_string": (full_path.split("?", 1)[1] if "?" in full_path else "").encode("utf-8"),
            "headers": [
                (key.lower().encode("latin-1"), value.encode("latin-1"))
                for key, value in (headers or {}).items()
            ],
            "client": ("testclient", 0),
            "server": ("testserver", 80),
            "root_path": "",
        }

        state = {"started": False, "status": 0, "headers": [], "body": b"", "done": False}

        async def receive() -> dict[str, Any]:
            if not state["body_sent"]:
                state["body_sent"] = True
                return {"type": "http.request", "body": body or b"", "more_body": False}
            # The application must not call receive() again after the body
            # has been fully sent; fail fast instead of hanging.
            raise RuntimeError("ASGI receive() called after the request body was sent.")

        async def send(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                state["started"] = True
                state["status"] = message["status"]
                state["headers"] = list(message.get("headers", []))
            elif message["type"] == "http.response.body":
                state["body"] += message.get("body", b"")
                if not message.get("more_body", False):
                    state["done"] = True

        state["body_sent"] = False

        async def run() -> None:
            await self.app(scope, receive, send)

        asyncio.run(run())
        if not state["started"]:
            raise AssertionError("The ASGI application did not start a response.")
        return ASGIResponse(state["status"], state["headers"], state["body"])

    # ------------------------------------------------------------------ #
    # Convenience verbs
    # ------------------------------------------------------------------ #
    def get(self, path: str, *, headers: dict[str, str] | None = None,
            query: str | None = None) -> ASGIResponse:
        """Perform a GET request."""
        return self.request("GET", path, headers=headers, query=query)

    def post_json(self, path: str, payload: Any,
                  *, headers: dict[str, str] | None = None) -> ASGIResponse:
        """Perform a POST request with a JSON body."""
        merged = {"Content-Type": "application/json", **(headers or {})}
        return self.request("POST", path, headers=merged,
                            body=_json.dumps(payload).encode("utf-8"))

    def post_multipart(self, path: str, fields: dict[str, str | None] | None = None,
                       files: dict[str, tuple[str, bytes, str]] | None = None) -> ASGIResponse:
        """Perform a POST request with a multipart/form-data body."""
        body, content_type = build_multipart(fields or {}, files or {})
        return self.request("POST", path,
                            headers={"Content-Type": content_type}, body=body)

    def delete(self, path: str, *, headers: dict[str, str] | None = None) -> ASGIResponse:
        """Perform a DELETE request."""
        return self.request("DELETE", path, headers=headers)
