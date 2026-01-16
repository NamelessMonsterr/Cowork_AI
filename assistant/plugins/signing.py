"""
Plugin Signing & Verification (W16.1).
Uses Ed25519 for secure, high-performance signatures.
"""
import os
import logging
import base64
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger("PluginSigning")

class PluginSigner:
    def __init__(self):
        pass

    @staticmethod
    def generate_keys(save_dir: str = "."):
        """Generate a new Ed25519 keypair for a publisher."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        # Save Private Key (Keep Safe!)
        priv_path = os.path.join(save_dir, "publisher_private.pem")
        with open(priv_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))

        # Save Public Key (Distribute)
        pub_path = os.path.join(save_dir, "publisher_public.pem")
        with open(pub_path, "wb") as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
            
        return priv_path, pub_path

    @staticmethod
    def load_private_key(path: str) -> ed25519.Ed25519PrivateKey:
        with open(path, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)

    @staticmethod
    def load_public_key(path: str) -> ed25519.Ed25519PublicKey:
        with open(path, "rb") as f:
            return serialization.load_pem_public_key(f.read())
            
    @staticmethod
    def load_public_key_from_bytes(data: bytes) -> ed25519.Ed25519PublicKey:
        return serialization.load_pem_public_key(data)

    @staticmethod
    def sign_file(file_path: str, private_key_path: str) -> str:
        """Sign a file and return hex signature."""
        private_key = PluginSigner.load_private_key(private_key_path)
        
        with open(file_path, "rb") as f:
            data = f.read()
            
        signature = private_key.sign(data)
        return signature.hex()

    @staticmethod
    def verify_file(file_path: str, signature_hex: str, public_key_path: str = None, public_key_bytes: bytes = None) -> bool:
        """Verify a file against its signature."""
        try:
            if public_key_bytes:
                public_key = PluginSigner.load_public_key_from_bytes(public_key_bytes)
            elif public_key_path:
                public_key = PluginSigner.load_public_key(public_key_path)
            else:
                raise ValueError("Must provide public_key_path or public_key_bytes")

            signature = bytes.fromhex(signature_hex)
            
            with open(file_path, "rb") as f:
                data = f.read()
                
            public_key.verify(signature, data)
            return True
        except Exception as e:
            logger.warning(f"Signature verification failed: {e}")
            return False

    @staticmethod
    def verify_with_raw_hex(file_path: str, signature_hex: str, public_key_hex: str) -> bool:
        """Verify using raw hex-encoded public key (32 bytes)."""
        try:
            # 1. Load Raw Key
            key_bytes = bytes.fromhex(public_key_hex)
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(key_bytes)
            
            # 2. Verify
            signature = bytes.fromhex(signature_hex)
            with open(file_path, "rb") as f:
                data = f.read()
            public_key.verify(signature, data)
            return True
        except Exception as e:
            logger.error(f"Hex Verification Failed: {e}")
            return False
