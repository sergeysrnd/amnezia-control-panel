"""Run on the VPN host after installing helper files. Explicit administrator setup."""

import argparse
import ipaddress
import json
import os
import sys

sys.path.insert(0, "/opt/amnezia-control")
from mutation_core import validate_endpoint  # noqa: E402
from remote_helper import (  # noqa: E402
    ROOT,
    SPECS,
    DockerStore,
    TransactionEngine,
    atomic_file,
    run,
)

parser = argparse.ArgumentParser()
parser.add_argument("--endpoint", required=True)
parser.add_argument("--dns", default="1.1.1.1")
parser.add_argument("--protocol", choices=list(SPECS), action="append", required=True)
args = parser.parse_args()
os.umask(0o077)
validate_endpoint(args.endpoint)
ipaddress.ip_address(args.dns)
ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
path = ROOT / "policy.json"
policies = json.loads(path.read_text()) if path.exists() else {}
for protocol in args.protocol:
    info = json.loads(run(["docker", "inspect", SPECS[protocol][0]]))[0]
    policy = {
        "container_id": info["Id"],
        "image_id": info["Image"],
        "endpoint": args.endpoint,
        "dns": args.dns,
    }
    store = DockerStore(protocol, policy)
    # No config writes: verify shape, peer consistency and actual server key.
    snapshot = TransactionEngine(store, ROOT / protocol).snapshot()
    policies[protocol] = policy
    print(
        json.dumps(
            {"protocol": protocol, "checked": True, "free_address": snapshot["next_ip"] is not None}
        )
    )
atomic_file(path, json.dumps(policies, indent=2))
