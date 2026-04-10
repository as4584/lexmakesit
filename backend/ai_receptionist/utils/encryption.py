"""
Encryption utilities for secure token storage.

Uses Fernet symmetric encryption for encrypting OAuth tokens.
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

LEGACY_ENCRYPTION_SALT = b"ai-receptionist-oauth"
LEGACY_ENCRYPTION_SALT_B64 = base64.urlsafe_b64encode(LEGACY_ENCRYPTION_SALT).decode()


def _decode_salt(salt_b64: str) -> bytes:
    try:
        salt = base64.urlsafe_b64decode(salt_b64)
    except Exception as e:
        raise RuntimeError("ENCRYPTION_SALT is invalid base64") from e

    if len(salt) < 8:
        raise RuntimeError("ENCRYPTION_SALT must decode to at least 8 bytes")

    return salt


def _get_encryption_salt() -> bytes:
    encryption_salt = os.environ.get("ENCRYPTION_SALT")
    if not encryption_salt:
        return LEGACY_ENCRYPTION_SALT
    return _decode_salt(encryption_salt)


def _derive_key_from_secret(secret: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(secret.encode()))


def _get_encryption_key() -> bytes:
    """
    Get or generate encryption key for token storage.
    
    Uses ENCRYPTION_KEY env var if set, otherwise generates from ADMIN_PRIVATE_KEY.
    For production, set a dedicated ENCRYPTION_KEY environment variable.
    
    Returns:
        32-byte encryption key suitable for Fernet
    """
    # Check for dedicated encryption key
    encryption_key = os.environ.get("ENCRYPTION_KEY")
    if encryption_key:
        try:
            key = encryption_key.encode()
            Fernet(key)
            return key
        except Exception as e:
            raise RuntimeError("ENCRYPTION_KEY is invalid for Fernet") from e
    
    # Fallback: derive from ADMIN_PRIVATE_KEY and ENCRYPTION_SALT
    secret = os.environ.get("ADMIN_PRIVATE_KEY")
    if not secret:
        raise RuntimeError(
            "ENCRYPTION_KEY or ADMIN_PRIVATE_KEY must be set for token encryption"
        )

    return _derive_key_from_secret(secret, _get_encryption_salt())


def _get_key_with_explicit_salt(salt_b64: str) -> bytes:
    secret = os.environ.get("ADMIN_PRIVATE_KEY")
    if not secret:
        raise RuntimeError("ADMIN_PRIVATE_KEY must be set for salt-based token migration")
    salt = _decode_salt(salt_b64)
    return _derive_key_from_secret(secret, salt)


def encrypt_token(token: str) -> str:
    """
    Encrypt a token for secure storage.
    
    Args:
        token: Plain text token to encrypt
        
    Returns:
        Base64-encoded encrypted token
    """
    try:
        key = _get_encryption_key()
        f = Fernet(key)
        encrypted = f.encrypt(token.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Token encryption failed: {e}")
        raise


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt a stored token.
    
    Args:
        encrypted_token: Base64-encoded encrypted token
        
    Returns:
        Decrypted plain text token
    """
    key = _get_encryption_key()
    f = Fernet(key)
    try:
        decrypted = f.decrypt(encrypted_token.encode())
        return decrypted.decode()
    except Exception:
        current_salt = os.environ.get("ENCRYPTION_SALT")
        if not current_salt:
            logger.error("Token decryption failed using legacy salt")
            raise

        secret = os.environ.get("ADMIN_PRIVATE_KEY")
        if not secret:
            logger.error("Token decryption fallback unavailable: ADMIN_PRIVATE_KEY missing")
            raise

        try:
            legacy_key = _derive_key_from_secret(secret, LEGACY_ENCRYPTION_SALT)
            legacy_decrypted = Fernet(legacy_key).decrypt(encrypted_token.encode())
            logger.warning("Token decrypted with legacy salt fallback; migration needed")
            return legacy_decrypted.decode()
        except Exception as e:
            logger.error(f"Token decryption failed: {e}")
            raise


def encrypt_token_with_salt(token: str, salt_b64: str) -> str:
    key = _get_key_with_explicit_salt(salt_b64)
    f = Fernet(key)
    return f.encrypt(token.encode()).decode()


def decrypt_token_with_salt(encrypted_token: str, salt_b64: str) -> str:
    key = _get_key_with_explicit_salt(salt_b64)
    f = Fernet(key)
    return f.decrypt(encrypted_token.encode()).decode()


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.
    
    Use this to generate an ENCRYPTION_KEY for your .env file.
    
    Returns:
        Base64-encoded 32-byte key
    """
    return Fernet.generate_key().decode()


def generate_encryption_salt() -> str:
    """
    Generate a new base64-encoded random salt for PBKDF2 derivation.

    Returns:
        Base64-encoded random salt bytes
    """
    return base64.urlsafe_b64encode(os.urandom(16)).decode()
