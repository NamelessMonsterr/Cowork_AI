"""
W17.1 Peer Discovery (UDP Multicast).
Allows agents on the same LAN to find each other.
"""

import json
import logging
import socket
import struct
import threading
import time

from pydantic import BaseModel

logger = logging.getLogger("TeamDiscovery")

MULTICAST_GROUP = "224.0.0.1"
MULTICAST_PORT = 8767


class PeerInfo(BaseModel):
    id: str
    name: str
    ip: str
    port: int
    role: str = "worker"
    status: str = "idle"
    last_seen: float = 0.0


class PeerDiscovery:
    def __init__(self, agent_id: str, agent_name: str, port: int):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.port = port  # API port (tcp)

        self.peers: dict[str, PeerInfo] = {}
        self.running = False
        self.sock: socket.socket | None = None

    def start(self):
        self.running = True

        # Setup Multicast Socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind
        try:
            # Windows requires binding to a specific interface IP for multicast receiving sometimes,
            # but 0.0.0.0 works for listening generally.
            self.sock.bind(("", MULTICAST_PORT))
        except Exception as e:
            logger.error(f"Failed to bind discovery socket: {e}")
            return

        # Join Group
        try:
            mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            # Set TTL
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        except Exception as e:
            logger.error(f"Multicast Join Failed: {e}")
            # Fallback?

        # Start Threads
        threading.Thread(target=self._listen_loop, daemon=True).start()
        threading.Thread(target=self._beacon_loop, daemon=True).start()
        threading.Thread(target=self._cleanup_loop, daemon=True).start()

        logger.info(f"📡 Peer Discovery Started (ID: {self.agent_id})")

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()

    def get_peers(self) -> list[PeerInfo]:
        return list(self.peers.values())

    def _beacon_loop(self):
        """Send presence beacon every 5s."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

        while self.running:
            try:
                # Resolve local IP (best effort)
                host_ip = socket.gethostbyname(socket.gethostname())

                payload = {
                    "id": self.agent_id,
                    "name": self.agent_name,
                    "ip": host_ip,
                    "port": self.port,
                    "role": "worker",
                    "status": "idle",  # TODO: wire to actual status
                }
                msg = json.dumps(payload).encode("utf-8")
                sock.sendto(msg, (MULTICAST_GROUP, MULTICAST_PORT))

            except Exception as e:
                logger.debug(f"Beacon error: {e}")

            time.sleep(5)

    def _listen_loop(self):
        """Receive beacons."""
        while self.running and self.sock:
            try:
                data, addr = self.sock.recvfrom(1024)
                info = json.loads(data.decode("utf-8"))

                pid = info.get("id")
                if pid and pid != self.agent_id:
                    # Register/Update Peer
                    info["last_seen"] = time.time()
                    # Use detected IP if payload IP is localhost/0.0.0.0?
                    # But discovery sends its own IP.

                    self.peers[pid] = PeerInfo(**info)

            except Exception:
                # logger.debug(f"Listen error: {e}")
                pass

    def _cleanup_loop(self):
        """Remove stale peers."""
        while self.running:
            time.sleep(10)
            now = time.time()
            stale = [pid for pid, p in self.peers.items() if now - p.last_seen > 15]
            for pid in stale:
                logger.info(f"Peer Lost: {pid}")
                del self.peers[pid]
