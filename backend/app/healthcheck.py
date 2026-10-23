"""Probes /healthz, for the container healthcheck: python -m app.healthcheck.

A module rather than python -c "...": Podman split that one-line check's
argument on its spaces, so the check could never pass.
"""

import sys
import urllib.request

URL = "http://127.0.0.1:8000/healthz"


def main() -> int:
    try:
        with urllib.request.urlopen(URL, timeout=3) as resp:
            return 0 if resp.status == 200 else 1
    except OSError:
        return 1


if __name__ == "__main__":
    sys.exit(main())
