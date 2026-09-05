"""Root-owned SSH helper. JSON stdin only; no user-supplied commands or paths.

Install alongside mutation_core.py. Backups stay on the VPN host, outside containers.
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

try:
    from .mutation_core import (
        AWG_FIELDS,
        MutationError,
        add_peer,
        export_client,
        free_ip,
        interface_state,
        metadata,
        peer_id,
        peer_state,
        preserve_runtime_interface,
        remove_peer,
        require,
        revision,
        sections,
        valid_key,
        validate_endpoint,
    )
except ImportError:
    from mutation_core import (  # type: ignore[no-redef]
        AWG_FIELDS,
        MutationError,
        add_peer,
        export_client,
        free_ip,
        interface_state,
        metadata,
        peer_id,
        peer_state,
        preserve_runtime_interface,
        remove_peer,
        require,
        revision,
        sections,
        valid_key,
        validate_endpoint,
    )

SPECS = {
    "awg-legacy": ("amnezia-awg", "/opt/amnezia/awg", "wg0", "wg", "wg-quick"),
    "awg": ("amnezia-awg2", "/opt/amnezia/awg", "awg0", "awg", "awg-quick"),
    "wireguard": ("amnezia-wireguard", "/opt/amnezia/wireguard", "wg0", "wg", "wg-quick"),
}
ROOT = Path("/var/lib/amnezia-control")
TERMINAL = {"committed", "rolled_back", "aborted"}


def run(args: list[str], data: str | None = None) -> str:
    try:
        result = subprocess.run(args, input=data, capture_output=True, text=True, timeout=25)
        require(result.returncode == 0, "remote_command_failed")
        return result.stdout
    except (OSError, subprocess.TimeoutExpired) as error:
        raise MutationError("remote_command_failed") from error


def atomic_file(path: Path, value: str) -> None:
    """Durable private files, including journal state transitions."""
    temporary = path.with_name(path.name + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


class DockerStore:
    def __init__(self, protocol: str, policy: dict):
        require(protocol in SPECS, "invalid_protocol")
        self.protocol = protocol
        self.container, self.directory, self.interface, self.binary, self.quick = SPECS[protocol]
        self.policy = policy
        self.identity()

    def identity(self) -> str:
        info = json.loads(run(["docker", "inspect", self.container]))[0]
        require(info["State"]["Running"] is True, "container_unavailable")
        require(
            info["Id"] == self.policy["container_id"] and info["Image"] == self.policy["image_id"],
            "container_changed",
        )
        return info["Id"]

    def command(self, *args: str, data: str | None = None) -> str:
        return run(["docker", "exec", "-i", self.policy["container_id"], *args], data)

    def paths(self) -> tuple[str, str]:
        return f"{self.directory}/{self.interface}.conf", f"{self.directory}/clientsTable"

    def read(self) -> tuple[str, str]:
        config, table = self.paths()
        for path in (config, table):
            self.command("sh", "-c", 'test -f "$1" && test ! -L "$1"', "check", path)
        return self.command("cat", config), self.command("cat", table)

    def runtime(self) -> str:
        return self.command(self.binary, "showconf", self.interface)

    def server_key(self, config: str) -> str:
        private = sections(config)[0].values["PrivateKey"]
        derived = self.command(self.binary, "pubkey", data=private + "\n").strip()
        actual = self.command(self.binary, "show", self.interface, "public-key").strip()
        require(valid_key(derived) and derived == actual, "runtime_drift")
        port = self.command(self.binary, "show", self.interface, "listen-port").strip()
        require(port == sections(config)[0].values["ListenPort"], "runtime_drift")
        source = sections(config)[0].values
        runtime = interface_state(self.runtime())
        require(
            all(source[key] == runtime.get(key, "0") for key in AWG_FIELDS & source.keys()),
            "runtime_drift",
        )
        return derived

    def keypair(self) -> tuple[str, str, str]:
        private = self.command(self.binary, "genkey").strip()
        public = self.command(self.binary, "pubkey", data=private + "\n").strip()
        psk = self.command(self.binary, "genpsk").strip()
        require(all(valid_key(k) for k in (private, public, psk)), "invalid_key")
        return private, public, psk

    @contextlib.contextmanager
    def stage(self, value: str):
        directory = f"{self.directory}/.panel-{uuid.uuid4().hex}"
        path = f"{directory}/{self.interface}.conf"
        self.command("mkdir", "-m", "700", directory)
        try:
            self.command("sh", "-c", 'umask 077; cat > "$1"', "stage", path, data=value)
            self.command("sync")
            yield path
        finally:
            self.command("rm", "-f", path)
            self.command("rmdir", directory)

    def strip(self, config: str) -> str:
        with self.stage(config) as path:
            return self.command(self.quick, "strip", path)

    def replace(self, which: int, value: str) -> None:
        require(which in (0, 1))
        target = self.paths()[which]
        with self.stage(value) as path:
            self.command("mv", "-f", path, target)
            self.command("sync")

    def sync(self, runtime_config: str) -> None:
        self.command(self.binary, "syncconf", self.interface, "/dev/stdin", data=runtime_config)


class TransactionEngine:
    def __init__(self, store: DockerStore, root: Path):
        self.store = store
        self.root = root
        root.mkdir(mode=0o700, parents=True, exist_ok=True)

    def state(self, folder: Path, phase: str, **fields) -> None:
        previous = (
            json.loads((folder / "state.json").read_text())
            if (folder / "state.json").exists()
            else {}
        )
        atomic_file(folder / "state.json", json.dumps({**previous, **fields, "phase": phase}))

    def restore(self, folder: Path) -> None:
        """Never overwrite third-party changes during recovery."""
        recorded = json.loads((folder / "state.json").read_text())
        require(self.store.identity() == recorded["container_id"], "container_changed")
        before = tuple((folder / name).read_text() for name in ("config.before", "table.before"))
        after = tuple((folder / name).read_text() for name in ("config.after", "table.after"))
        current = self.store.read()
        require(
            all(c in (old, new) for c, old, new in zip(current, before, after, strict=True)),
            "recovery_conflict",
        )
        runtime_before = (folder / "runtime.before").read_text()
        runtime_after = (folder / "runtime.after").read_text()
        runtime_state = peer_state(self.store.runtime())
        require(
            interface_state(self.store.runtime()) == interface_state(runtime_before),
            "recovery_conflict",
        )
        require(
            runtime_state in (peer_state(runtime_before), peer_state(runtime_after)),
            "recovery_conflict",
        )
        self.state(folder, "rolling_back")
        for index, value in enumerate(before):
            require(self.store.read()[index] in (before[index], after[index]), "recovery_conflict")
            self.store.replace(index, value)
        self.store.sync(runtime_before)
        require(self.store.read() == before, "rollback_failed")
        require(peer_state(self.store.runtime()) == peer_state(runtime_before), "rollback_failed")
        require(
            interface_state(self.store.runtime()) == interface_state(runtime_before),
            "rollback_failed",
        )
        self.state(folder, "rolled_back")

    def recover(self) -> None:
        for folder in sorted(self.root.iterdir()):
            if not folder.is_dir() or not re.fullmatch(r"[0-9a-f-]{36}", folder.name):
                continue
            state_path = folder / "state.json"
            if not state_path.exists():
                continue  # Crash while backing up: no writes are allowed before prepared.
            state = json.loads(state_path.read_text())
            if state["phase"] not in TERMINAL:
                try:
                    self.restore(folder)
                except Exception as error:
                    self.state(folder, "recovery_required")
                    raise MutationError("recovery_required") from error

    def snapshot(self) -> dict:
        for state_path in self.root.glob("*/state.json"):
            require(json.loads(state_path.read_text())["phase"] in TERMINAL, "recovery_required")
        self.store.identity()
        config, table = self.store.read()
        sections(config)
        metadata(table)
        require(peer_state(config) == peer_state(self.store.runtime()), "runtime_drift")
        self.store.server_key(config)
        try:
            next_ip = free_ip(config)
        except MutationError as error:
            if error.code != "subnet_full":
                raise
            next_ip = None
        return {"revision": revision(config, table), "next_ip": next_ip}

    def execute(self, request: dict) -> dict:
        operation_id = request["operation_id"]
        require(str(uuid.UUID(operation_id)) == operation_id, "invalid_operation_id")
        folder = self.root / operation_id
        if folder.exists():
            state_path = folder / "state.json"
            require(state_path.exists(), "operation_incomplete")
            state = json.loads(state_path.read_text())
            require(
                state.get("request_hash")
                == hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest(),
                "idempotency_conflict",
            )
            return {
                "operation_id": operation_id,
                "status": state["phase"],
                "peer_id": state.get("peer_id"),
                "replayed": True,
            }
        self.store.identity()
        before = self.store.read()
        require(revision(*before) == request["revision"], "revision_conflict")
        sections(before[0])
        metadata(before[1])
        runtime_before = self.store.runtime()
        require(peer_state(before[0]) == peer_state(runtime_before), "runtime_drift")
        server_key = self.store.server_key(before[0])
        result: dict = {"operation_id": operation_id, "status": "committed", "replayed": False}
        if request["action"] == "create":
            private, public, psk = self.store.keypair()
            config, table, address = add_peer(
                *before,
                public,
                psk,
                request["name"],
                datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
            )
            profile = export_client(
                config,
                private,
                server_key,
                psk,
                address,
                self.store.policy["endpoint"],
                self.store.policy["dns"],
                request["keepalive"],
            )
            result.update(
                peer_id=peer_id(public),
                ip_address=address,
                filename=f"amnezia-{self.store.protocol}-{peer_id(public)}.conf",
                native_config=profile,
            )
        else:
            require(request["action"] == "delete", "invalid_action")
            config, table = remove_peer(*before, request["peer_id"], request["name"])
            result["peer_id"] = request["peer_id"]
        after = (config, table)
        runtime_after = preserve_runtime_interface(self.store.strip(config), runtime_before)
        require(peer_state(runtime_after) == peer_state(config), "invalid_candidate")
        # Backups are durable before any persistent or runtime mutation.
        folder.mkdir(mode=0o700)
        directory_fd = os.open(self.root, os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        for name, value in zip(
            (
                "config.before",
                "table.before",
                "config.after",
                "table.after",
                "runtime.before",
                "runtime.after",
            ),
            (*before, *after, runtime_before, runtime_after),
            strict=True,
        ):
            atomic_file(folder / name, value)
        self.state(
            folder,
            "prepared",
            container_id=self.store.identity(),
            action=request["action"],
            peer_id=result["peer_id"],
            created_at=datetime.now(UTC).isoformat(),
            request_hash=hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest(),
        )
        changed = False
        try:
            self.store.identity()
            require(self.store.read() == before, "revision_conflict")
            require(peer_state(self.store.runtime()) == peer_state(runtime_before), "runtime_drift")
            require(
                interface_state(self.store.runtime()) == interface_state(runtime_before),
                "runtime_drift",
            )
            self.state(folder, "writing")
            changed = True  # A failed remote rename may still have succeeded.
            self.store.replace(0, after[0])
            require(self.store.read() == (after[0], before[1]), "revision_conflict")
            self.store.replace(1, after[1])
            require(self.store.read() == after, "revision_conflict")
            self.store.identity()
            self.state(folder, "applying")
            self.store.sync(runtime_after)
            require(peer_state(self.store.runtime()) == peer_state(runtime_after), "verify_failed")
            require(
                interface_state(self.store.runtime()) == interface_state(runtime_before),
                "verify_failed",
            )
            require(self.store.read() == after, "revision_conflict")
            self.store.server_key(config)
            self.state(folder, "committed")
        except Exception as error:
            if not changed:
                self.state(folder, "aborted")
                raise
            try:
                self.restore(folder)
            except Exception:
                self.state(folder, "recovery_required")
                raise MutationError("recovery_required") from error
            raise MutationError("rolled_back") from error
        return result


def read_journal(root: Path) -> dict:
    require(root.is_dir(), "journal_unavailable")
    events = []
    skipped = 0
    phases = TERMINAL | {"prepared", "writing", "applying", "rolling_back", "recovery_required"}
    for protocol in SPECS:
        for path in (root / protocol).glob("*/state.json"):
            try:
                require(not path.is_symlink() and not path.parent.is_symlink())
                require(str(uuid.UUID(path.parent.name)) == path.parent.name)
                require(path.stat().st_size < 65536)
                state = json.loads(path.read_text())
                require(state["action"] in {"create", "delete"} and state["phase"] in phases)
                created = datetime.fromisoformat(state["created_at"]).astimezone(UTC).isoformat()
                identifier = state.get("peer_id")
                require(
                    isinstance(identifier, str) and bool(re.fullmatch(r"[0-9a-f]{20}", identifier))
                )
                events.append(
                    {
                        "id": path.parent.name,
                        "protocol": protocol,
                        "action": state["action"],
                        "status": state["phase"],
                        "peer_id": identifier,
                        "created_at": created,
                    }
                )
            except (OSError, ValueError, KeyError, TypeError, MutationError):
                skipped += 1
    events.sort(key=lambda item: (item["created_at"], item["id"]), reverse=True)
    return {"events": events[:100], "total": len(events), "skipped": skipped}


def dispatch(request: dict, root: Path = ROOT) -> dict:
    require(isinstance(request, dict), "invalid_request")
    if request == {"action": "journal"}:
        return read_journal(root)
    protocol = request.get("protocol")
    require(protocol in SPECS, "invalid_protocol")
    policy_path = root / "policy.json"
    require(policy_path.is_file(), "not_enrolled")
    policies = json.loads(policy_path.read_text())
    require(protocol in policies, "not_enrolled")
    policy = policies[protocol]
    validate_endpoint(policy["endpoint"])
    with (root / f"{protocol}.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise MutationError("busy") from error
        engine = TransactionEngine(DockerStore(protocol, policy), root / protocol)
        action = request.get("action")
        if action == "recover":
            engine.recover()
            return {"status": "recovered"}
        if action == "preflight":
            return {**engine.snapshot(), "endpoint": policy["endpoint"], "dns": policy["dns"]}
        if action == "status":
            operation_id = request.get("operation_id", "")
            require(str(uuid.UUID(operation_id)) == operation_id, "invalid_operation_id")
            path = engine.root / operation_id / "state.json"
            require(path.exists(), "operation_not_found")
            state = json.loads(path.read_text())
            return {
                "operation_id": operation_id,
                "status": state["phase"],
                "peer_id": state.get("peer_id"),
            }
        require(action in ("create", "delete"), "invalid_action")
        allowed = {"action", "protocol", "operation_id", "revision", "name"}
        allowed |= {"keepalive"} if action == "create" else {"peer_id"}
        require(set(request) == allowed, "invalid_request")
        require(
            isinstance(request["revision"], str)
            and bool(re.fullmatch(r"[0-9a-f]{64}", request["revision"])),
            "invalid_request",
        )
        if action == "create":
            require(isinstance(request["keepalive"], bool), "invalid_request")
        engine.recover()
        return engine.execute(request)


def main() -> None:
    os.umask(0o077)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    try:
        raw = sys.stdin.read(8193)
        require(len(raw) <= 8192, "request_too_large")
        response = dispatch(json.loads(raw))
    except MutationError as error:
        response = {"error": error.code}
    except Exception:
        response = {"error": "helper_failed"}  # Never include command output or config.
    print(json.dumps(response, ensure_ascii=False))


if __name__ == "__main__":
    main()
