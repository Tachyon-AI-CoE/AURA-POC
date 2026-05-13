"""FastAPI app factory.

Boot with::

    uvicorn app.main:app --reload --port 8000
"""
# This is the entry point that builds the FastAPI app and connects all pieces.

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.exceptions import (
    AuraError,
    aura_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from app.logging import configure_logging
from app.middleware import RequestIDMiddleware
from app.routers import health, scaffold_routes, templates
from app.settings import get_settings


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging(level=get_settings().log_level)
    yield


def create_app() -> FastAPI:    #function that builds the app
    settings = get_settings()   # Read environment config (repo name, API key, etc.)
    app = FastAPI(
        title="AURA-POC — AI Component Scaffolding Service",
        description=(
            "Scaffolds new AI components (today: agents and multiagent) "
            "into a shared GitHub repository. See spec.md and openapi.yaml "
            "for the contract."
        ),
        version="0.1.0",
        lifespan=_lifespan,
    )

    # Middleware (outermost to innermost)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowlist,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
    )
    app.add_middleware(RequestIDMiddleware)

    # Exception handlers — emit application/problem+json
    app.add_exception_handler(AuraError, aura_error_handler)  # Handle our custom errors
    app.add_exception_handler(RequestValidationError, validation_error_handler)    # Handle bad input
    app.add_exception_handler(Exception, unhandled_error_handler) # Handle all other errors

# Include routers (the actual endpoints)
    app.include_router(health.router)
    app.include_router(templates.router)
    app.include_router(scaffold_routes.router)
    return app  # Return the complete app


app = create_app() # Create app when file loads (uvicorn uses this)
