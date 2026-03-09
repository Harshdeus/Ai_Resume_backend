from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

load_dotenv()

FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    raise ValueError("FERNET_KEY not set in .env")

# Fernet expects key as bytes
cipher = Fernet(FERNET_KEY.encode() if isinstance(FERNET_KEY, str) else FERNET_KEY)

def encrypt_password(password: str) -> str:
    """Encrypt password and return as string"""
    encrypted = cipher.encrypt(password.encode())  # bytes
    return encrypted.decode()  # convert to string for DB

def decrypt_password(encrypted_password: str) -> str:
    """Decrypt password from string"""
    try:
        return cipher.decrypt(encrypted_password.encode()).decode()  # string -> bytes -> decrypt -> string
    except Exception:
        raise ValueError("Error decrypting password")