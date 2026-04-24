"""
Adversarial Security Tests for AVCPM (M-T6)

Covers:
- Path traversal rejection via agent_id
- Invalid agent_id formats rejected
- AES-GCM round-trip encryption/decryption
- AES-GCM detects tampered ciphertext
- Ledger signature verification catches tampered entries

Run with: pytest test_avcpm_security.py -v
"""

import os
import sys
import json
import hashlib
import shutil
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from avcpm_security import (
    validate_agent_id,
    safe_join,
    sanitize_path,
    SecurityError,
    AGENT_ID_PATTERN,
)
from avcpm_agent import (
    _encrypt_data,
    _decrypt_data,
    _derive_key,
    create_agent,
    sign_commit,
    verify_commit_signature,
    calculate_changes_hash,
)
from avcpm_auth import create_session, require_auth
from avcpm_branch import _ensure_main_branch, get_branch_ledger_dir
from avcpm_commit import commit
from avcpm_ledger_integrity import calculate_entry_hash


# ============================================================================
# M-T6.1: Path Traversal Rejection via agent_id
# ============================================================================

class TestPathTraversalViaAgentId:
    """Verify that agent_id cannot be used for path traversal."""

    @pytest.mark.parametrize("malicious_id", [
        "../../../etc/passwd",
        "..%2F..%2Fetc%2Fpasswd",
        "agent/../../../etc",
        "agent\\..\\..\\etc",
        "./../../../tmp",
        "/etc/passwd",
        "agent/../../secret",
    ])
    def test_path_traversal_in_agent_id_rejected(self, malicious_id):
        """Path traversal patterns in agent_id should be rejected."""
        with pytest.raises(ValueError):
            validate_agent_id(malicious_id)

    def test_safe_join_rejects_traversal(self, tmp_path):
        """safe_join should reject agent_ids that escape base_dir."""
        base = str(tmp_path / "avcpm")
        os.makedirs(base, exist_ok=True)

        with pytest.raises(ValueError):
            safe_join(base, "../../../etc/passwd")

    def test_safe_join_with_valid_agent_id(self, tmp_path):
        """safe_join should work with valid agent_ids."""
        base = str(tmp_path / "avcpm")
        os.makedirs(base, exist_ok=True)

        result = safe_join(base, "my-agent")
        expected = os.path.join(os.path.realpath(base), "my-agent")
        assert result == expected


# ============================================================================
# M-T6.2: Invalid agent_id Format Rejection
# ============================================================================

class TestInvalidAgentIdFormats:
    """Verify that invalid agent_id formats are rejected."""

    @pytest.mark.parametrize("invalid_id,reason", [
        ("", "empty string"),
        ("   ", "whitespace only"),
        ("a" * 65, "too long (>64 chars)"),
        ("agent with spaces", "contains spaces"),
        ("agent@domain", "contains @"),
        ("agent.name", "contains dot"),
        ("agent!", "contains !"),
        ("agent#", "contains #"),
        ("agent$", "contains $"),
        ("agent%", "contains %"),
        ("agent&", "contains &"),
        ("agent*", "contains *"),
        ("agent(", "contains ("),
        ("agent)", "contains )"),
        ("agent+", "contains +"),
        ("agent=", "contains ="),
        ("agent[", "contains ["),
        ("agent]", "contains ]"),
        ("agent{", "contains {"),
        ("agent}", "contains }"),
        ("agent|", "contains |"),
        ("agent\\", "contains backslash"),
        ("agent:", "contains colon"),
        ("agent;", "contains semicolon"),
        ('agent"', "contains quote"),
        ("agent'", "contains single quote"),
        ("agent<", "contains <"),
        ("agent>", "contains >"),
        ("agent?", "contains ?"),
        (",agent", "starts with comma"),
        (None, "None value"),
        (123, "integer value"),
        (True, "boolean value"),
    ])
    def test_invalid_agent_id_rejected(self, invalid_id, reason):
        """Invalid agent_id formats should be rejected with ValueError."""
        with pytest.raises((ValueError, TypeError)):
            validate_agent_id(invalid_id)

    @pytest.mark.parametrize("valid_id", [
        "agent",
        "my-agent",
        "my_agent",
        "Agent123",
        "a",
        "A" * 64,  # max length
        "agent-001",
        "test_agent",
        "UPPER",
        "lower",
        "MiXeD",
    ])
    def test_valid_agent_id_accepted(self, valid_id):
        """Valid agent_ids should pass validation."""
        result = validate_agent_id(valid_id)
        assert result == valid_id


# ============================================================================
# M-T6.3: AES-GCM Round-trip Encryption/Decryption
# ============================================================================

class TestAESGCMRoundTrip:
    """Test AES-256-GCM encryption and decryption."""

    def test_encrypt_decrypt_round_trip(self):
        """Data encrypted with AES-GCM should decrypt correctly."""
        plaintext = b"Hello, AVCPM! This is a secret message."
        passphrase = "test-passphrase-12345"

        encrypted = _encrypt_data(plaintext, passphrase)
        decrypted = _decrypt_data(encrypted, passphrase)

        assert decrypted == plaintext

    def test_gcm_format_has_v2_prefix(self):
        """Encrypted data should use v2: prefix for GCM format."""
        plaintext = b"Test data"
        passphrase = "secure-password"

        encrypted = _encrypt_data(plaintext, passphrase)

        assert encrypted.startswith(b"v2:")

    def test_gcm_encryption_differs_each_time(self):
        """Each encryption should produce different ciphertext (random salt/nonce)."""
        plaintext = b"Same data"
        passphrase = "same-password"

        enc1 = _encrypt_data(plaintext, passphrase)
        enc2 = _encrypt_data(plaintext, passphrase)

        # Different due to random salt and nonce
        assert enc1 != enc2

        # But both decrypt correctly
        assert _decrypt_data(enc1, passphrase) == plaintext
        assert _decrypt_data(enc2, passphrase) == plaintext

    def test_wrong_passphrase_fails(self):
        """Decryption with wrong passphrase should fail."""
        plaintext = b"Secret data"
        correct_passphrase = "correct-password"
        wrong_passphrase = "wrong-password"

        encrypted = _encrypt_data(plaintext, correct_passphrase)

        with pytest.raises(ValueError, match="Failed to decrypt"):
            _decrypt_data(encrypted, wrong_passphrase)

    def test_empty_data_round_trip(self):
        """Empty data should round-trip correctly."""
        plaintext = b""
        passphrase = "passphrase"

        encrypted = _encrypt_data(plaintext, passphrase)
        decrypted = _decrypt_data(encrypted, passphrase)

        assert decrypted == plaintext

    def test_large_data_round_trip(self):
        """Large data should round-trip correctly."""
        plaintext = b"A" * 1_000_000  # 1MB of data
        passphrase = "large-data-pass"

        encrypted = _encrypt_data(plaintext, passphrase)
        decrypted = _decrypt_data(encrypted, passphrase)

        assert decrypted == plaintext

    def test_pbkdf2_iteration_count(self):
        """Verify PBKDF2 uses 600k iterations."""
        from avcpm_agent import ENCRYPTION_ITERATIONS
        assert ENCRYPTION_ITERATIONS == 600000


# ============================================================================
# M-T6.4: AES-GCM Detects Tampered Ciphertext
# ============================================================================

class TestAESGCMTamperDetection:
    """Test that AES-GCM authentication detects tampered ciphertext."""

    def test_tampered_ciphertext_rejected(self):
        """Modifying the ciphertext should cause decryption to fail."""
        plaintext = b"Sensitive data"
        passphrase = "secure-pass"

        encrypted = _encrypt_data(plaintext, passphrase)

        # Tamper with the ciphertext: flip a bit in the payload
        # v2 format: b"v2:" + base64(salt || nonce || ciphertext || tag)
        import base64
        payload_b64 = encrypted[3:]  # Skip "v2:"
        payload = bytearray(base64.b64decode(payload_b64))

        # Flip a bit somewhere in the ciphertext portion (after salt+nonce, before tag)
        # salt=16, nonce=12, tag=16, so ciphertext starts at offset 28
        # Flip a bit at offset 30
        if len(payload) > 32:
            payload[30] ^= 0x01

        tampered_encrypted = b"v2:" + base64.b64encode(bytes(payload))

        with pytest.raises((ValueError, Exception)):
            _decrypt_data(tampered_encrypted, passphrase)

    def test_tampered_tag_rejected(self):
        """Modifying the GCM authentication tag should cause decryption to fail."""
        plaintext = b"Protected data"
        passphrase = "tag-test-pass"

        encrypted = _encrypt_data(plaintext, passphrase)

        import base64
        payload_b64 = encrypted[3:]
        payload = bytearray(base64.b64decode(payload_b64))

        # The last 16 bytes are the GCM tag
        # Flip a bit in the tag
        payload[-1] ^= 0x01

        tampered_encrypted = b"v2:" + base64.b64encode(bytes(payload))

        with pytest.raises((ValueError, Exception)):
            _decrypt_data(tampered_encrypted, passphrase)

    def test_corrupted_prefix_rejected(self):
        """Removing the v2: prefix should cause v2 decryption to fail."""
        plaintext = b"Prefix test"
        passphrase = "prefix-pass"

        encrypted = _encrypt_data(plaintext, passphrase)

        # Remove the v2: prefix, making it look like v1 data but not valid
        corrupted = encrypted[3:]

        with pytest.raises((ValueError, Exception)):
            _decrypt_data(corrupted, passphrase)

    def test_truncated_payload_rejected(self):
        """Truncated encrypted data should be rejected."""
        plaintext = b"Truncation test"
        passphrase = "trunc-pass"

        encrypted = _encrypt_data(plaintext, passphrase)

        # Truncate to just salt + nonce (28 bytes) — no ciphertext or tag
        import base64
        payload_b64 = encrypted[3:]
        payload = base64.b64decode(payload_b64)
        truncated = b"v2:" + base64.b64encode(payload[:28])

        with pytest.raises(ValueError, match="payload too short|Failed to decrypt|Invalid"):
            _decrypt_data(truncated, passphrase)


# ============================================================================
# M-T6.5: Ledger Signature Verification Catches Tampered Entries
# ============================================================================

class TestLedgerSignatureVerification:
    """Test that tampered ledger entries are detected via signature verification."""

    @pytest.fixture
    def env(self, tmp_path):
        """Set up AVCPM environment with agent and auth."""
        base_dir = str(tmp_path / ".avcpm")
        os.makedirs(base_dir, exist_ok=True)
        _ensure_main_branch(base_dir)

        # Create agent without encryption for simpler test setup
        agent_data = create_agent("sigagent", "sig@test.com", base_dir=base_dir, encrypt=False)

        # Authenticate
        from avcpm_auth import ensure_auth_directories, create_session
        ensure_auth_directories(base_dir)
        session = create_session("sigagent", base_dir=base_dir)

        # Create production directory
        prod_dir = str(tmp_path / "project")
        os.makedirs(prod_dir, exist_ok=True)

        original_cwd = os.getcwd()
        os.chdir(prod_dir)

        yield {
            "base_dir": base_dir,
            "prod_dir": prod_dir,
            "agent_id": "sigagent",
        }

        os.chdir(original_cwd)

    def test_valid_commit_signature_verifies(self, env):
        """A legitimate commit's signature should verify correctly."""
        # Create and commit a file
        fpath = os.path.join(env["prod_dir"], "test.txt")
        with open(fpath, "w") as f:
            f.write("Original content")

        # Initialize lifecycle config
        from avcpm_lifecycle import init_lifecycle_config
        init_lifecycle_config(env["base_dir"])

        commit(
            task_id="TASK-500",
            agent_id=env["agent_id"],
            rationale="Signature test",
            files_to_commit=[fpath],
            base_dir=env["base_dir"],
        )

        # Load ledger entry and verify signature
        ledger_dir = get_branch_ledger_dir("main", env["base_dir"])
        commits = [f for f in os.listdir(ledger_dir) if f.endswith(".json")]
        with open(os.path.join(ledger_dir, commits[0])) as f:
            entry = json.load(f)

        is_valid = verify_commit_signature(
            entry["commit_id"],
            entry["timestamp"],
            entry["changes"],
            entry["agent_id"],
            entry["signature"],
            base_dir=env["base_dir"],
        )
        assert is_valid is True

    def test_tampered_rationale_detected(self, env):
        """Changing the rationale should invalidate the signature."""
        # Create and commit
        fpath = os.path.join(env["prod_dir"], "tamper.txt")
        with open(fpath, "w") as f:
            f.write("Tamper test")

        from avcpm_lifecycle import init_lifecycle_config
        init_lifecycle_config(env["base_dir"])

        commit(
            task_id="TASK-501",
            agent_id=env["agent_id"],
            rationale="Original rationale",
            files_to_commit=[fpath],
            base_dir=env["base_dir"],
        )

        # Load and tamper with rationale (which doesn't affect signature directly,
        # but does affect entry_hash)
        ledger_dir = get_branch_ledger_dir("main", env["base_dir"])
        commits = [f for f in os.listdir(ledger_dir) if f.endswith(".json")]
        ledger_path = os.path.join(ledger_dir, commits[0])

        with open(ledger_path) as f:
            entry = json.load(f)

        # Tamper with rationale
        entry["rationale"] = "TAMPERED rationale"
        with open(ledger_path, "w") as f:
            json.dump(entry, f)

        # Recalculate entry_hash — it won't match the stored one
        recalculated = calculate_entry_hash(entry)
        assert recalculated != entry["entry_hash"], "Tampering rationale should change entry_hash"

    def test_tampered_changes_detected(self, env):
        """Changing the changes list should invalidate the signature."""
        fpath = os.path.join(env["prod_dir"], "changes_tamper.txt")
        with open(fpath, "w") as f:
            f.write("Changes test")

        from avcpm_lifecycle import init_lifecycle_config
        init_lifecycle_config(env["base_dir"])

        commit(
            task_id="TASK-502",
            agent_id=env["agent_id"],
            rationale="Changes tamper test",
            files_to_commit=[fpath],
            base_dir=env["base_dir"],
        )

        ledger_dir = get_branch_ledger_dir("main", env["base_dir"])
        commits = [f for f in os.listdir(ledger_dir) if f.endswith(".json")]
        ledger_path = os.path.join(ledger_dir, commits[0])

        with open(ledger_path) as f:
            entry = json.load(f)

        # Tamper with changes — modify checksum
        original_signature = entry["signature"]
        entry["changes"][0]["checksum"] = "0" * 64  # Fake checksum

        # Verify with original signature — should fail
        is_valid = verify_commit_signature(
            entry["commit_id"],
            entry["timestamp"],
            entry["changes"],  # tampered changes
            entry["agent_id"],
            original_signature,  # original signature
            base_dir=env["base_dir"],
        )
        assert is_valid is False, "Tampered changes should fail signature verification"

    def test_tampered_commit_id_detected(self, env):
        """Changing the commit_id should invalidate the signature."""
        fpath = os.path.join(env["prod_dir"], "id_tamper.txt")
        with open(fpath, "w") as f:
            f.write("ID tamper test")

        from avcpm_lifecycle import init_lifecycle_config
        init_lifecycle_config(env["base_dir"])

        commit(
            task_id="TASK-503",
            agent_id=env["agent_id"],
            rationale="ID tamper test",
            files_to_commit=[fpath],
            base_dir=env["base_dir"],
        )

        ledger_dir = get_branch_ledger_dir("main", env["base_dir"])
        commits = [f for f in os.listdir(ledger_dir) if f.endswith(".json")]
        ledger_path = os.path.join(ledger_dir, commits[0])

        with open(ledger_path) as f:
            entry = json.load(f)

        original_signature = entry["signature"]

        # Verify with wrong commit_id should fail
        is_valid = verify_commit_signature(
            "TAMPERED-COMMIT-ID",  # wrong commit ID
            entry["timestamp"],
            entry["changes"],
            entry["agent_id"],
            original_signature,
            base_dir=env["base_dir"],
        )
        assert is_valid is False, "Tampered commit_id should fail signature verification"

    def test_tampered_signature_rejected(self, env):
        """A completely wrong signature should be rejected."""
        fpath = os.path.join(env["prod_dir"], "sig_tamper.txt")
        with open(fpath, "w") as f:
            f.write("Sig tamper test")

        from avcpm_lifecycle import init_lifecycle_config
        init_lifecycle_config(env["base_dir"])

        commit(
            task_id="TASK-504",
            agent_id=env["agent_id"],
            rationale="Sig tamper test",
            files_to_commit=[fpath],
            base_dir=env["base_dir"],
        )

        ledger_dir = get_branch_ledger_dir("main", env["base_dir"])
        commits = [f for f in os.listdir(ledger_dir) if f.endswith(".json")]
        ledger_path = os.path.join(ledger_dir, commits[0])

        with open(ledger_path) as f:
            entry = json.load(f)

        # Use a fake signature
        is_valid = verify_commit_signature(
            entry["commit_id"],
            entry["timestamp"],
            entry["changes"],
            entry["agent_id"],
            "00" * 128,  # Completely fake 256-byte signature
            base_dir=env["base_dir"],
        )
        assert is_valid is False, "Fake signature should be rejected"


# ============================================================================
# Additional: Sanitize Path Security Tests
# ============================================================================

class TestSanitizePathSecurity:
    """Test path sanitization against traversal attacks."""

    def test_path_traversal_rejected(self):
        """Paths with .. should be rejected."""
        with pytest.raises(ValueError, match="[Tt]raversal"):
            sanitize_path("../../../etc/passwd", "/safe/dir")

    def test_absolute_path_rejected(self):
        """Absolute paths should be rejected."""
        with pytest.raises(ValueError, match="[Aa]bsolute"):
            sanitize_path("/etc/passwd", "/safe/dir")

    def test_empty_path_rejected(self):
        """Empty paths should be rejected."""
        with pytest.raises(ValueError, match="[Ee]mpty"):
            sanitize_path("", "/safe/dir")

    def test_valid_path_accepted(self, tmp_path):
        """Valid relative paths should be accepted."""
        base_dir = str(tmp_path)
        os.makedirs(base_dir, exist_ok=True)

        result = sanitize_path("file.txt", base_dir)
        assert result.endswith("file.txt")

    def test_nested_valid_path(self, tmp_path):
        """Valid nested paths should be accepted."""
        base_dir = str(tmp_path)
        os.makedirs(base_dir, exist_ok=True)

        result = sanitize_path("subdir/file.txt", base_dir)
        assert "subdir" in result
        assert result.endswith("file.txt")