import hashlib
import hmac

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def get_fernet():
    key = getattr(settings, "NIN_ENCRYPTION_KEY", "")
    if not key:
        raise ImproperlyConfigured(
            "NIN_ENCRYPTION_KEY is required. Generate one with: "
            'python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (TypeError, ValueError) as exc:
        raise ImproperlyConfigured(
            "NIN_ENCRYPTION_KEY is invalid. It must be a URL-safe base64-encoded "
            "32-byte key."
        ) from exc


def encrypt_nin(raw_nin):
    return get_fernet().encrypt(raw_nin.encode()).decode()


def decrypt_nin(encrypted_nin):
    if not encrypted_nin:
        return ""
    try:
        return get_fernet().decrypt(encrypted_nin.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Could not decrypt the stored NIN.") from exc


def hash_nin(raw_nin):
    key = getattr(settings, "NIN_ENCRYPTION_KEY", "")
    if not key:
        raise ImproperlyConfigured(
            "NIN_ENCRYPTION_KEY is required to hash a NIN for duplicate detection."
        )
    digest_key = hashlib.sha256(key.encode()).digest()
    return hmac.new(digest_key, raw_nin.encode(), hashlib.sha256).hexdigest()
