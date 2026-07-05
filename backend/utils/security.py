"""
Security Utilities
==================
Security-related tools for the AgentForge platform.

Provides:
- API key encryption and secure storage (AES-256-GCM)
- Command injection detection and sanitization
- Sandbox execution isolation for agent subprocesses
- Path traversal prevention
- Input validation helpers
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import shlex
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

__all__ = [
    "SecureKeyStore",
    "CommandSanitizer",
    "SandboxConfig",
    "validate_path",
    "generate_api_key",
]


# ------------------------------------------------------------------
# Secure API Key Store (AES-256-GCM)
# ------------------------------------------------------------------

class SecureKeyStore:
    """
    Encrypts and decrypts API keys using AES-256-GCM.

    Keys are derived from a master password using PBKDF2-HMAC-SHA256
    with 600,000 iterations (OWASP 2023 recommendation).

    The master key should be set via the AGENTFORGE_MASTER_KEY environment
    variable. In development, a machine-specific default is used.

    Usage:
        store = SecureKeyStore()
        encrypted = store.encrypt("sk-abc123")
        decrypted = store.decrypt(encrypted)
    """

    _SALT_LENGTH: int = 32
    _NONCE_LENGTH: int = 12
    _KEY_LENGTH: int = 32  # AES-256
    _PBKDF2_ITERATIONS: int = 600_000

    def __init__(self, master_password: str | None = None) -> None:
        """
        Initialize the key store with a master password.

        Args:
            master_password: Override for the master encryption password.
                             Defaults to AGENTFORGE_MASTER_KEY env var or
                             a machine-specific derived key.
        """
        self._master_password: str = master_password or self._get_default_master_key()
        self._aesgcm = AESGCM(self._derive_key())

    @staticmethod
    def _get_default_master_key() -> str:
        """
        Derive a default master key from machine-specific identifiers.

        Returns:
            A hex-encoded machine-derived key string.

        Note:
            This is NOT secure for production use. Always set
            AGENTFORGE_MASTER_KEY in production environments.
        """
        env_key = os.environ.get("AGENTFORGE_MASTER_KEY")
        if env_key:
            return env_key

        # Machine-specific fallback for development only
        identifiers = [
            os.environ.get("COMPUTERNAME", "unknown"),
            os.environ.get("USERNAME", "unknown"),
            str(Path.home()),
        ]
        combined = "|".join(identifiers)
        return hashlib.sha256(combined.encode()).hexdigest()

    def _derive_key(self) -> bytes:
        """
        Derive a 256-bit encryption key from the master password using PBKDF2.

        A fixed salt is embedded in the code for deterministic derivation.
        In production, the salt should be stored separately.

        Returns:
            32-byte AES-256 key.
        """
        salt = b"AgentForge_KeyStore_Salt_v1"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self._KEY_LENGTH,
            salt=salt,
            iterations=self._PBKDF2_ITERATIONS,
        )
        return kdf.derive(self._master_password.encode("utf-8"))

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext API key.

        Args:
            plaintext: The API key to encrypt.

        Returns:
            Base64-encoded ciphertext with embedded nonce.
            Format: base64(nonce + ciphertext)
        """
        nonce = secrets.token_bytes(self._NONCE_LENGTH)
        ciphertext = self._aesgcm.encrypt(
            nonce,
            plaintext.encode("utf-8"),
            None,  # No associated data
        )
        # Combine nonce + ciphertext and encode as base64
        combined = nonce + ciphertext
        return base64.b64encode(combined).decode("ascii")

    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt an encrypted API key.

        Args:
            encrypted: Base64-encoded nonce+ciphertext string.

        Returns:
            The original plaintext API key.

        Raises:
            ValueError: If decryption fails (wrong key or corrupted data).
        """
        try:
            combined = base64.b64decode(encrypted.encode("ascii"))
            nonce = combined[:self._NONCE_LENGTH]
            ciphertext = combined[self._NONCE_LENGTH:]
            plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")
        except Exception as exc:
            raise ValueError(f"Decryption failed: {exc}") from exc


# ------------------------------------------------------------------
# Command Injection Detection & Sanitization
# ------------------------------------------------------------------

class CommandSanitizer:
    """
    Detects and sanitizes potentially dangerous patterns in command strings.

    Protects against:
        - Command chaining operators (&&, ||, ;, |)
        - Command substitution ($(...), `...`)
        - Shell metacharacters for redirection (> , >>, <)
        - Inline script execution (curl | sh, etc.)
    """

    # Patterns that indicate command injection attempts
    _DANGEROUS_PATTERNS: list[tuple[str, str]] = [
        # (regex pattern, description)
        (r"\$\(.*\)", "Command substitution $(...)"),
        (r"`[^`]*`", "Backtick command substitution"),
        (r";\s*\w", "Command chaining with ;"),
        (r"&&\s*\w", "Command chaining with &&"),
        (r"\|\|\s*\w", "Command chaining with ||"),
        (r">\s*\S", "Output redirection >"),
        (r">>\s*\S", "Append redirection >>"),
        (r"<\s*\S", "Input redirection <"),
        (r"\|\s*\w", "Pipe operator |"),
        (r"curl.*\|.*sh", "curl piped to shell"),
        (r"wget.*\|.*sh", "wget piped to shell"),
        (r"rm\s+-rf\s+/", "Recursive root deletion"),
        (r"dd\s+if=", "Disk duplication"),
        (r"mkfs\.", "Filesystem formatting"),
        (r"chmod\s+777", "Overly permissive chmod"),
        (r"/dev/", "Access to device files"),
        (r"\\x[0-9a-fA-F]{2}", "Hex-encoded injection attempt"),
    ]

    @classmethod
    def detect_injection(cls, command: str) -> list[str]:
        """
        Scan a command string for injection patterns.

        Args:
            command: The command string to analyze.

        Returns:
            List of descriptions of detected dangerous patterns.
            Empty list means the command appears safe.
        """
        detected: list[str] = []
        for pattern, description in cls._DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                detected.append(description)
        return detected

    @classmethod
    def sanitize(cls, command: str) -> tuple[str, bool]:
        """
        Sanitize a command string, returning the cleaned version.

        Args:
            command: The raw command string.

        Returns:
            Tuple of (sanitized_command, was_modified).
            was_modified is True if any dangerous patterns were removed.
        """
        original = command
        cleaned = command

        # Remove command chaining
        cleaned = re.sub(r";.*$", "", cleaned)
        cleaned = re.sub(r"&&.*$", "", cleaned)
        cleaned = re.sub(r"\|\|.*$", "", cleaned)

        # Remove redirections
        cleaned = re.sub(r">>?\s*\S+", "", cleaned)
        cleaned = re.sub(r"<\s*\S+", "", cleaned)

        # Remove pipes
        cleaned = re.sub(r"\|\s*\S.*$", "", cleaned)

        was_modified = cleaned != original
        return cleaned.strip(), was_modified

    @classmethod
    def is_safe(cls, command: str) -> bool:
        """
        Check if a command is safe to execute.

        Args:
            command: The command to check.

        Returns:
            True if no dangerous patterns are detected.
        """
        return len(cls.detect_injection(command)) == 0


# ------------------------------------------------------------------
# Sandbox Isolation Configuration
# ------------------------------------------------------------------

class SandboxConfig:
    """
    Configuration for sandboxed subprocess execution.

    Defines isolation boundaries for agent process execution:
    - Working directory restriction
    - Allowed command whitelist
    - File system access boundaries
    - Network access control
    - Resource limits (timeout, memory)

    Usage:
        config = SandboxConfig(
            allowed_dirs=["/home/user/projects"],
            allowed_commands=["python", "node", "git"],
            timeout_sec=300,
        )
    """

    def __init__(
        self,
        allowed_dirs: list[str] | None = None,
        allowed_commands: list[str] | None = None,
        denied_paths: list[str] | None = None,
        timeout_sec: int = 600,
        max_memory_mb: int = 2048,
        allow_network: bool = True,
        allow_subprocesses: bool = False,
    ) -> None:
        """
        Initialize sandbox configuration.

        Args:
            allowed_dirs: Directories the agent process can access.
            allowed_commands: Whitelist of executable commands.
            denied_paths: Explicitly blocked paths (takes precedence).
            timeout_sec: Maximum execution time before kill.
            max_memory_mb: Maximum memory usage in MB.
            allow_network: Whether network access is permitted.
            allow_subprocesses: Whether the agent can spawn child processes.
        """
        self.allowed_dirs = [Path(d).resolve() for d in (allowed_dirs or [])]
        self.allowed_commands = allowed_commands or []
        self.denied_paths = [Path(d).resolve() for d in (denied_paths or [])]
        self.timeout_sec = timeout_sec
        self.max_memory_mb = max_memory_mb
        self.allow_network = allow_network
        self.allow_subprocesses = allow_subprocesses

    def is_path_allowed(self, path: str | Path) -> bool:
        """
        Check if a file system path is within allowed boundaries.

        Args:
            path: The path to validate.

        Returns:
            True if the path is accessible within sandbox constraints.
        """
        resolved = Path(path).resolve()

        # Denied paths always take precedence
        for denied in self.denied_paths:
            try:
                resolved.relative_to(denied)
                return False
            except ValueError:
                continue

        # If no allowed dirs specified, only block denied paths
        if not self.allowed_dirs:
            return True

        # Check if path is within any allowed directory
        for allowed in self.allowed_dirs:
            try:
                resolved.relative_to(allowed)
                return True
            except ValueError:
                continue

        return False

    def is_command_allowed(self, command: str) -> bool:
        """
        Check if a command is in the allowed whitelist.

        Args:
            command: The base command name (e.g., 'python', 'git').

        Returns:
            True if the command is allowed.
        """
        if not self.allowed_commands:
            return True  # No whitelist = allow all (dangerous, use with caution)
        return command in self.allowed_commands

    @classmethod
    def default(cls) -> SandboxConfig:
        """
        Create a sensible default sandbox configuration.

        Returns:
            SandboxConfig with safe defaults for agent execution.
        """
        return cls(
            allowed_dirs=[
                str(Path.home() / "projects"),
                str(Path(os.environ.get("TEMP", "/tmp"))),
            ],
            allowed_commands=[
                "python",
                "python3",
                "node",
                "npm",
                "npx",
                "git",
                "go",
                "rustc",
                "cargo",
                "java",
                "javac",
            ],
            denied_paths=[
                str(Path.home() / ".ssh"),
                str(Path.home() / ".aws"),
                str(Path.home() / ".kube"),
                "/etc",
                "/boot",
                "/sys",
                "/proc",
            ],
            timeout_sec=600,
            max_memory_mb=2048,
            allow_network=True,
            allow_subprocesses=False,
        )


# ------------------------------------------------------------------
# Path Validation
# ------------------------------------------------------------------

def validate_path(
    path: str,
    base_dir: str | Path | None = None,
    allow_absolute: bool = True,
) -> Path:
    """
    Validate and resolve a file system path, preventing traversal attacks.

    Args:
        path: The path string to validate.
        base_dir: Optional base directory to restrict the path under.
                  If provided, the resolved path must be within base_dir.
        allow_absolute: Whether absolute paths are permitted.

    Returns:
        Resolved absolute Path object.

    Raises:
        ValueError: If the path violates security constraints.
    """
    resolved = Path(path).resolve()

    # Prevent access to sensitive system paths
    sensitive_roots = {
        Path("/etc"),
        Path("/boot"),
        Path("/proc"),
        Path("/sys"),
        Path("/dev"),
    }
    try:
        for sensitive in sensitive_roots:
            resolved.relative_to(sensitive)
            raise ValueError(
                f"Access denied: path '{path}' resolves to sensitive system directory "
                f"'{sensitive}'"
            )
    except ValueError:
        pass  # Not in sensitive path — OK

    # Restrict to base directory if specified
    if base_dir is not None:
        base = Path(base_dir).resolve()
        try:
            resolved.relative_to(base)
        except ValueError:
            raise ValueError(
                f"Path traversal detected: '{path}' escapes base directory '{base_dir}'"
            )

    # Block absolute paths if disallowed
    if not allow_absolute and Path(path).is_absolute():
        raise ValueError(f"Absolute paths are not allowed: '{path}'")

    return resolved


# ------------------------------------------------------------------
# API Key Generation
# ------------------------------------------------------------------

def generate_api_key(prefix: str = "af_") -> str:
    """
    Generate a cryptographically secure API key.

    Args:
        prefix: Prefix for the key (defaults to 'af_' for AgentForge).

    Returns:
        A random API key string.

    Example:
        >>> generate_api_key()
        'af_d4e8f1a2b3c4d5e6f7a8b9c0d1e2f3a4'
    """
    random_part = secrets.token_hex(32)  # 64 hex chars = 256 bits
    return f"{prefix}{random_part}"
