"""FastAPI dependencies: shared application state access.

The application state (configuration, repository, services) is created once
by the application factory and attached to ``app.state``; this module
provides the ``Depends`` callable that exposes it to the routers.
"""

from __future__ import annotations

from fastapi import Request

from AcheoConverter.application import AppState


def get_state(request: Request) -> AppState:
    """Return the shared :class:`AppState` of the running application."""
    return request.app.state.app_state
