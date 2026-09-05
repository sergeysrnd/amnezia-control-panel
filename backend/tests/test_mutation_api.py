from fastapi.testclient import TestClient

from amnezia_panel.main import create_app
from amnezia_panel.mutation_core import MutationError


class Inventory:
    invalidations = 0

    def invalidate(self):
        self.invalidations += 1


class Mutations:
    def __init__(self):
        self.calls = []
        self.error = None

    async def call(self, payload):
        self.calls.append(payload)
        if self.error:
            raise MutationError(self.error)
        return {"status": "committed", "native_config": "private-test-material"}


BODY = {
    "operation_id": "11111111-1111-4111-8111-111111111111",
    "revision": "a" * 64,
    "name": "Test",
    "keepalive": True,
}
URL = "/api/v1/protocols/wireguard/peers"


def test_writes_require_origin_and_session_token():
    mutations = Mutations()
    with TestClient(
        create_app(Inventory(), mutations, enable_mutations=True), base_url="http://localhost"
    ) as client:
        token = client.get("/api/v1/session").json()["token"]
        assert client.post(URL, json=BODY).status_code == 403
        headers = {"Origin": "https://evil.example", "X-Amnezia-Token": token}
        assert client.post(URL, json=BODY, headers=headers).status_code == 403
        headers["Origin"] = "http://localhost:5173"
        response = client.post(URL, json=BODY, headers=headers)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert len(mutations.calls) == 1


def test_read_only_gate_and_dns_rebinding():
    mutations = Mutations()
    with TestClient(
        create_app(Inventory(), mutations, enable_mutations=False), base_url="http://localhost"
    ) as client:
        assert client.post(URL, json=BODY).status_code == 403
        assert client.get("/api/v1/session", headers={"Host": "evil.example"}).status_code == 400
        assert mutations.calls == []


def test_conflict_and_invalid_input_never_leak_secrets():
    mutations = Mutations()
    inventory = Inventory()
    with TestClient(
        create_app(inventory, mutations, enable_mutations=True), base_url="http://localhost"
    ) as client:
        token = client.get("/api/v1/session").json()["token"]
        headers = {"Origin": "http://localhost:5173", "X-Amnezia-Token": token}
        assert client.post(URL, json={**BODY, "command": "rm"}, headers=headers).status_code == 422
        assert mutations.calls == []
        mutations.error = "revision_conflict"
        response = client.post(URL, json=BODY, headers=headers)
        assert response.status_code == 409
        assert response.json() == {"error": "revision_conflict"}
        assert inventory.invalidations == 1
