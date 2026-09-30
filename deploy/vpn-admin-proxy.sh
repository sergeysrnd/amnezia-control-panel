#!/bin/bash
set -euo pipefail
# Only a cryptographically identified AWG peer may reach this listener.
container=amnezia-awg2
proxy_pid=
cleanup() { if [ -n "$proxy_pid" ]; then kill "$proxy_pid" 2>/dev/null || true; wait "$proxy_pid" 2>/dev/null || true; fi; }
trap 'cleanup; exit 0' TERM INT
trap cleanup EXIT
while true; do
    container_pid=$(docker inspect -f '{{.State.Pid}}' "$container" 2>/dev/null || echo 0)
    if [[ "$container_pid" =~ ^[1-9][0-9]*$ ]]; then
        nsenter -t "$container_pid" -n /usr/bin/socat \
            TCP4-LISTEN:8000,bind=10.8.1.0,reuseaddr,fork,range=10.8.1.5/32 \
            "EXEC:'/usr/bin/nsenter -t 1 -n /usr/bin/socat STDIO TCP4:127.0.0.1:8000'" &
        proxy_pid=$!
        while kill -0 "$proxy_pid" 2>/dev/null; do
            sleep 3
            current_pid=$(docker inspect -f '{{.State.Pid}}' "$container" 2>/dev/null || echo 0)
            if [ "$current_pid" != "$container_pid" ]; then break; fi
        done
        cleanup
        proxy_pid=
    fi
    sleep 3
done
