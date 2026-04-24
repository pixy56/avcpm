"""
Tests for Sprint 1 Security Fixes:
- C4: Encrypt private keys by default
- M-S1: Replace AES-CBC with AES-GCM
- M-S8: Close TOCTOU in symlink helpers
"""

import os
import sys
import pytest
import tempfile
import json
import stat
import warnings

# Ensure we can import the modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from avcpm_agent import (
    create_agent,
    list_agents,
    get_agent,
    get_public_key,
    sign_data,
    verify_signature,
    sign_commit,
    verify_commit_signature,
    _encrypt_data,
    _decrypt_data,
    _decrypt_data_v1,
    _decrypt_data_v2,
    _V1_PREFIX,
    _V2_PREFIX,
    ENCRYPTION_SALT_LENGTH,
    ENCRYPTION_IV_LENGTH,
    ENCRYPTION_NONCE_LENGTH,
    ENCRYPTION_TAG_LENGTH,
    get_agent_dir,
    get_registry_path,
)
from avcpm_security import (
    safe_open_nofollow,
    safe_read,
    safe_write,
    safe_copy,
    safe_exists,
    SecurityError,
)


# ============================================================================
# C4: Encrypt private keys by default
# ============================================================================

class TestEncryptByDefault:
    """Test that create_agent encrypts private keys by default (C4)."""

    def test_create_agent_default_encrypts(self, tmp_path):
        """Private key should be encrypted by default when passphrase provided."""
        base_dir = tmp_path / ".avcpm"
        agent = create_agent("Test", "test@example.com", base_dir=str(base_dir), passphrase="secretpass123")
        
        agent_dir = get_agent_dir(agent["agent_id"], base_dir=str(base_dir))
        # Should have .enc file, not plain .pem
        assert os.path.exists(os.path.join(agent_dir, "private.pem.enc"))
        assert not os.path.exists(os.path.join(agent_dir, "private.pem"))
        
        # Registry should mark encrypted
        registry_path = get_registry_path(base_dir=str(base_dir))
        with open(registry_path) as f:
            registry = json.load(f)
        assert registry["agents"][agent["agent_id"]]["encrypted"] is True

    def test_create_agent_encrypt_false_needs_passphrase(self, tmp_path):
        """Creating without passphrase and encrypt=True should raise ValueError."""
        base_dir = tmp_path / ".avcpm"
        with pytest.raises(ValueError, match="encryption is mandatory"):
            create_agent("Test", "test@example.com", base_dir=str(base_dir), passphrase=None, encrypt=True)

    def test_create_agent_no_encrypt_stores_plain(self, tmp_path):
        """With encrypt=False, private key should be stored unencrypted with warning."""
        base_dir = tmp_path / ".avcpm"
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            agent = create_agent("Test", "test@example.com", base_dir=str(base_dir), passphrase=None, encrypt=False)
            # Should emit UserWarning about unencrypted storage
            assert any("unencrypted" in str(warning.message).lower() for warning in w)
        
        agent_dir = get_agent_dir(agent["agent_id"], base_dir=str(base_dir))
        assert os.path.exists(os.path.join(agent_dir, "private.pem"))
        assert not os.path.exists(os.path.join(agent_dir, "private.pem.enc"))

    def test_no_encrypt_no_passphrase(self, tmp_path):
        """encrypt=False with passphrase=None should work (but warn)."""
        base_dir = tmp_path / ".avcpm"
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            agent = create_agent("NoEnc", "noenc@example.com", base_dir=str(base_dir), passphrase=None, encrypt=False)
        
        assert agent is not None
        agent_dir = get_agent_dir(agent["agent_id"], base_dir=str(base_dir))
        assert os.path.exists(os.path.join(agent_dir, "private.pem"))

    def test_encrypted_key_can_sign(self, tmp_path):
        """Encrypted key should be usable for signing with passphrase."""
        base_dir = tmp_path / ".avcpm"
        agent = create_agent("Signer", "sign@example.com", base_dir=str(base_dir), passphrase="testpass12345")
        
        data = b"Test data to sign"
        signature = sign_data(agent["agent_id"], data, base_dir=str(base_dir), passphrase="testpass12345")
        assert verify_signature(agent["agent_id"], data, signature, base_dir=str(base_dir)) is True

    def test_encrypted_key_wrong_passphrase_fails(self, tmp_path):
        """Wrong passphrase should fail to decrypt."""
        base_dir = tmp_path / ".avcpm"
        agent = create_agent("Signer", "sign@example.com", base_dir=str(base_dir), passphrase="correctpass123")
        
        with pytest.raises(ValueError, match="Failed to decrypt"):
            sign_data(agent["agent_id"], b"data", base_dir=str(base_dir), passphrase="wrongpass12345")


# ============================================================================
# M-S1: Replace AES-CBC with AES-GCM
# ============================================================================

class TestAESGCMEncryption:
    """Test that AES-256-GCM encryption works correctly (M-S1)."""

    def test_encrypt_decrypt_roundtrip(self):
        """Data encrypted with _encrypt_data should decrypt correctly."""
        plaintext = b"Hello, AES-GCM world!"
        passphrase = "test_passphrase_123"
        
        encrypted = _encrypt_data(plaintext, passphrase)
        decrypted = _decrypt_data(encrypted, passphrase)
        
        assert decrypted == plaintext

    def test_encrypt_produces_v2_format(self):
        """New encryption should produce v2: prefix."""
        plaintext = b"test data"
        passphrase = "passphrase123"
        
        encrypted = _encrypt_data(plaintext, passphrase)
        assert encrypted.startswith(b"v2:")

    def test_v2_format_is_base64(self):
        """v2 format payload should be valid base64."""
        import base64
        
        plaintext = b"test data for base64"
        passphrase = "passphrase123"
        
        encrypted = _encrypt_data(plaintext, passphrase)
        assert encrypted.startswith(b"v2:")
        payload_b64 = encrypted[3:]  # Strip "v2:"
        # Should not raise
        payload = base64.b64decode(payload_b64)
        
        # Payload should be: salt(16) + nonce(12) + ciphertext + tag(16)
        assert len(payload) > ENCRYPTION_SALT_LENGTH + ENCRYPTION_NONCE_LENGTH + ENCRYPTION_TAG_LENGTH

    def test_wrong_passphrase_fails(self):
        """Wrong passphrase should raise ValueError."""
        plaintext = b"secret data"
        encrypted = _encrypt_data(plaintext, "correct_pass")
        
        with pytest.raises(ValueError, match="Failed to decrypt"):
            _decrypt_data(encrypted, "wrong_pass")

    def test_tampered_ciphertext_fails(self):
        """Tampering with the encrypted data should cause decryption to fail."""
        plaintext = b"secret data"
        passphrase = "passphrase123"
        
        encrypted = _encrypt_data(plaintext, passphrase)
        # Tamper with the base64 payload
        tampered = encrypted[:-5] + b"XXXXX"
        
        with pytest.raises(Exception):
            _decrypt_data(tampered, passphrase)

    def test_encrypt_empty_data(self):
        """Encrypting empty data should work."""
        plaintext = b""
        passphrase = "passphrase123"
        
        encrypted = _encrypt_data(plaintext, passphrase)
        decrypted = _decrypt_data(encrypted, passphrase)
        assert decrypted == plaintext

    def test_encrypt_large_data(self):
        """Encrypting large data should work."""
        plaintext = b"x" * 1_000_000
        passphrase = "passphrase123"
        
        encrypted = _encrypt_data(plaintext, passphrase)
        decrypted = _decrypt_data(encrypted, passphrase)
        assert decrypted == plaintext

    def test_different_passphrases_produce_different_ciphertext(self):
        """Same plaintext with different passphrases should produce different ciphertext."""
        plaintext = b"same data"
        encrypted1 = _encrypt_data(plaintext, "pass1")
        encrypted2 = _encrypt_data(plaintext, "pass2")
        assert encrypted1 != encrypted2

    def test_same_passphrase_different_ciphertext(self):
        """Same plaintext and passphrase should produce different ciphertext (random salt/nonce)."""
        plaintext = b"same data"
        passphrase = "passphrase123"
        
        encrypted1 = _encrypt_data(plaintext, passphrase)
        encrypted2 = _encrypt_data(plaintext, passphrase)
        # Different random salt/nonce should produce different ciphertext
        assert encrypted1 != encrypted2
        # But both should decrypt correctly
        assert _decrypt_data(encrypted1, passphrase) == plaintext
        assert _decrypt_data(encrypted2, passphrase) == plaintext


class TestV1BackwardCompatibility:
    """Test backward compatibility with v1 (AES-CBC) encrypted data (M-S1)."""

    def _create_v1_ciphertext(self, plaintext: bytes, passphrase: str) -> bytes:
        """Manually create v1 format ciphertext (salt + iv + padded_ciphertext)."""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        
        salt = os.urandom(16)
        iv = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600000,
        )
        key = kdf.derive(passphrase.encode('utf-8'))
        
        # PKCS7 padding
        pad_length = 16 - (len(plaintext) % 16)
        padded = plaintext + bytes([pad_length] * pad_length)
        
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded) + encryptor.finalize()
        
        return salt + iv + ciphertext

    def test_decrypt_v1_format(self):
        """_decrypt_data should handle v1 (legacy CBC) format with deprecation warning."""
        plaintext = b"legacy CBC data"
        passphrase = "legacy_pass123"
        
        v1_data = self._create_v1_ciphertext(plaintext, passphrase)
        # v1 data should NOT start with "v2:" prefix
        assert not v1_data.startswith(b"v2:")
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            decrypted = _decrypt_data(v1_data, passphrase)
            assert decrypted == plaintext
            # Should emit DeprecationWarning
            assert any(issubclass(warning.category, DeprecationWarning) for warning in w)

    def test_decrypt_v2_format_no_warning(self):
        """Decrypting v2 format should NOT emit deprecation warning."""
        plaintext = b"new GCM data"
        passphrase = "passphrase123"
        
        encrypted = _encrypt_data(plaintext, passphrase)
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            decrypted = _decrypt_data(encrypted, passphrase)
            assert decrypted == plaintext
            # Should NOT emit DeprecationWarning
            deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
            assert len(deprecation_warnings) == 0

    def test_v1_decrypt_wrong_passphrase(self):
        """Wrong passphrase for v1 data should fail."""
        plaintext = b"legacy data"
        v1_data = self._create_v1_ciphertext(plaintext, "correct_pass")
        
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            with pytest.raises(ValueError, match="Failed to decrypt"):
                _decrypt_data(v1_data, "wrong_pass")


# ============================================================================
# M-S8: Close TOCTOU in symlink helpers
# ============================================================================

class TestSafeOpenNofollow:
    """Test safe_open_nofollow function (M-S8)."""

    def test_open_regular_file(self, tmp_path):
        """Opening a regular file should work."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"hello world")
        
        with safe_open_nofollow(str(test_file), "rb") as f:
            data = f.read()
        assert data == b"hello world"

    def test_open_symlink_rejected(self, tmp_path):
        """Opening a symlink should raise SecurityError."""
        target = tmp_path / "target.txt"
        target.write_bytes(b"secret data")
        
        link = tmp_path / "link.txt"
        link.symlink_to(target)
        
        with pytest.raises(SecurityError, match="symlink"):
            safe_open_nofollow(str(link), "rb")

    def test_open_nonexistent_file(self, tmp_path):
        """Opening a nonexistent file should raise FileNotFoundError."""
        missing = tmp_path / "missing.txt"
        with pytest.raises((FileNotFoundError, OSError)):
            safe_open_nofollow(str(missing), "rb")

    def test_write_regular_file(self, tmp_path):
        """Writing to a regular file via safe_open_nofollow should work."""
        test_file = tmp_path / "output.txt"
        
        with safe_open_nofollow(str(test_file), "wb") as f:
            f.write(b"written data")
        
        assert test_file.read_bytes() == b"written data"


class TestSafeReadTOCTOU:
    """Test safe_read with TOCTOU protection (M-S8)."""

    def test_safe_read_regular_file(self, tmp_path):
        """Reading a regular file should work."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"hello world")
        
        data = safe_read(str(test_file), str(tmp_path))
        assert data == b"hello world"

    def test_safe_read_symlink_outside_base(self, tmp_path):
        """Reading a symlink pointing outside base_dir should raise SecurityError."""
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        outside_file = outside_dir / "secret.txt"
        outside_file.write_bytes(b"secret data")
        
        inside_dir = tmp_path / "inside"
        inside_dir.mkdir()
        link = inside_dir / "link.txt"
        link.symlink_to(outside_file)
        
        with pytest.raises(SecurityError, match="Security violation"):
            safe_read(str(link), str(inside_dir))

    def test_safe_read_symlink_within_base(self, tmp_path):
        """Reading a symlink pointing within base_dir should be allowed."""
        base = tmp_path / "base"
        base.mkdir()
        target = base / "target.txt"
        target.write_bytes(b"safe data")
        
        link = base / "link.txt"
        link.symlink_to(target)
        
        data = safe_read(str(link), str(base))
        assert data == b"safe data"

    def test_safe_read_missing_file(self, tmp_path):
        """Reading a missing file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            safe_read(str(tmp_path / "missing.txt"), str(tmp_path))


class TestSafeWriteTOCTOU:
    """Test safe_write with TOCTOU protection (M-S8)."""

    def test_safe_write_regular_file(self, tmp_path):
        """Writing to a regular file should work."""
        test_file = tmp_path / "output.txt"
        safe_write(str(test_file), b"written data", str(tmp_path))
        assert test_file.read_bytes() == b"written data"

    def test_safe_write_symlink_outside_base(self, tmp_path):
        """Writing to a symlink pointing outside base_dir should raise SecurityError."""
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        outside_file = outside_dir / "target.txt"
        outside_file.write_bytes(b"original")
        
        inside_dir = tmp_path / "inside"
        inside_dir.mkdir()
        link = inside_dir / "link.txt"
        link.symlink_to(outside_file)
        
        with pytest.raises(SecurityError, match="Security violation"):
            safe_write(str(link), b"attacker data", str(inside_dir))

    def test_safe_write_symlink_within_base(self, tmp_path):
        """Writing through a symlink within base_dir should be allowed."""
        base = tmp_path / "base"
        base.mkdir()
        target = base / "target.txt"
        target.write_bytes(b"original")
        
        link = base / "link.txt"
        link.symlink_to(target)
        
        safe_write(str(link), b"updated data", str(base))
        # Should write through the symlink to the target
        assert target.read_bytes() == b"updated data"

    def test_safe_write_creates_parent_dirs(self, tmp_path):
        """safe_write should create parent directories if needed."""
        test_file = tmp_path / "subdir" / "output.txt"
        safe_write(str(test_file), b"deep data", str(tmp_path))
        assert test_file.read_bytes() == b"deep data"


class TestSafeCopyTOCTOU:
    """Test safe_copy with TOCTOU protection (M-S8)."""

    def test_safe_copy_regular_file(self, tmp_path):
        """Copying a regular file should work."""
        src = tmp_path / "src.txt"
        src.write_bytes(b"copy me")
        dst = tmp_path / "dst.txt"
        
        safe_copy(str(src), str(dst), str(tmp_path))
        assert dst.read_bytes() == b"copy me"

    def test_safe_copy_symlink_outside_base(self, tmp_path):
        """Copying a symlink pointing outside base_dir should raise SecurityError."""
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        outside_file = outside_dir / "secret.txt"
        outside_file.write_bytes(b"secret")
        
        inside_dir = tmp_path / "inside"
        inside_dir.mkdir()
        link = inside_dir / "link.txt"
        link.symlink_to(outside_file)
        
        dst = inside_dir / "dst.txt"
        with pytest.raises(SecurityError, match="Security violation"):
            safe_copy(str(link), str(dst), str(inside_dir))

    def test_safe_copy_symlink_within_base(self, tmp_path):
        """Copying a symlink pointing within base_dir should be allowed."""
        base = tmp_path / "base"
        base.mkdir()
        target = base / "target.txt"
        target.write_bytes(b"safe data")
        
        link = base / "link.txt"
        link.symlink_to(target)
        
        dst = base / "dst.txt"
        safe_copy(str(link), str(dst), str(base))
        assert dst.read_bytes() == b"safe data"

    def test_safe_copy_missing_src(self, tmp_path):
        """Copying a missing file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            safe_copy(str(tmp_path / "missing.txt"), str(tmp_path / "dst.txt"), str(tmp_path))


class TestSafeOpenNofollowAtomic:
    """Test that O_NOFOLLOW provides atomic symlink rejection (M-S8)."""

    @pytest.mark.skipif(sys.platform == "win32", reason="O_NOFOLLOW not available on Windows")
    def test_nofollow_atomic_rejection(self, tmp_path):
        """On Unix, O_NOFOLLOW should reject symlinks atomically."""
        target = tmp_path / "real.txt"
        target.write_bytes(b"real content")
        
        link = tmp_path / "symlink.txt"
        link.symlink_to(target)
        
        # This should fail with SecurityError because O_NOFOLLOW
        # will reject the symlink at the kernel level
        with pytest.raises(SecurityError, match="symlink"):
            safe_open_nofollow(str(link), "rb")

    @pytest.mark.skipif(sys.platform == "win32", reason="O_NOFOLLOW not available on Windows")
    def test_nofollow_allows_regular_file(self, tmp_path):
        """O_NOFOLLOW should allow regular files to be opened."""
        test_file = tmp_path / "regular.txt"
        test_file.write_bytes(b"regular content")
        
        with safe_open_nofollow(str(test_file), "rb") as f:
            data = f.read()
        assert data == b"regular content"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])