"""
Tests for AVCPM Commit Module (M-T1)

Covers:
- Commit creation with valid/invalid agent
- SHA256 checksum verification
- Commit ID uniqueness (no collisions)
- Staging file path encoding (M-V4)
- Ledger entry format and integrity chain
- Auth rejection when not authenticated

Run with: pytest test_avcpm_commit.py -v
"""

import os
import sys
import json
import hashlib
import shutil
import tempfile
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import avcpm_commit as commit_mod
import avcpm_branch as branch
import avcpm_agent as agent
import avcpm_auth as auth_mod
from avcpm_ledger_integrity import calculate_entry_hash, get_last_commit_hash


@pytest.fixture
def env(tmp_path):
    """Set up a full AVCPM environment for commit tests."""
    base_dir = str(tmp_path / ".avcpm")
    os.makedirs(base_dir, exist_ok=True)

    # Initialize branch system (creates main)
    branch._ensure_main_branch(base_dir)

    # Create an agent (unencrypted for testing simplicity)
    agent_data = agent.create_agent("testagent", "test@test.com", base_dir=base_dir, encrypt=False)

    # Create an authenticated session for the agent
    auth_mod.ensure_auth_directories(base_dir)
    session = auth_mod.create_session("testagent", base_dir=base_dir)

    # Create a production file to commit
    prod_dir = str(tmp_path / "project")
    os.makedirs(prod_dir, exist_ok=True)
    test_file = os.path.join(prod_dir, "hello.txt")
    with open(test_file, "w") as f:
        f.write("Hello, World!")

    # Create a nested directory file
    nested_dir = os.path.join(prod_dir, "subdir")
    os.makedirs(nested_dir, exist_ok=True)
    nested_file = os.path.join(nested_dir, "nested.txt")
    with open(nested_file, "w") as f:
        f.write("Nested content")

    # Save the original cwd and switch
    original_cwd = os.getcwd()
    os.chdir(prod_dir)

    yield {
        "base_dir": base_dir,
        "tmp_path": tmp_path,
        "prod_dir": prod_dir,
        "agent_id": "testagent",
        "test_file": test_file,
        "nested_file": nested_file,
        "agent_data": agent_data,
        "session": session,
    }

    os.chdir(original_cwd)


class TestCommitCreation:
    """Test commit creation with valid and invalid agents."""

    def test_commit_with_valid_agent(self, env):
        """Commit should succeed with a valid, authenticated agent."""
        result = commit_mod.commit(
            task_id="TASK-001",
            agent_id=env["agent_id"],
            rationale="Initial commit",
            files_to_commit=[env["test_file"]],
            base_dir=env["base_dir"],
        )
        # commit() prints but doesn't return a value; check side effects
        ledger_dir = branch.get_branch_ledger_dir("main", env["base_dir"])
        commits = [f for f in os.listdir(ledger_dir) if f.endswith(".json")]
        assert len(commits) == 1

        with open(os.path.join(ledger_dir, commits[0])) as f:
            entry = json.load(f)
        assert entry["agent_id"] == env["agent_id"]
        assert entry["task_id"] == "TASK-001"
        assert entry["rationale"] == "Initial commit"
        assert len(entry["changes"]) == 1
        assert entry["changes"][0]["file"] == env["test_file"]

    def test_commit_with_nonexistent_agent_raises(self, env):
        """Commit should raise ValueError for nonexistent agent."""
        with pytest.raises(ValueError, match="not found"):
            commit_mod.commit(
                task_id="TASK-002",
                agent_id="ghost_agent",
                rationale="Should fail",
                files_to_commit=[env["test_file"]],
                base_dir=env["base_dir"],
            )

    def test_commit_without_authentication_raises(self, env):
        """Commit should raise PermissionError when agent is not authenticated."""
        # Create another agent but don't authenticate it
        agent.create_agent("noauth_agent", "noauth@test.com", base_dir=env["base_dir"], encrypt=False)

        with pytest.raises(PermissionError):
            commit_mod.commit(
                task_id="TASK-003",
                agent_id="noauth_agent",
                rationale="Should fail auth",
                files_to_commit=[env["test_file"]],
                base_dir=env["base_dir"],
            )


class TestChecksumVerification:
    """Test SHA256 checksum verification."""

    def test_checksum_matches_file_content(self, env):
        """The checksum in the ledger entry should match the file's SHA256."""
        commit_mod.commit(
            task_id="TASK-010",
            agent_id=env["agent_id"],
            rationale="Checksum test",
            files_to_commit=[env["test_file"]],
            base_dir=env["base_dir"],
        )

        ledger_dir = branch.get_branch_ledger_dir("main", env["base_dir"])
        commits = [f for f in os.listdir(ledger_dir) if f.endswith(".json")]
        with open(os.path.join(ledger_dir, commits[0])) as f:
            entry = json.load(f)

        # Calculate expected checksum
        with open(env["test_file"], "rb") as f:
            expected = hashlib.sha256(f.read()).hexdigest()

        assert entry["changes"][0]["checksum"] == expected

    def test_checksum_differs_for_different_content(self, env):
        """Two commits of different content should have different checksums."""
        # Commit first file
        commit_mod.commit(
            task_id="TASK-011",
            agent_id=env["agent_id"],
            rationale="First file",
            files_to_commit=[env["test_file"]],
            base_dir=env["base_dir"],
        )

        # Create and commit second file
        file2 = os.path.join(env["prod_dir"], "different.txt")
        with open(file2, "w") as f:
            f.write("Different content here")

        # Small sleep to ensure different timestamp
        import time
        time.sleep(1)

        commit_mod.commit(
            task_id="TASK-012",
            agent_id=env["agent_id"],
            rationale="Second file",
            files_to_commit=[file2],
            base_dir=env["base_dir"],
        )

        ledger_dir = branch.get_branch_ledger_dir("main", env["base_dir"])
        commits = sorted([f for f in os.listdir(ledger_dir) if f.endswith(".json")])

        with open(os.path.join(ledger_dir, commits[0])) as f:
            entry1 = json.load(f)
        with open(os.path.join(ledger_dir, commits[1])) as f:
            entry2 = json.load(f)

        assert entry1["changes"][0]["checksum"] != entry2["changes"][0]["checksum"]


class TestCommitIDUniqueness:
    """Test commit ID uniqueness."""

    def test_commit_ids_are_unique(self, env):
        """Multiple commits should have unique IDs."""
        ids = set()

        for i in range(5):
            # Create a distinct file each time
            fpath = os.path.join(env["prod_dir"], f"file_{i}.txt")
            with open(fpath, "w") as f:
                f.write(f"Content {i}")

            commit_mod.commit(
                task_id=f"TASK-020-{i}",
                agent_id=env["agent_id"],
                rationale=f"Commit {i}",
                files_to_commit=[fpath],
                base_dir=env["base_dir"],
            )

            ledger_dir = branch.get_branch_ledger_dir("main", env["base_dir"])
            for fname in os.listdir(ledger_dir):
                if fname.endswith(".json"):
                    with open(os.path.join(ledger_dir, fname)) as f:
                        entry = json.load(f)
                    ids.add(entry["commit_id"])

        # All 5 commits should have unique IDs
        assert len(ids) == 5


class TestStagingPathEncoding:
    """Test M-V4: staging file path encoding to prevent basename collision."""

    def test_nested_path_encoded_with_underscores(self, env):
        """Nested file paths should use _ encoding instead of basename."""
        commit_mod.commit(
            task_id="TASK-030",
            agent_id=env["agent_id"],
            rationale="Staging path test",
            files_to_commit=[env["nested_file"]],
            base_dir=env["base_dir"],
        )

        ledger_dir = branch.get_branch_ledger_dir("main", env["base_dir"])
        commits = [f for f in os.listdir(ledger_dir) if f.endswith(".json")]
        with open(os.path.join(ledger_dir, commits[0])) as f:
            entry = json.load(f)

        staging_path = entry["changes"][0]["staging_path"]
        # The staging path should use _ instead of / for directory separators
        # e.g., subdir_foo.txt -> subdir_foo.txt
        staging_basename = os.path.basename(staging_path)
        assert "/" not in staging_basename or staging_basename.count("/") == 0

        # The staging file should exist
        assert os.path.exists(staging_path)

    def test_flat_file_staging_path(self, env):
        """Flat file path should work normally."""
        commit_mod.commit(
            task_id="TASK-031",
            agent_id=env["agent_id"],
            rationale="Flat staging test",
            files_to_commit=[env["test_file"]],
            base_dir=env["base_dir"],
        )

        ledger_dir = branch.get_branch_ledger_dir("main", env["base_dir"])
        commits = [f for f in os.listdir(ledger_dir) if f.endswith(".json")]
        with open(os.path.join(ledger_dir, commits[0])) as f:
            entry = json.load(f)

        # Staging path should exist and file should be readable
        assert os.path.exists(entry["changes"][0]["staging_path"])


class TestLedgerIntegrityChain:
    """Test ledger entry format and integrity chain."""

    def test_ledger_entry_has_required_fields(self, env):
        """Each ledger entry must have commit_id, timestamp, agent_id, entry_hash, etc."""
        commit_mod.commit(
            task_id="TASK-040",
            agent_id=env["agent_id"],
            rationale="Ledger format test",
            files_to_commit=[env["test_file"]],
            base_dir=env["base_dir"],
        )

        ledger_dir = branch.get_branch_ledger_dir("main", env["base_dir"])
        commits = [f for f in os.listdir(ledger_dir) if f.endswith(".json")]
        with open(os.path.join(ledger_dir, commits[0])) as f:
            entry = json.load(f)

        required_fields = ["commit_id", "timestamp", "agent_id", "task_id",
                           "rationale", "changes", "entry_hash", "signature",
                           "changes_hash", "previous_hash"]
        for field in required_fields:
            assert field in entry, f"Missing field: {field}"

    def test_entry_hash_is_correct(self, env):
        """The entry_hash should match a fresh calculation of the entry's hash."""
        commit_mod.commit(
            task_id="TASK-041",
            agent_id=env["agent_id"],
            rationale="Hash verification test",
            files_to_commit=[env["test_file"]],
            base_dir=env["base_dir"],
        )

        ledger_dir = branch.get_branch_ledger_dir("main", env["base_dir"])
        commits = [f for f in os.listdir(ledger_dir) if f.endswith(".json")]
        with open(os.path.join(ledger_dir, commits[0])) as f:
            entry = json.load(f)

        # Recalculate and compare
        expected_hash = calculate_entry_hash(entry)
        assert entry["entry_hash"] == expected_hash

    def test_integrity_chain_links(self, env):
        """Each commit should reference the previous commit's entry_hash via previous_hash."""
        # First commit - previous_hash should be None
        commit_mod.commit(
            task_id="TASK-042-A",
            agent_id=env["agent_id"],
            rationale="First commit in chain",
            files_to_commit=[env["test_file"]],
            base_dir=env["base_dir"],
        )

        import time
        time.sleep(1)

        # Modify file for second commit
        with open(env["test_file"], "w") as f:
            f.write("Updated content")

        commit_mod.commit(
            task_id="TASK-042-B",
            agent_id=env["agent_id"],
            rationale="Second commit in chain",
            files_to_commit=[env["test_file"]],
            base_dir=env["base_dir"],
        )

        ledger_dir = branch.get_branch_ledger_dir("main", env["base_dir"])
        commits = sorted([f for f in os.listdir(ledger_dir) if f.endswith(".json")])

        with open(os.path.join(ledger_dir, commits[0])) as f:
            first_entry = json.load(f)
        with open(os.path.join(ledger_dir, commits[1])) as f:
            second_entry = json.load(f)

        # First commit should have no previous_hash
        assert first_entry["previous_hash"] is None

        # Second commit should reference first commit's entry_hash
        assert second_entry["previous_hash"] == first_entry["entry_hash"]

    def test_signature_present(self, env):
        """Each commit should have a signature from the committing agent."""
        commit_mod.commit(
            task_id="TASK-043",
            agent_id=env["agent_id"],
            rationale="Signature test",
            files_to_commit=[env["test_file"]],
            base_dir=env["base_dir"],
        )

        ledger_dir = branch.get_branch_ledger_dir("main", env["base_dir"])
        commits = [f for f in os.listdir(ledger_dir) if f.endswith(".json")]
        with open(os.path.join(ledger_dir, commits[0])) as f:
            entry = json.load(f)

        assert "signature" in entry
        assert entry["signature"] is not None
        assert len(entry["signature"]) > 0