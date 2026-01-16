"""
W19.4 Sync Crypto (AES-GCM).
Default Mode: E2E Encryption using a generated key stored locally.
"""
import os
import base64
import json
import logging
from typing import Tuple, Optional

logger = logging.getLogger("SyncCrypto")

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    logger.warning("cryptography not installed. E2E sync encryption valid only in mock.")

class SyncCrypto:
    def __init__(self, key_hex: str = None):
        if not HAS_CRYPTO:
            self.key = b'mock_key_32_bytes_len___________'  # Fallback for dev without libs
            return
            
        if key_hex:
            self.key = bytes.fromhex(key_hex)
        else:
             # Auto-generate if missing (and persist?)
             # For MVP, we pass it in. If None, generate new.
             self.key = AESGCM.generate_key(bit_length=256)

    def get_key_hex(self) -> str:
        return self.key.hex()

    def encrypt_payload(self, payload: dict) -> str:
        """Encrypt dictionary to base64 string."""
        data = json.dumps(payload).encode('utf-8')
        
        if not HAS_CRYPTO:
            # Mock Encryption (Base64 only)
            return base64.b64encode(data).decode('utf-8')
            
        aesgcm = AESGCM(self.key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        # Format: nonce + ciphertext -> base64
        return base64.b64encode(nonce + ciphertext).decode('utf-8')

    def decrypt_payload(self, blob: str) -> dict:
        """Decrypt base64 string to dictionary."""
        raw = base64.b64decode(blob)
        
        if not HAS_CRYPTO:
            return json.loads(raw.decode('utf-8'))
            
        nonce = raw[:12]
        ciphertext = raw[12:]
        aesgcm = AESGCM(self.key)
        
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(plaintext.decode('utf-8'))
