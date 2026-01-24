"""
AquilAuth - Password Hashing

Argon2id implementation for secure password hashing.
"""

from typing import Literal
import secrets


try:
    from argon2 import PasswordHasher as Argon2PasswordHasher
    from argon2.exceptions import VerifyMismatchError, InvalidHash
    HAS_ARGON2 = True
except ImportError:
    HAS_ARGON2 = False
    # Fallback to PBKDF2
    import hashlib


class PasswordHasher:
    """
    Password hasher using Argon2id (recommended) or PBKDF2 (fallback).
    
    Argon2id is memory-hard and GPU-resistant, making it excellent
    for password hashing. Falls back to PBKDF2-HMAC-SHA256 if argon2
    is not available.
    
    Security parameters:
    - Argon2id: time_cost=2, memory_cost=65536 (64MB), parallelism=4
    - PBKDF2: iterations=600000, hash=SHA256
    """
    
    def __init__(
        self,
        algorithm: Literal["argon2id", "pbkdf2_sha256"] | None = None,
        # Argon2 parameters
        time_cost: int = 2,
        memory_cost: int = 65536,  # 64 MB
        parallelism: int = 4,
        hash_len: int = 32,
        salt_len: int = 16,
        # PBKDF2 parameters
        iterations: int = 600000,
    ):
        """
        Initialize password hasher.
        
        Args:
            algorithm: Hash algorithm (auto-detect if None)
            time_cost: Argon2 time cost (iterations)
            memory_cost: Argon2 memory cost (KB)
            parallelism: Argon2 parallelism (threads)
            hash_len: Output hash length
            salt_len: Salt length
            iterations: PBKDF2 iterations
        """
        # Auto-detect best algorithm
        if algorithm is None:
            algorithm = "argon2id" if HAS_ARGON2 else "pbkdf2_sha256"
        
        self.algorithm = algorithm
        
        if algorithm == "argon2id":
            if not HAS_ARGON2:
                raise ImportError(
                    "argon2-cffi not installed. Install with: pip install argon2-cffi"
                )
            
            self.hasher = Argon2PasswordHasher(
                time_cost=time_cost,
                memory_cost=memory_cost,
                parallelism=parallelism,
                hash_len=hash_len,
                salt_len=salt_len,
            )
        else:
            self.iterations = iterations
            self.hash_len = hash_len
            self.salt_len = salt_len
    
    def hash(self, password: str) -> str:
        """
        Hash password.
        
        Returns encoded hash that includes algorithm, parameters, salt, and hash.
        
        Example Argon2 output:
            $argon2id$v=19$m=65536,t=2,p=4$saltbase64$hashbase64
        
        Example PBKDF2 output:
            $pbkdf2_sha256$600000$saltbase64$hashbase64
        """
        if self.algorithm == "argon2id":
            return self.hasher.hash(password)
        else:
            return self._hash_pbkdf2(password)
    
    def verify(self, password_hash: str, password: str) -> bool:
        """
        Verify password against hash.
        
        Returns True if password matches hash, False otherwise.
        Constant-time comparison to prevent timing attacks.
        """
        try:
            if password_hash.startswith("$argon2id"):
                return self._verify_argon2(password_hash, password)
            elif password_hash.startswith("$pbkdf2_sha256"):
                return self._verify_pbkdf2(password_hash, password)
            else:
                return False
        except Exception:
            return False
    
    def check_needs_rehash(self, password_hash: str) -> bool:
        """
        Check if password hash needs rehashing (parameters changed).
        
        Returns True if hash should be regenerated with new parameters.
        """
        if self.algorithm == "argon2id" and HAS_ARGON2:
            try:
                return self.hasher.check_needs_rehash(password_hash)
            except (InvalidHash, AttributeError):
                return True
        
        # For PBKDF2, check if iterations match
        if password_hash.startswith("$pbkdf2_sha256"):
            try:
                parts = password_hash.split("$")
                iterations = int(parts[2])
                return iterations != self.iterations
            except (IndexError, ValueError):
                return True
        
        return True
    
    def _hash_pbkdf2(self, password: str) -> str:
        """Hash password with PBKDF2-HMAC-SHA256."""
        salt = secrets.token_bytes(self.salt_len)
        
        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            self.iterations,
            dklen=self.hash_len,
        )
        
        # Encode in custom format: $pbkdf2_sha256$iterations$salt$hash
        import base64
        salt_b64 = base64.b64encode(salt).decode()
        hash_b64 = base64.b64encode(password_hash).decode()
        
        return f"$pbkdf2_sha256${self.iterations}${salt_b64}${hash_b64}"
    
    def _verify_argon2(self, password_hash: str, password: str) -> bool:
        """Verify Argon2 password."""
        try:
            self.hasher.verify(password_hash, password)
            return True
        except VerifyMismatchError:
            return False
    
    def _verify_pbkdf2(self, password_hash: str, password: str) -> bool:
        """Verify PBKDF2 password."""
        import base64
        
        try:
            # Parse hash: $pbkdf2_sha256$iterations$salt$hash
            parts = password_hash.split("$")
            if len(parts) != 5 or parts[1] != "pbkdf2_sha256":
                return False
            
            iterations = int(parts[2])
            salt = base64.b64decode(parts[3])
            stored_hash = base64.b64decode(parts[4])
            
            # Compute hash with same parameters
            computed_hash = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode(),
                salt,
                iterations,
                dklen=len(stored_hash),
            )
            
            # Constant-time comparison
            return secrets.compare_digest(computed_hash, stored_hash)
        
        except (IndexError, ValueError):
            return False


# ============================================================================
# Password Validation
# ============================================================================

class PasswordPolicy:
    """
    Password policy validator.
    
    Enforces:
    - Minimum length
    - Character requirements (uppercase, lowercase, digit, special)
    - Breached password check (optional, requires external API)
    - Common password blacklist
    """
    
    def __init__(
        self,
        min_length: int = 12,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = False,
        check_breached: bool = False,
    ):
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digit = require_digit
        self.require_special = require_special
        self.check_breached = check_breached
        
        # Common passwords to reject
        self.blacklist = {
            "password", "password123", "12345678", "qwerty", "abc123",
            "monkey", "1234567", "letmein", "trustno1", "dragon",
            "baseball", "iloveyou", "master", "sunshine", "ashley",
            "bailey", "passw0rd", "shadow", "123123", "654321",
        }
    
    def validate(self, password: str) -> tuple[bool, list[str]]:
        """
        Validate password against policy.
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        # Check length
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters")
        
        # Check character requirements
        if self.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if self.require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if self.require_digit and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if self.require_special:
            special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            if not any(c in special_chars for c in password):
                errors.append("Password must contain at least one special character")
        
        # Check blacklist
        if password.lower() in self.blacklist:
            errors.append("Password is too common")
        
        # Check breached passwords (requires external API)
        if self.check_breached and self._is_breached(password):
            errors.append("Password has been found in data breaches")
        
        return (len(errors) == 0, errors)
    
    def _is_breached(self, password: str) -> bool:
        """
        Check if password has been breached (Have I Been Pwned API).
        
        Uses k-anonymity: only first 5 chars of SHA1 hash sent to API.
        """
        import hashlib
        import urllib.request
        
        # Hash password
        sha1_hash = hashlib.sha1(password.encode()).hexdigest().upper()
        prefix = sha1_hash[:5]
        suffix = sha1_hash[5:]
        
        try:
            # Query API
            url = f"https://api.pwnedpasswords.com/range/{prefix}"
            response = urllib.request.urlopen(url, timeout=2)
            
            # Check if suffix in response
            hashes = response.read().decode().splitlines()
            for line in hashes:
                hash_suffix, count = line.split(":")
                if hash_suffix == suffix:
                    return True  # Password breached
            
            return False
        
        except Exception:
            # API unavailable, assume not breached
            return False


# ============================================================================
# Convenience Functions
# ============================================================================

# Global hasher instance
_default_hasher = None


def get_password_hasher() -> PasswordHasher:
    """Get default password hasher instance."""
    global _default_hasher
    
    if _default_hasher is None:
        _default_hasher = PasswordHasher()
    
    return _default_hasher


def hash_password(password: str) -> str:
    """Hash password with default hasher."""
    return get_password_hasher().hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Verify password with default hasher."""
    return get_password_hasher().verify(password_hash, password)


def validate_password(password: str, policy: PasswordPolicy | None = None) -> tuple[bool, list[str]]:
    """Validate password against policy."""
    if policy is None:
        policy = PasswordPolicy()
    
    return policy.validate(password)
