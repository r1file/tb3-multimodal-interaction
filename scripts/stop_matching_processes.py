#!/usr/bin/env python3
"""Stop only processes matching explicit role-owned command patterns."""

import argparse
import os
import signal
import subprocess
import time


def mount_namespace(pid):
    """Return the process mount namespace, or None if the process vanished."""
    try:
        return os.readlink(f"/proc/{pid}/ns/mnt")
    except (FileNotFoundError, PermissionError):
        return None


def matching_pids(patterns):
    protected = {os.getpid(), os.getppid()}
    own_mount_namespace = mount_namespace(os.getpid())
    output = subprocess.check_output(["ps", "-eo", "pid,args"], text=True)
    result = []
    for line in output.splitlines()[1:]:
        fields = line.strip().split(None, 1)
        if len(fields) != 2:
            continue
        try:
            pid = int(fields[0])
        except ValueError:
            continue
        if pid in protected:
            continue
        # The TB3 container intentionally uses the host PID namespace. Restrict
        # matches to processes in this container's mount namespace so a pattern
        # appearing in the host-side `docker exec` command cannot kill its caller.
        if own_mount_namespace and mount_namespace(pid) != own_mount_namespace:
            continue
        if any(pattern in fields[1] for pattern in patterns):
            result.append(pid)
    return sorted(set(result))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pattern", nargs="+")
    parser.add_argument("--grace", type=float, default=1.5)
    args = parser.parse_args()
    for sig in (signal.SIGTERM, signal.SIGKILL):
        pids = matching_pids(args.pattern)
        if not pids:
            break
        print(f"{sig.name}: {','.join(map(str, pids))}", flush=True)
        for pid in pids:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass
        time.sleep(args.grace)
    remaining = matching_pids(args.pattern)
    if remaining:
        print(f"Processes still present: {remaining}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
