"""Wait for the Reflex frontend to be ready, then open the browser."""

import os
import socket
import time
import webbrowser

PORT = 3000
URL = os.environ.get("PORTLESS_URL", f"http://localhost:{PORT}")
TIMEOUT = 60  # seconds


def wait_for_port(port: int, timeout: int) -> bool:
    """Wait until a port is accepting connections."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


if __name__ == "__main__":
    if wait_for_port(PORT, TIMEOUT):
        webbrowser.open(URL)
