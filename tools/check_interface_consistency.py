"""Print only differing field names, never values."""

import json
import re
import sys

sys.path.insert(0, "/opt/amnezia-control")
from mutation_core import AWG_FIELDS, sections  # noqa: E402
from remote_helper import ROOT, DockerStore  # noqa: E402

for protocol, policy in json.loads((ROOT / "policy.json").read_text()).items():
    store = DockerStore(protocol, policy)
    source = sections(store.read()[0])[0].values
    runtime_header = re.split(r"(?m)^\s*\[Peer]\s*$", store.runtime())[0]
    runtime = dict(
        tuple(s.strip() for s in line.split("=", 1))
        for line in runtime_header.splitlines()
        if "=" in line
    )
    differences = [
        key for key in AWG_FIELDS & source.keys() if source[key] != runtime.get(key, "0")
    ]
    print(json.dumps({"protocol": protocol, "interface_field_differences": differences}))
