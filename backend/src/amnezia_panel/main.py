from __future__ import annotations

import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles

from amnezia_panel.models import (
    Capabilities,
    CreatePeerRequest,
    DeletePeerRequest,
    HealthResponse,
    ProtocolId,
    ServerInventory,
)
from amnezia_panel.mutation_core import MutationError
from amnezia_panel.mutations import MutationService
from amnezia_panel.service import InventoryService
from amnezia_panel.transport import SshDockerTransport

ORIGINS = {
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
}


def create_app(
    service: InventoryService | None = None,
    mutations: MutationService | None = None,
    *,
    enable_mutations: bool | None = None,
) -> FastAPI:
    enabled = (
        os.getenv("AMNEZIA_ENABLE_MUTATIONS") == "true"
        if enable_mutations is None
        else enable_mutations
    )
    token = secrets.token_urlsafe(32)
    local = os.getenv("AMNEZIA_LOCAL_TRANSPORT") == "true"

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.inventory_service = service or InventoryService(
            SshDockerTransport(
                target=os.getenv("AMNEZIA_SSH_TARGET", "amnezia-server"), local=local
            )
        )
        app.state.mutations = mutations or MutationService(
            target=os.getenv("AMNEZIA_SSH_TARGET", "amnezia-server"), local=local
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
        allow_origins=list(ORIGINS),
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Accept", "Content-Type", "X-Amnezia-Token"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if request.method in {"POST", "DELETE"}:
            if not enabled:
                return JSONResponse({"error": "read_only"}, status_code=403)
            if (
                request.headers.get("origin") not in ORIGINS
                or not secrets.compare_digest(request.headers.get("x-amnezia-token", ""), token)
                or request.headers.get("content-type", "").split(";")[0] != "application/json"
            ):
                return JSONResponse({"error": "forbidden"}, status_code=403)
            if len(await request.body()) > 8192:
                return JSONResponse({"error": "request_too_large"}, status_code=413)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(MutationError)
    async def mutation_error(request: Request, error: MutationError):
        conflict = {
            "revision_conflict",
            "runtime_drift",
            "busy",
            "confirmation_mismatch",
            "idempotency_conflict",
            "peer_not_found",
        }
        status = 409 if error.code in conflict else 503
        if error.code.startswith("invalid_") or error.code == "subnet_full":
            status = 422
        return JSONResponse(
            {"error": error.code}, status_code=status, headers={"Cache-Control": "no-store"}
        )

    @app.get("/api/v1/session")
    async def session():
        return {"token": token if enabled else None}

    @app.get("/api/v1/journal")
    async def journal(request: Request):
        return await request.app.state.mutations.call({"action": "journal"})

    @app.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(mode="management" if enabled else "read-only")

    @app.get("/api/v1/server", response_model=ServerInventory)
    async def server_inventory(request: Request) -> ServerInventory:
        inventory_service: InventoryService = request.app.state.inventory_service
        inventory = await inventory_service.inventory()
        return inventory.model_copy(update={"capabilities": Capabilities(can_mutate=enabled)})

    @app.get("/api/v1/protocols/{protocol}/preflight")
    async def preflight(protocol: ProtocolId, request: Request):
        if not enabled:
            raise HTTPException(403, "read_only")
        return await request.app.state.mutations.call({"action": "preflight", "protocol": protocol})

    @app.get("/api/v1/protocols/{protocol}/operations/{operation_id}")
    async def operation_status(protocol: ProtocolId, operation_id: str, request: Request):
        if not enabled:
            raise HTTPException(403, "read_only")
        return await request.app.state.mutations.call(
            {"action": "status", "protocol": protocol, "operation_id": operation_id}
        )

    async def mutate(request: Request, payload: dict):
        try:
            return await request.app.state.mutations.call(payload)
        finally:
            request.app.state.inventory_service.invalidate()

    @app.post("/api/v1/protocols/{protocol}/recovery")
    async def recover(protocol: ProtocolId, request: Request):
        return await mutate(request, {"action": "recover", "protocol": protocol})

    @app.post("/api/v1/protocols/{protocol}/peers")
    async def create_peer(protocol: ProtocolId, body: CreatePeerRequest, request: Request):
        return await mutate(
            request, {**body.model_dump(), "action": "create", "protocol": protocol}
        )

    @app.delete("/api/v1/protocols/{protocol}/peers/{peer_id}")
    async def delete_peer(
        protocol: ProtocolId,
        peer_id: str,
        body: DeletePeerRequest,
        request: Request,
    ):
        return await mutate(
            request,
            {**body.model_dump(), "action": "delete", "protocol": protocol, "peer_id": peer_id},
        )

    static_dir = os.getenv("AMNEZIA_STATIC_DIR")
    if static_dir:
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")

    return app


app = create_app()
