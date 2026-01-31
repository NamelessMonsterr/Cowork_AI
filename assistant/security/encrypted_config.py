"""
Encrypted Configuration Storage
CRITICAL SECURITY: Encrypts API keys and sensitive data at rest
"""

import json
import os
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkfd2 import PBKDF2HMAC
import base64

class EncryptedConfig:
    """Encrypts and decrypts configuration data using Fernet (AES-128)."""
    
    def __init__(self, password: str | None = None):
        """
        Initialize encryption with a password-derived key.
        
        Args:
            password: Master password. If None, uses env var COWORK_MASTER_KEY
        """
        # Get master password from environment or parameter
        master_password = password or os.getenv("COWORK_MASTER_KEY")
        
        if not master_password:
            raise ValueError(
                "CRITICAL SECURITY: No master password set! "
                "Set COWORK_MASTER_KEY environment variable."
            )
        
        # Derive encryption key from password using PBKDF2
        salt = b'cowork_salt_v1'  # Static salt for key derivation
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,  # OWASP 2023 recommendation
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        self.cipher = Fernet(key)
    
    def encrypt_file(self, data: dict, filepath: str | Path) -> None:
        """
        Encrypt dictionary and save to file.
        
        Args:
            data: Data to encrypt (must be JSON-serializable)
            filepath: Path to encrypted file
        """
        # Serialize to JSON
        json_data = json.dumps(data).encode()
        
        # Encrypt
        encrypted = self.cipher.encrypt(json_data)
        
        # Write to file
        Path(filepath).write_bytes(encrypted)
    
    def decrypt_file(self, filepath: str | Path) -> dict:
        """
        Decrypt file and return dictionary.
        
        Args:
            filepath: Path to encrypted file
            
        Returns:
            Decrypted data as dictionary
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If decryption fails (wrong password or corrupted data)
        """
        # Read encrypted data
        encrypted = Path(filepath).read_bytes()
        
        # Decrypt
        try:
            decrypted = self.cipher.decrypt(encrypted)
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}. Wrong password or corrupted file.") from e
        
        # Deserialize JSON
        return json.loads(decrypted)
    
    def migrate_plaintext_to_encrypted(self, plaintext_path: str | Path, encrypted_path: str | Path) -> None:
        """
        Migrate existing plaintext JSON config to encrypted format.
        
        Args:
            plaintext_path: Path to existing plaintext JSON
            encrypted_path: Path for new encrypted file
        """
        # Read plaintext
        with open(plaintext_path) as f:
            data = json.load(f)
        
        # Encrypt and save
        self.encrypt_file(data, encrypted_path)
        
        # Securely delete plaintext (overwrite then delete)
        Path(plaintext_path).write_text("MIGRATED_TO_ENCRYPTED")
        Path(plaintext_path).unlink()
