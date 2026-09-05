"""Opt-in server checks; never logs profiles, private keys or client names.

isolated: new synthetic interface inside an ephemeral network namespace.
lifecycle: create/revoke only a unique acceptance peer, using production transactions.
"""

import argparse
import json
import sys
import uuid

sys.path.insert(0, "/opt/amnezia-control")
import remote_helper  # noqa: E402
from mutation_core import AWG_FIELDS, MutationError, peer_state, revision, sections  # noqa: E402
from remote_helper import ROOT, DockerStore, TransactionEngine, dispatch  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("mode", choices=["isolated", "lifecycle", "rollback"])
parser.add_argument("protocol", choices=["wireguard", "awg-legacy", "awg"])
args = parser.parse_args()
policy = json.loads((ROOT / "policy.json").read_text())[args.protocol]
store = DockerStore(args.protocol, policy)


def isolated():
    original = store.read()
    server_private, _, _ = store.keypair()
    _, client_public, psk = store.keypair()
    params = sections(original[0])[0].values
    config = f"[Interface]\nPrivateKey = {server_private}\nListenPort = 51820\n"
    config += "".join(f"{k} = {v}\n" for k, v in params.items() if k in AWG_FIELDS)
    config += (
        f"[Peer]\nPublicKey = {client_public}\nPresharedKey = {psk}\nAllowedIPs = 10.254.254.2/32\n"
    )
    binary = store.binary
    if args.protocol == "wireguard":
        setup = "ip link add paneltest type wireguard; trap 'ip link delete paneltest' EXIT; "
    else:
        # Foreground worker lifetime is bounded by the enclosing shell trap.
        executable = "wireguard-go" if args.protocol == "awg-legacy" else "amneziawg-go"
        setup = (
            f"WG_PROCESS_FOREGROUND=1 {executable} paneltest >/dev/null 2>&1 & worker=$!; "
            "trap 'kill $worker 2>/dev/null || true; wait $worker 2>/dev/null || true' EXIT; "
            "sleep 1; "
        )
    script = (
        "set -eu; " + setup + f"{binary} syncconf paneltest /dev/stdin; "
        f'test "$({binary} show paneltest peers | wc -l)" -eq 1; '
        f'{binary} set paneltest peer "$({binary} show paneltest peers)" remove; '
        f'test -z "$({binary} show paneltest peers)"'
    )
    store.command("unshare", "-n", "sh", "-c", script, data=config)
    assert store.read() == original
    print(json.dumps({"protocol": args.protocol, "isolated_native_create_delete": "passed"}))


def lifecycle():
    before = store.read()
    runtime_before = peer_state(store.runtime())
    operation_id = str(uuid.uuid4())
    name = f"Panel acceptance {operation_id[:8]}"
    created = None
    try:
        created = dispatch(
            {
                "action": "create",
                "protocol": args.protocol,
                "operation_id": operation_id,
                "revision": revision(*before),
                "name": name,
                "keepalive": True,
            }
        )
        assert created["status"] == "committed" and created["native_config"]
        assert len(peer_state(store.runtime())) == len(runtime_before) + 1
    finally:
        if created:
            deleted = dispatch(
                {
                    "action": "delete",
                    "protocol": args.protocol,
                    "operation_id": str(uuid.uuid4()),
                    "revision": revision(*store.read()),
                    "name": name,
                    "peer_id": created["peer_id"],
                }
            )
            assert deleted["status"] == "committed"
        else:
            TransactionEngine(store, ROOT / args.protocol).recover()
    assert peer_state(store.runtime()) == runtime_before
    assert peer_state(store.read()[0]) == peer_state(before[0])
    assert json.loads(store.read()[1]) == json.loads(before[1])
    assert sections(store.read()[0])[0].values == sections(before[0])[0].values
    print(
        json.dumps(
            {
                "protocol": args.protocol,
                "transaction_create_delete": "passed",
                "existing_peers_preserved": len(runtime_before),
            }
        )
    )


def rollback():
    before = store.read()
    live_before = peer_state(store.runtime())
    original_sync = store.sync
    calls = 0

    def fail_after_apply(config):
        nonlocal calls
        calls += 1
        original_sync(config)
        if calls == 1:
            raise MutationError("injected_test_failure")

    store.sync = fail_after_apply
    original_factory = remote_helper.DockerStore
    remote_helper.DockerStore = lambda protocol, policy: store
    try:
        try:
            dispatch(
                {
                    "action": "create",
                    "protocol": args.protocol,
                    "operation_id": str(uuid.uuid4()),
                    "revision": revision(*before),
                    "name": "Panel rollback acceptance",
                    "keepalive": True,
                }
            )
        except MutationError as error:
            assert error.code == "rolled_back"
        else:
            raise AssertionError("Failure injection did not run")
    finally:
        remote_helper.DockerStore = original_factory
    assert calls == 2
    assert store.read() == before
    assert peer_state(store.runtime()) == live_before
    print(
        json.dumps(
            {
                "protocol": args.protocol,
                "real_runtime_rollback": "passed",
                "existing_peers_preserved": len(live_before),
            }
        )
    )


try:
    {"isolated": isolated, "lifecycle": lifecycle, "rollback": rollback}[args.mode]()
except Exception as error:
    print(
        json.dumps(
            {
                "protocol": args.protocol,
                "check": args.mode,
                "error": getattr(error, "code", type(error).__name__),
            }
        )
    )
    sys.exit(1)
