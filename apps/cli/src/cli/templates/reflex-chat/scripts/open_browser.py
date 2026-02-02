#!/usr/bin/env python3
"""Wait for localhost:3000 to be available, then open browser."""

import socket
import time
import webbrowser


def wait_for_port(port: int, host: str = "localhost", timeout: float = 30.0) -> bool:
    """Wait for a port to become available."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


if __name__ == "__main__":
    if wait_for_port(3000):
        webbrowser.open("http://localhost:3000")
