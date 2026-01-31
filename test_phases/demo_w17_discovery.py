"""
W17 Verification - Peer Discovery.
"""

import sys
import os
import time
import logging

sys.path.append(os.getcwd())

from assistant.team.discovery import PeerDiscovery

# Configure logging to see discovery output
logging.basicConfig(level=logging.INFO)


def test_discovery():
    print("🧪 Testing Peer Discovery...")

    # Agent A
    agent_a = PeerDiscovery(agent_id="agent-A", agent_name="Agent A", port=8001)

    # Agent B
    agent_b = PeerDiscovery(agent_id="agent-B", agent_name="Agent B", port=8002)

    try:
        print("Starting Agent A...")
        agent_a.start()

        print("Starting Agent B...")
        agent_b.start()

        print("Waiting for beacons (6s)...")
        time.sleep(6)

        peers_a = agent_a.get_peers()
        peers_b = agent_b.get_peers()

        print(f"Agent A found: {[p.id for p in peers_a]}")
        print(f"Agent B found: {[p.id for p in peers_b]}")

        found_b = any(p.id == "agent-B" for p in peers_a)
        found_a = any(p.id == "agent-A" for p in peers_b)

        if found_b and found_a:
            print("✅ Discovery SUCCESS: Both agents found each other.")
        else:
            print("❌ Discovery FAILED.")
            # Debug
            if not found_b:
                print("  Agent A did not find B.")
            if not found_a:
                print("  Agent B did not find A.")

    finally:
        agent_a.stop()
        agent_b.stop()


if __name__ == "__main__":
    test_discovery()
