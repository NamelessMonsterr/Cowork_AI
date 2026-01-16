"""
P2.2 - Port Management.
Dynamic port discovery and lock file for Electron communication.
"""
import os
import json
import socket
import logging
from typing import Optional
from pathlib import Path

from assistant.config.paths import get_appdata_dir

logger = logging.getLogger("PortManager")

PORT_FILE_NAME = "backend.port"
DEFAULT_PORT = 8765
PORT_RANGE = (8765, 8775)

def get_port_file_path() -> Path:
    """Get the port file path."""
    return get_appdata_dir() / PORT_FILE_NAME

def find_available_port(start: int = PORT_RANGE[0], end: int = PORT_RANGE[1]) -> int:
    """Find an available port in the given range."""
    for port in range(start, end + 1):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('127.0.0.1', port))
            sock.close()
            return port
        except OSError:
            continue
    
    # Fallback: let OS choose
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

def write_port_file(port: int, pid: int = None):
    """Write port info for UI discovery."""
    port_file = get_port_file_path()
    port_file.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "port": port,
        "host": "127.0.0.1",
        "pid": pid or os.getpid(),
        "version": "1.0.0"
    }
    
    with open(port_file, 'w') as f:
        json.dump(data, f)
    
    logger.info(f"Port file written: {port_file} (port={port})")

def read_port_file() -> Optional[dict]:
    """Read port info from file."""
    port_file = get_port_file_path()
    if not port_file.exists():
        return None
    
    try:
        with open(port_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read port file: {e}")
        return None

def clear_port_file():
    """Remove port file on shutdown."""
    port_file = get_port_file_path()
    if port_file.exists():
        port_file.unlink()
        logger.info("Port file cleared.")

def get_backend_url() -> Optional[str]:
    """Get the backend URL from port file (for UI/clients)."""
    data = read_port_file()
    if data:
        return f"http://{data['host']}:{data['port']}"
    return None
