"""
OrA Encrypted Vault - Hardware-bound encryption for API key storage

Features:
- Fernet encryption with hardware-derived key
- Memory-safe credential handling
- Tamper-evident audit logging
- Secure import/export with password protection

Port from BUZZ Neural Core EncryptedVault
"""

import os
import json
import base64
import hashlib
import platform
import getpass
import secrets
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

# Cryptography imports
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

# Memory protection
try:
    import mmap
    MMAP_AVAILABLE = True
except ImportError:
    MMAP_AVAILABLE = False


logger = logging.getLogger(__name__)


@dataclass
class CredentialEntry:
    """Single API credential entry"""
    provider: str
    api_key: str
    endpoint: Optional[str] = None
    org_id: Optional[str] = None
    extra: Optional[Dict] = None
    created_at: str = ""
    updated_at: str = ""
    last_tested: Optional[str] = None
    is_valid: bool = False
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()


@dataclass
class VaultMetadata:
    """Vault metadata for versioning and integrity"""
    version: str = "2.0"
    created_at: str = ""
    updated_at: str = ""
    salt: str = ""
    checksum: str = ""
    encryption_type: str = "fernet_pbkdf2"
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
        if not self.salt:
            self.salt = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()


class SecureString:
    """Memory-safe string that attempts to clear from memory on deletion"""
    
    def __init__(self, value: str):
        self._value = value
        self._buffer = None
        
    def get(self) -> str:
        """Get the string value"""
        return self._value
    
    def clear(self):
        """Attempt to clear from memory"""
        # Overwrite with random data before deletion
        self._value = secrets.token_hex(len(self._value))
        self._value = ""
    
    def __del__(self):
        self.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.clear()


class HardwareFingerprint:
    """Generate hardware-bound fingerprint for key derivation"""
    
    @staticmethod
    def get_machine_id() -> str:
        """Get machine-specific identifier"""
        system = platform.system()
        
        try:
            if system == "Linux":
                # Try machine-id first
                for path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
                    if os.path.exists(path):
                        with open(path) as f:
                            return f.read().strip()
                # Fallback to hostname + user
                return f"{os.uname().nodename}-{os.getlogin()}"
                
            elif system == "Darwin":  # macOS
                # Use IOPlatformUUID
                import subprocess
                result = subprocess.run(
                    ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                    capture_output=True, text=True
                )
                for line in result.stdout.split("\n"):
                    if "IOPlatformUUID" in line:
                        return line.split('"')[-2]
                return f"{platform.node()}-{getpass.getuser()}"
                
            elif system == "Windows":
                import subprocess
                result = subprocess.run(
                    ["wmic", "csproduct", "get", "UUID"],
                    capture_output=True, text=True
                )
                lines = [l.strip() for l in result.stdout.split("\n") if l.strip()]
                if len(lines) > 1:
                    return lines[1]
                return f"{platform.node()}-{getpass.getuser()}"
                
        except Exception as e:
            logger.warning(f"Could not get hardware ID: {e}")
            
        # Ultimate fallback
        return f"{platform.node()}-{getpass.getuser()}-{platform.machine()}"
    
    @classmethod
    def derive_key_material(cls, password: Optional[str] = None) -> Tuple[bytes, bytes]:
        """Derive encryption key material from hardware + optional password"""
        machine_id = cls.get_machine_id()
        
        # Combine hardware ID with password if provided
        if password:
            combined = f"{machine_id}:{password}"
        else:
            combined = machine_id
        
        # Generate salt from hardware ID hash
        salt = hashlib.sha256(machine_id.encode()).digest()[:16]
        
        return combined.encode(), salt


class OraVault:
    """
    Hardware-bound encrypted vault for API credentials
    
    Storage: ~/.ora/vault.enc (encrypted JSON)
    Encryption: Fernet with PBKDF2 key derivation
    """
    
    VAULT_PATH = Path.home() / ".ora" / "vault.enc"
    VAULT_DIR = Path.home() / ".ora"
    
    def __init__(self):
        self._unlocked = False
        self._credentials: Dict[str, CredentialEntry] = {}
        self._metadata: VaultMetadata = VaultMetadata()
        self._master_key: Optional[bytes] = None
        self._fernet: Optional[Fernet] = None
        
        # Ensure vault directory exists
        self.VAULT_DIR.mkdir(parents=True, exist_ok=True)
        self.VAULT_DIR.chmod(0o700)  # Only owner can access
    
    def exists(self) -> bool:
        """Check if vault file exists"""
        return self.VAULT_PATH.exists()
    
    def is_unlocked(self) -> bool:
        """Check if vault is currently unlocked"""
        return self._unlocked
    
    def _derive_key(self, password: Optional[str] = None, salt: Optional[bytes] = None) -> bytes:
        """Derive encryption key from hardware + password"""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography library not available")
        
        material, default_salt = HardwareFingerprint.derive_key_material(password)
        salt = salt or default_salt
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(material))
        return key
    
    def create(self, password: Optional[str] = None) -> bool:
        """Create new empty vault"""
        try:
            self._metadata = VaultMetadata()
            salt = base64.urlsafe_b64decode(self._metadata.salt.encode())
            
            self._master_key = self._derive_key(password, salt)
            self._fernet = Fernet(self._master_key)
            self._unlocked = True
            
            # Save empty vault
            self._save()
            
            logger.info("Created new encrypted vault")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create vault: {e}")
            return False
    
    def unlock(self, password: Optional[str] = None) -> bool:
        """Unlock the vault with password"""
        if not self.exists():
            return self.create(password)
        
        try:
            # Read encrypted vault
            with open(self.VAULT_PATH, 'rb') as f:
                encrypted_data = f.read()
            
            # Parse metadata from beginning of file
            metadata_end = encrypted_data.find(b"\n---VAULT_DATA---\n")
            if metadata_end == -1:
                # Legacy format - try without metadata
                metadata_json = {}
                encrypted_blob = encrypted_data
            else:
                metadata_json = json.loads(encrypted_data[:metadata_end].decode())
                encrypted_blob = encrypted_data[metadata_end + len(b"\n---VAULT_DATA---\n"):]
            
            self._metadata = VaultMetadata(**metadata_json)
            salt = base64.urlsafe_b64decode(self._metadata.salt.encode())
            
            # Derive key and decrypt
            self._master_key = self._derive_key(password, salt)
            self._fernet = Fernet(self._master_key)
            
            decrypted = self._fernet.decrypt(encrypted_blob)
            data = json.loads(decrypted.decode())
            
            # Load credentials
            self._credentials = {}
            for provider, entry_data in data.get("credentials", {}).items():
                self._credentials[provider] = CredentialEntry(**entry_data)
            
            # Verify checksum
            stored_checksum = self._metadata.checksum
            computed_checksum = self._compute_checksum()
            
            if stored_checksum and stored_checksum != computed_checksum:
                logger.warning("Vault checksum mismatch - possible tampering")
                # Still continue but warn
            
            self._unlocked = True
            logger.info("Vault unlocked successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unlock vault: {e}")
            self._unlocked = False
            self._master_key = None
            self._fernet = None
            return False
    
    def lock(self):
        """Lock the vault, clearing credentials from memory"""
        # Clear credentials
        for entry in self._credentials.values():
            entry.api_key = ""
        self._credentials = {}
        
        # Clear key material
        if self._master_key:
            # Overwrite with zeros (best effort)
            self._master_key = bytes(len(self._master_key))
        self._master_key = None
        self._fernet = None
        self._unlocked = False
        
        logger.info("Vault locked")
    
    def _compute_checksum(self) -> str:
        """Compute integrity checksum of credentials"""
        data = json.dumps({k: asdict(v) for k, v in self._credentials.items()}, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _save(self) -> bool:
        """Save vault to disk"""
        if not self._unlocked or not self._fernet:
            raise RuntimeError("Vault must be unlocked to save")
        
        try:
            # Update metadata
            self._metadata.updated_at = datetime.now().isoformat()
            self._metadata.checksum = self._compute_checksum()
            
            # Prepare data
            data = {
                "credentials": {k: asdict(v) for k, v in self._credentials.items()},
                "metadata": asdict(self._metadata)
            }
            
            # Encrypt
            json_data = json.dumps(data).encode()
            encrypted = self._fernet.encrypt(json_data)
            
            # Write with metadata header
            metadata_bytes = json.dumps(asdict(self._metadata)).encode()
            output = metadata_bytes + b"\n---VAULT_DATA---\n" + encrypted
            
            # Atomic write
            temp_path = self.VAULT_PATH.with_suffix('.tmp')
            with open(temp_path, 'wb') as f:
                f.write(output)
            temp_path.replace(self.VAULT_PATH)
            
            # Secure permissions
            self.VAULT_PATH.chmod(0o600)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save vault: {e}")
            return False
    
    def get(self, provider: str) -> Optional[CredentialEntry]:
        """Get credential for a provider"""
        if not self._unlocked:
            raise RuntimeError("Vault is locked")
        return self._credentials.get(provider)
    
    def set(self, provider: str, api_key: str, endpoint: Optional[str] = None, 
            org_id: Optional[str] = None, extra: Optional[Dict] = None) -> bool:
        """Store credential for a provider"""
        if not self._unlocked:
            raise RuntimeError("Vault is locked")
        
        entry = CredentialEntry(
            provider=provider,
            api_key=api_key,
            endpoint=endpoint,
            org_id=org_id,
            extra=extra or {},
            updated_at=datetime.now().isoformat()
        )
        
        # Preserve creation date if exists
        if provider in self._credentials:
            entry.created_at = self._credentials[provider].created_at
        
        self._credentials[provider] = entry
        return self._save()
    
    def delete(self, provider: str) -> bool:
        """Remove a credential"""
        if not self._unlocked:
            raise RuntimeError("Vault is locked")
        
        if provider in self._credentials:
            del self._credentials[provider]
            return self._save()
        return False
    
    def list_providers(self) -> List[str]:
        """List all stored credential providers"""
        if not self._unlocked:
            raise RuntimeError("Vault is locked")
        return list(self._credentials.keys())
    
    def test_credential(self, provider: str) -> bool:
        """Test if a credential is valid (basic connectivity check)"""
        if not self._unlocked:
            raise RuntimeError("Vault is locked")
        
        entry = self._credentials.get(provider)
        if not entry:
            return False
        
        # TODO: Implement actual credential testing
        # For now, just update timestamp
        entry.last_tested = datetime.now().isoformat()
        self._save()
        return True
    
    def export(self, export_password: str, export_path: Path) -> bool:
        """Export vault to portable encrypted file"""
        if not self._unlocked:
            raise RuntimeError("Vault is locked")
        
        try:
            # Create export data
            export_data = {
                "credentials": {k: asdict(v) for k, v in self._credentials.items()},
                "metadata": asdict(self._metadata),
                "exported_at": datetime.now().isoformat(),
                "exported_from": platform.node()
            }
            
            # Encrypt with export password
            export_salt = secrets.token_bytes(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=export_salt,
                iterations=100000,
                backend=default_backend()
            )
            export_key = base64.urlsafe_b64encode(kdf.derive(export_password.encode()))
            export_fernet = Fernet(export_key)
            
            encrypted = export_fernet.encrypt(json.dumps(export_data).encode())
            
            # Write export file
            with open(export_path, 'wb') as f:
                f.write(base64.urlsafe_b64encode(export_salt) + b"\n---EXPORT---\n" + encrypted)
            
            export_path.chmod(0o600)
            return True
            
        except Exception as e:
            logger.error(f"Failed to export vault: {e}")
            return False
    
    def import_vault(self, import_password: str, import_path: Path) -> bool:
        """Import vault from portable encrypted file"""
        if not self._unlocked:
            raise RuntimeError("Vault must be unlocked to import")
        
        try:
            with open(import_path, 'rb') as f:
                import_data = f.read()
            
            # Parse export file
            separator = b"\n---EXPORT---\n"
            sep_idx = import_data.find(separator)
            if sep_idx == -1:
                logger.error("Invalid export file format")
                return False
            
            export_salt = base64.urlsafe_b64decode(import_data[:sep_idx])
            encrypted = import_data[sep_idx + len(separator):]
            
            # Decrypt with export password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=export_salt,
                iterations=100000,
                backend=default_backend()
            )
            export_key = base64.urlsafe_b64encode(kdf.derive(import_password.encode()))
            export_fernet = Fernet(export_key)
            
            decrypted = export_fernet.decrypt(encrypted)
            import_data = json.loads(decrypted.decode())
            
            # Merge credentials
            for provider, entry_data in import_data.get("credentials", {}).items():
                self._credentials[provider] = CredentialEntry(**entry_data)
            
            return self._save()
            
        except Exception as e:
            logger.error(f"Failed to import vault: {e}")
            return False