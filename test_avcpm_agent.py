"""
Tests for AVCPM Agent Identity System

Tests key generation, signing, verification, and signature tampering detection.
"""

import os
import sys
import pytest
import tempfile
import json
import stat
from datetime import datetime

# Ensure we can import the module
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
    calculate_changes_hash,
    get_agents_dir,
    get_agent_dir,
    get_registry_path,
)


class TestAgentCreation:
    """Tests for agent creation and key generation."""
    
    TEST_PASSPHRASE = "secure_test_pass_123"  # Required passphrase for all tests
    
    def test_create_agent_requires_passphrase(self, tmp_path):
        """Test that creating an agent requires a passphrase."""
        base_dir = tmp_path / ".avcpm"
        
        with pytest.raises(ValueError) as exc_info:
            create_agent("Test Agent", "test@example.com", base_dir=str(base_dir))
        
        assert "Passphrase is required" in str(exc_info.value)
    
    def test_create_agent_generates_keys(self, tmp_path):
        """Test that creating an agent generates RSA key pair with encryption."""
        base_dir = tmp_path / ".avcpm"
        agent = create_agent(
            "Test Agent", 
            "test@example.com", 
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        assert "agent_id" in agent
        assert agent["name"] == "Test Agent"
        assert agent["email"] == "test@example.com"
        assert "created_at" in agent
        
        # Check keys were created
        agent_dir = get_agent_dir(agent["agent_id"], base_dir=str(base_dir))
        assert os.path.exists(os.path.join(agent_dir, "private.pem.enc"))  # Encrypted key
        assert not os.path.exists(os.path.join(agent_dir, "private.pem"))  # No plaintext key
        assert os.path.exists(os.path.join(agent_dir, "public.pem"))
    
    def test_private_key_permissions(self, tmp_path):
        """Test that encrypted private key has restrictive permissions (600)."""
        base_dir = tmp_path / ".avcpm"
        agent = create_agent(
            "Test Agent", 
            "test@example.com", 
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        agent_dir = get_agent_dir(agent["agent_id"], base_dir=str(base_dir))
        private_key_path = os.path.join(agent_dir, "private.pem.enc")  # Encrypted key
        
        # Check permissions are 600 (readable/writable only by owner)
        mode = os.stat(private_key_path).st_mode
        assert stat.S_IMODE(mode) == 0o600
    
    def test_passphrase_too_short(self, tmp_path):
        """Test that short passphrase is rejected."""
        base_dir = tmp_path / ".avcpm"
        
        with pytest.raises(ValueError) as exc_info:
            create_agent(
                "Test Agent",
                "test@example.com",
                base_dir=str(base_dir),
                passphrase="short"
            )
        
        assert "at least 8 characters" in str(exc_info.value)
    
    def test_registry_created(self, tmp_path):
        """Test that agent is registered in registry.json with encryption flag."""
        base_dir = tmp_path / ".avcpm"
        agent = create_agent(
            "Test Agent", 
            "test@example.com", 
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        registry_path = get_registry_path(base_dir=str(base_dir))
        assert os.path.exists(registry_path)
        
        with open(registry_path, "r") as f:
            registry = json.load(f)
        
        assert agent["agent_id"] in registry["agents"]
        assert registry["agents"][agent["agent_id"]]["name"] == "Test Agent"
        assert registry["agents"][agent["agent_id"]]["email"] == "test@example.com"
        assert registry["agents"][agent["agent_id"]].get("encrypted") is True
    
    def test_unique_agent_ids(self, tmp_path):
        """Test that multiple agents get unique IDs."""
        base_dir = tmp_path / ".avcpm"
        agent1 = create_agent(
            "Agent 1", 
            "agent1@example.com", 
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        agent2 = create_agent(
            "Agent 2", 
            "agent2@example.com", 
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        assert agent1["agent_id"] != agent2["agent_id"]


class TestAgentManagement:
    """Tests for agent listing and retrieval."""
    
    def test_list_agents_empty(self, tmp_path):
        """Test listing agents when none exist."""
        base_dir = tmp_path / ".avcpm"
        agents = list_agents(base_dir=str(base_dir))
        assert agents == {}
    
    def test_list_agents_with_multiple(self, tmp_path):
        """Test listing multiple agents."""
        base_dir = tmp_path / ".avcpm"
        TEST_PASSPHRASE = "secure_test_pass_123"
        agent1 = create_agent(
            "Agent 1", 
            "agent1@example.com", 
            base_dir=str(base_dir),
            passphrase=TEST_PASSPHRASE
        )
        agent2 = create_agent(
            "Agent 2", 
            "agent2@example.com", 
            base_dir=str(base_dir),
            passphrase=TEST_PASSPHRASE
        )
        
        agents = list_agents(base_dir=str(base_dir))
        
        assert len(agents) == 2
        assert agent1["agent_id"] in agents
        assert agent2["agent_id"] in agents
    
    def test_get_agent_existing(self, tmp_path):
        """Test getting an existing agent."""
        base_dir = tmp_path / ".avcpm"
        TEST_PASSPHRASE = "secure_test_pass_123"
        agent = create_agent(
            "Test Agent", 
            "test@example.com", 
            base_dir=str(base_dir),
            passphrase=TEST_PASSPHRASE
        )
        
        result = get_agent(agent["agent_id"], base_dir=str(base_dir))
        
        assert result is not None
        assert result["agent_id"] == agent["agent_id"]
        assert result["name"] == "Test Agent"
        assert result["email"] == "test@example.com"
    
    def test_get_agent_nonexistent(self, tmp_path):
        """Test getting a non-existent agent."""
        base_dir = tmp_path / ".avcpm"
        result = get_agent("nonexistent", base_dir=str(base_dir))
        assert result is None
    
    def test_get_public_key(self, tmp_path):
        """Test retrieving public key."""
        base_dir = tmp_path / ".avcpm"
        TEST_PASSPHRASE = "secure_test_pass_123"
        agent = create_agent(
            "Test Agent", 
            "test@example.com", 
            base_dir=str(base_dir),
            passphrase=TEST_PASSPHRASE
        )
        
        public_key = get_public_key(agent["agent_id"], base_dir=str(base_dir))
        
        assert public_key is not None
        assert b"BEGIN PUBLIC KEY" in public_key
        assert b"END PUBLIC KEY" in public_key
    
    def test_get_public_key_nonexistent(self, tmp_path):
        """Test retrieving public key for non-existent agent."""
        base_dir = tmp_path / ".avcpm"
        public_key = get_public_key("nonexistent", base_dir=str(base_dir))
        assert public_key is None


class TestSigning:
    """Tests for data signing and verification."""
    
    TEST_PASSPHRASE = "secure_test_pass_123"
    
    def test_sign_string_data(self, tmp_path):
        """Test signing string data with passphrase."""
        base_dir = tmp_path / ".avcpm"
        agent = create_agent(
            "Test Agent", 
            "test@example.com", 
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        data = "Hello, World!"
        signature = sign_data(agent["agent_id"], data, base_dir=str(base_dir), passphrase=self.TEST_PASSPHRASE)
        
        assert isinstance(signature, bytes)
        assert len(signature) > 0
        
        assert isinstance(signature, bytes)
        assert len(signature) > 0
    
    def test_sign_bytes_data(self, tmp_path):
        """Test signing bytes data with passphrase."""
        base_dir = tmp_path / ".avcpm"
        agent = create_agent(
            "Test Agent", 
            "test@example.com", 
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        data = b"Hello, World!"
        signature = sign_data(agent["agent_id"], data, base_dir=str(base_dir), passphrase=self.TEST_PASSPHRASE)
        
        assert isinstance(signature, bytes)
        assert len(signature) > 0
    
    def test_verify_valid_signature(self, tmp_path):
        """Test verifying a valid signature."""
        base_dir = tmp_path / ".avcpm"
        agent = create_agent(
            "Test Agent", 
            "test@example.com", 
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        data = "Hello, World!"
        signature = sign_data(agent["agent_id"], data, base_dir=str(base_dir), passphrase=self.TEST_PASSPHRASE)
        
        assert verify_signature(agent["agent_id"], data, signature, base_dir=str(base_dir)) is True
    
    def test_verify_valid_signature_bytes(self, tmp_path):
        """Test verifying a valid signature for bytes data."""
        base_dir = tmp_path / ".avcpm"
        agent = create_agent(
            "Test Agent", 
            "test@example.com", 
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        data = b"Hello, World!"
        signature = sign_data(agent["agent_id"], data, base_dir=str(base_dir), passphrase=self.TEST_PASSPHRASE)
        
        assert verify_signature(agent["agent_id"], data, signature, base_dir=str(base_dir)) is True
    
    def test_sign_requires_passphrase(self, tmp_path):
        """Test that signing requires passphrase."""
        base_dir = tmp_path / ".avcpm"
        agent = create_agent(
            "Test Agent", 
            "test@example.com", 
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        data = "Hello, World!"
        with pytest.raises(ValueError) as exc_info:
            sign_data(agent["agent_id"], data, base_dir=str(base_dir))
        
        assert "Passphrase is required" in str(exc_info.value)


class TestTamperingDetection:
    """Tests for signature tampering detection."""
    
    TEST_PASSPHRASE = "secure_test_pass_123"
    
    def test_tampered_data(self, tmp_path):
        """Test that tampered data fails verification."""
        base_dir = tmp_path / ".avcpm"
        agent = create_agent(
            "Test Agent", 
            "test@example.com", 
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        data = "Hello, World!"
        signature = sign_data(agent["agent_id"], data, base_dir=str(base_dir), passphrase=self.TEST_PASSPHRASE)
        
        # Try to verify with tampered data
        tampered_data = "Hello, Tampered!"
        assert verify_signature(agent["agent_id"], tampered_data, signature, base_dir=str(base_dir)) is False
    
    def test_tampered_signature(self, tmp_path):
        """Test that tampered signature fails verification."""
        base_dir = tmp_path / ".avcpm"
        agent = create_agent(
            "Test Agent", 
            "test@example.com", 
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        data = "Hello, World!"
        signature = sign_data(agent["agent_id"], data, base_dir=str(base_dir), passphrase=self.TEST_PASSPHRASE)
        
        # Tamper with signature (flip a byte)
        tampered_signature = signature[:-1] + bytes([signature[-1] ^ 0xFF])
        assert verify_signature(agent["agent_id"], data, tampered_signature, base_dir=str(base_dir)) is False
    
    def test_wrong_agent_signature(self, tmp_path):
        """Test that signature from wrong agent fails verification."""
        base_dir = tmp_path / ".avcpm"
        agent1 = create_agent(
            "Agent 1", 
            "agent1@example.com", 
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        agent2 = create_agent(
            "Agent 2", 
            "agent2@example.com", 
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        data = "Hello, World!"
        signature = sign_data(agent1["agent_id"], data, base_dir=str(base_dir), passphrase=self.TEST_PASSPHRASE)
        
        # Try to verify with wrong agent
        assert verify_signature(agent2["agent_id"], data, signature, base_dir=str(base_dir)) is False
    
    def test_empty_signature(self, tmp_path):
        """Test that empty signature fails verification."""
        base_dir = tmp_path / ".avcpm"
        agent = create_agent(
            "Test Agent", 
            "test@example.com", 
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        data = "Hello, World!"
        assert verify_signature(agent["agent_id"], data, b"", base_dir=str(base_dir)) is False


class TestCommitIntegration:
    """Tests for commit signing and verification."""
    
    TEST_PASSPHRASE = "secure_test_pass_123"
    
    def test_calculate_changes_hash(self):
        """Test changes hash calculation."""
        changes = [
            {"file": "test.py", "checksum": "abc123"},
            {"file": "main.py", "checksum": "def456"}
        ]
        
        hash1 = calculate_changes_hash(changes)
        hash2 = calculate_changes_hash(changes)
        
        # Same input should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length
    
    def test_calculate_changes_hash_order_independence(self):
        """Test that changes hash is order-independent."""
        changes1 = [
            {"file": "a.py", "checksum": "abc"},
            {"file": "b.py", "checksum": "def"}
        ]
        changes2 = [
            {"file": "b.py", "checksum": "def"},
            {"file": "a.py", "checksum": "abc"}
        ]
        
        hash1 = calculate_changes_hash(changes1)
        hash2 = calculate_changes_hash(changes2)
        
        # Same files/checksums should produce same hash regardless of order
        assert hash1 == hash2
    
    def test_sign_commit(self, tmp_path):
        """Test signing commit metadata with passphrase."""
        base_dir = tmp_path / ".avcpm"
        agent = create_agent(
            "Test Agent",
            "test@example.com",
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        changes = [
            {"file": "test.py", "checksum": "abc123"},
            {"file": "main.py", "checksum": "def456"}
        ]
        
        commit_meta = sign_commit(
            "20250101120000",
            datetime.now().isoformat(),
            changes,
            agent["agent_id"],
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        assert "commit_id" in commit_meta
        assert "timestamp" in commit_meta
        assert "changes_hash" in commit_meta
        assert "agent_id" in commit_meta
        assert "signature" in commit_meta
        assert commit_meta["agent_id"] == agent["agent_id"]
    
    def test_verify_commit_signature(self, tmp_path):
        """Test verifying commit signature."""
        base_dir = tmp_path / ".avcpm"
        agent = create_agent(
            "Test Agent",
            "test@example.com",
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        changes = [
            {"file": "test.py", "checksum": "abc123"},
            {"file": "main.py", "checksum": "def456"}
        ]
        
        timestamp = datetime.now().isoformat()
        
        commit_meta = sign_commit(
            "20250101120000",
            timestamp,
            changes,
            agent["agent_id"],
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        # Verify the signature
        is_valid = verify_commit_signature(
            "20250101120000",
            timestamp,
            changes,
            agent["agent_id"],
            commit_meta["signature"],
            base_dir=str(base_dir)
        )
        
        assert is_valid is True
    
    def test_commit_tampering_detection(self, tmp_path):
        """Test that tampered commit fails verification."""
        base_dir = tmp_path / ".avcpm"
        agent = create_agent(
            "Test Agent",
            "test@example.com",
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        changes = [
            {"file": "test.py", "checksum": "abc123"},
            {"file": "main.py", "checksum": "def456"}
        ]
        
        timestamp = datetime.now().isoformat()
        
        commit_meta = sign_commit(
            "20250101120000",
            timestamp,
            changes,
            agent["agent_id"],
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        # Tamper with the changes
        tampered_changes = [
            {"file": "test.py", "checksum": "tampered"},  # Changed checksum
            {"file": "main.py", "checksum": "def456"}
        ]
        
        # Verify with tampered changes should fail
        is_valid = verify_commit_signature(
            "20250101120000",
            timestamp,
            tampered_changes,
            agent["agent_id"],
            commit_meta["signature"],
            base_dir=str(base_dir)
        )
        
        assert is_valid is False
    
    def test_commit_wrong_timestamp(self, tmp_path):
        """Test that wrong timestamp fails verification."""
        base_dir = tmp_path / ".avcpm"
        agent = create_agent(
            "Test Agent",
            "test@example.com",
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        changes = [
            {"file": "test.py", "checksum": "abc123"}
        ]
        
        timestamp = datetime.now().isoformat()
        
        commit_meta = sign_commit(
            "20250101120000",
            timestamp,
            changes,
            agent["agent_id"],
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        # Verify with wrong timestamp
        is_valid = verify_commit_signature(
            "20250101120000",
            "2025-01-02T00:00:00",  # Different timestamp
            changes,
            agent["agent_id"],
            commit_meta["signature"],
            base_dir=str(base_dir)
        )
        
        assert is_valid is False


class TestIntegration:
    """Integration tests with Phase 1 modules."""
    
    TEST_PASSPHRASE = "secure_test_pass_123"
    
    def test_integration_with_configurable_base_dir(self, tmp_path):
        """Test that all functions work with configurable base_dir."""
        base_dir = tmp_path / "custom_avcpm"
        
        # Create agent
        agent = create_agent(
            "Integration Agent",
            "integration@example.com",
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        # List agents
        agents = list_agents(base_dir=str(base_dir))
        assert agent["agent_id"] in agents
        
        # Get agent
        retrieved = get_agent(agent["agent_id"], base_dir=str(base_dir))
        assert retrieved["name"] == "Integration Agent"
        
        # Get public key
        public_key = get_public_key(agent["agent_id"], base_dir=str(base_dir))
        assert public_key is not None
        
        # Sign data
        signature = sign_data(agent["agent_id"], "test data", base_dir=str(base_dir), passphrase=self.TEST_PASSPHRASE)
        assert signature is not None
        
        # Verify signature
        assert verify_signature(agent["agent_id"], "test data", signature, base_dir=str(base_dir)) is True
    
    def test_end_to_end_file_signing(self, tmp_path):
        """Test end-to-end file signing workflow."""
        base_dir = tmp_path / ".avcpm"
        
        # Create agent
        agent = create_agent(
            "File Agent",
            "file@example.com",
            base_dir=str(base_dir),
            passphrase=self.TEST_PASSPHRASE
        )
        
        # Create a test file
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("This is important data that needs to be signed.")
        
        # Sign the file
        with open(test_file, "rb") as f:
            data = f.read()
        signature = sign_data(agent["agent_id"], data, base_dir=str(base_dir), passphrase=self.TEST_PASSPHRASE)
        
        # Verify the signature
        assert verify_signature(agent["agent_id"], data, signature, base_dir=str(base_dir)) is True
        
        # Verify fails with tampered data
        tampered_data = data + b"tampered"
        assert verify_signature(agent["agent_id"], tampered_data, signature, base_dir=str(base_dir)) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
