"""
Plugin Signing & Verification (W16.1).
Uses Ed25519 for secure, high-performance signatures.
"""

import logging
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

logger = logging.getLogger("PluginSigning")


class PluginSigner:
    def __init__(self):
        pass

    @staticmethod
    def generate_keys(save_dir: str = ".", password: bytes = None):
        """
        Generate a new Ed25519 keypair for a publisher.
        
        P0 SECURITY FIX: Private keys are now encrypted with password.
        If no password provided, generates a secure random one.
        
        Args:
            save_dir: Directory to save keys
            password: Password for private key encryption (bytes)
                     If None, generates random password and saves to .password file
        
        Returns:
            tuple: (priv_path, pub_path, password_used)
        """
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        # P0 SECURITY: Generate password if not provided
        if password is None:
            import secrets

            password = secrets.token_bytes(32)  # 256-bit random password
            password_path = os.path.join(save_dir, "publisher_private.password")
            with open(password_path, "wb") as f:
                f.write(password)
            logger.warning(
                f"⚠️ Generated random password saved to: {password_path}\n"
                f"KEEP THIS FILE SECURE! Required to use private key."
            )

        # Save Private Key - P0 FIX: Now ENCRYPTED
        priv_path = os.path.join(save_dir, "publisher_private.pem")
        with open(priv_path, "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.BestAvailableEncryption(password),
                )
            )

        # Save Public Key (Distribute)
        pub_path = os.path.join(save_dir, "publisher_public.pem")
        with open(pub_path, "wb") as f:
            f.write(
                public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
            )

        logger.info(f"✅ Generated ENCRYPTED keypair: {priv_path}, {pub_path}")
        return priv_path, pub_path, password

    @staticmethod
    def load_private_key(path: str, password: bytes = None) -> ed25519.Ed25519PrivateKey:
        """
        Load private key from PEM file.
        
        P0 SECURITY: Now supports encrypted keys (mandatory for new keys).
        
        Args:
            path: Path to private key PEM file
            password: Password for encrypted key (bytes) or None for legacy unencrypted keys
        
        Returns:
            Ed25519PrivateKey instance
        """
        with open(path, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=password)


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
    def verify_file(
        file_path: str,
        signature_hex: str,
        public_key_path: str = None,
        public_key_bytes: bytes = None,
    ) -> bool:
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
