from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from amnezia_panel.models import HealthResponse, ServerInventory
from amnezia_panel.service import InventoryService
from amnezia_panel.transport import SshDockerTransport


def create_app(service: InventoryService | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.inventory_service = service or InventoryService(
            SshDockerTransport(target=os.getenv("AMNEZIA_SSH_TARGET", "amnezia-server"))
        )
        yield

    app = FastAPI(
        title="Amnezia Control API",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept", "Content-Type"],
    )

    @app.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/api/v1/server", response_model=ServerInventory)
    async def server_inventory(request: Request) -> ServerInventory:
        inventory_service: InventoryService = request.app.state.inventory_service
        return await inventory_service.inventory()

    return app


app = create_app()
