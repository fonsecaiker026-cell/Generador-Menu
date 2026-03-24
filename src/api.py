"""Compatibility shim for `uvicorn src.api:app`.

Use `api_server:app` as the canonical ASGI entrypoint.
"""

import api_server

app = api_server.app
