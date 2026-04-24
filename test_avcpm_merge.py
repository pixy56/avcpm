"""
Tests for AVCPM Merge Module (M-T2)

Covers:
- Merge copies files to production
- Merge requires approval file
- Merge handles missing approval
- Cross-branch merge

Run with: pytest test_avcpm_merge.py -v
"""

import os
import sys
import json
import shutil
import tempfile
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import avcpm_commit as commit_mod
import avcpm_merge as merge_mod
import avcpm_branch as branch
import avcpm_agent as agent
import avcpm_auth as auth_mod


@pytest.fixture
def env(tmp_path):
    """Set up a full AVCPM environment for merge tests."""
    base_dir = str(tmp_path / ".avcpm")
    os.makedirs(base_dir, exist_ok=True)

    # Initialize branch system
    branch._ensure_main_branch(base_dir)

    # Create an agent (unencrypted for test simplicity)
    agent_data = agent.create_agent("mergeagent", "merge@test.com", base_dir=base_dir, encrypt=False)

    # Authenticate the agent
    auth_mod.ensure_auth_directories(base_dir)
    session = auth_mod.create_session("mergeagent", base_dir=base_dir)

    # Initialize lifecycle config (required by commit)
    from avcpm_lifecycle import init_lifecycle_config
    init_lifecycle_config(base_dir)

    # Create production directory
    prod_dir = str(tmp_path / "project")
    os.makedirs(prod_dir, exist_ok=True)

    # Save original cwd and switch to prod dir
    original_cwd = os.getcwd()
    os.chdir(prod_dir)

    yield {
        "base_dir": base_dir,
        "tmp_path": tmp_path,
        "prod_dir": prod_dir,
        "agent_id": "mergeagent",
        "agent_data": agent_data,
        "session": session,
    }

    os.chdir(original_cwd)


def _create_commit(env, task_id, files_dict, rationale="Test commit", branch_name=None):
    """Helper: create files and commit them."""
    file_paths = []
    for name, content in files_dict.items():
        fpath = os.path.join(env["prod_dir"], name)
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, "w") as f:
            f.write(content)
        file_paths.append(fpath)

    commit_mod.commit(
        task_id=task_id,
        agent_id=env["agent_id"],
        rationale=rationale,
        files_to_commit=file_paths,
        branch_name=branch_name,
        base_dir=env["base_dir"],
    )

    # Get commit ID from ledger
    br = branch_name or "main"
    ledger_dir = branch.get_branch_ledger_dir(br, env["base_dir"])
    commits = sorted([f for f in os.listdir(ledger_dir) if f.endswith(".json")])
    with open(os.path.join(ledger_dir, commits[-1])) as f:
        return json.load(f)["commit_id"]


def _approve_commit(env, commit_id):
    """Helper: create an approval review file for a commit."""
    reviews_dir = os.path.join(env["base_dir"], "reviews")
    os.makedirs(reviews_dir, exist_ok=True)
    review_path = os.path.join(reviews_dir, f"{commit_id}.review")
    with open(review_path, "w") as f:
        f.write(f"Commit {commit_id}\nStatus: APPROVED\nReviewer: mergeagent\n")
    return review_path


class TestMergeToProduction:
    """Test that merge copies files from staging to production."""

    def test_merge_copies_staged_file_to_production(self, env):
        """Merged files should appear in the production directory."""
        # Create and commit a file
        commit_id = _create_commit(env, "TASK-100", {"output.txt": "Production content"})
        _approve_commit(env, commit_id)

        # Verify file is in staging
        ledger_dir = branch.get_branch_ledger_dir("main", env["base_dir"])
        with open(os.path.join(ledger_dir, f"{commit_id}.json")) as f:
            entry = json.load(f)
        staging_path = entry["changes"][0]["staging_path"]
        assert os.path.exists(staging_path)

        # Remove the production file to prove merge restores it
        prod_file = os.path.join(env["prod_dir"], "output.txt")
        if os.path.exists(prod_file):
            os.remove(prod_file)
        assert not os.path.exists(prod_file)

        # Merge
        merge_mod.merge(commit_id, base_dir=env["base_dir"])

        # The production file should now exist
        assert os.path.exists(prod_file)
        with open(prod_file) as f:
            assert f.read() == "Production content"

    def test_merge_overwrites_existing_production_file(self, env):
        """Merge should overwrite the production file with the staged version."""
        # Create a file in production
        fpath = os.path.join(env["prod_dir"], "config.yaml")
        with open(fpath, "w") as f:
            f.write("old: value")

        commit_id = _create_commit(env, "TASK-101", {"config.yaml": "new: value"})
        _approve_commit(env, commit_id)

        merge_mod.merge(commit_id, base_dir=env["base_dir"])

        with open(fpath) as f:
            assert f.read() == "new: value"

    def test_merge_multiple_files(self, env):
        """Merge should copy all files in the commit."""
        commit_id = _create_commit(env, "TASK-102", {
            "file_a.txt": "Content A",
            "file_b.txt": "Content B",
        })
        _approve_commit(env, commit_id)

        merge_mod.merge(commit_id, base_dir=env["base_dir"])

        for name, content in [("file_a.txt", "Content A"), ("file_b.txt", "Content B")]:
            fpath = os.path.join(env["prod_dir"], name)
            assert os.path.exists(fpath), f"{name} should exist after merge"
            with open(fpath) as f:
                assert f.read() == content


class TestMergeRequiresApproval:
    """Test that merge requires an approval file."""

    def test_merge_without_approval_raises(self, env):
        """Merge should raise ValueError when no review file exists."""
        commit_id = _create_commit(env, "TASK-200", {"data.txt": "data"})

        with pytest.raises(ValueError, match="No review file found"):
            merge_mod.merge(commit_id, base_dir=env["base_dir"])

    def test_merge_with_approval_succeeds(self, env):
        """Merge should succeed when an approved review exists."""
        commit_id = _create_commit(env, "TASK-201", {"data.txt": "data"})
        _approve_commit(env, commit_id)

        # Should not raise
        merge_mod.merge(commit_id, base_dir=env["base_dir"])

    def test_merge_with_non_approved_review_raises(self, env):
        """Merge should raise ValueError if review exists but is not APPROVED."""
        commit_id = _create_commit(env, "TASK-202", {"data.txt": "data"})

        # Create a review that's NOT approved
        reviews_dir = os.path.join(env["base_dir"], "reviews")
        os.makedirs(reviews_dir, exist_ok=True)
        review_path = os.path.join(reviews_dir, f"{commit_id}.review")
        with open(review_path, "w") as f:
            f.write(f"Commit {commit_id}\nStatus: REJECTED\nReviewer: mergeagent\n")

        with pytest.raises(ValueError, match="not APPROVED"):
            merge_mod.merge(commit_id, base_dir=env["base_dir"])


class TestMergeMissingApproval:
    """Test handling of missing or invalid approval scenarios."""

    def test_merge_wrong_commit_id_raises(self, env):
        """Merge with a non-existent commit ID should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            merge_mod.merge("nonexistent-commit-id", base_dir=env["base_dir"])

    def test_merge_commit_without_signature_raises(self, env):
        """Merge should reject a commit with no signature."""
        commit_id = _create_commit(env, "TASK-203", {"data.txt": "data"})

        # Tamper with ledger entry: remove signature
        ledger_dir = branch.get_branch_ledger_dir("main", env["base_dir"])
        ledger_path = os.path.join(ledger_dir, f"{commit_id}.json")
        with open(ledger_path) as f:
            entry = json.load(f)
        del entry["signature"]
        with open(ledger_path, "w") as f:
            json.dump(entry, f)

        _approve_commit(env, commit_id)

        with pytest.raises(ValueError, match="no signature"):
            merge_mod.merge(commit_id, base_dir=env["base_dir"])


class TestCrossBranchMerge:
    """Test merging across branches."""

    def test_cross_branch_merge(self, env):
        """Merge from a feature branch into main should work."""
        # Create feature branch
        branch.create_branch("feature-x", parent_branch="main", base_dir=env["base_dir"])
        branch.switch_branch("feature-x", env["base_dir"])

        # Commit on feature branch
        commit_id = _create_commit(env, "TASK-300", {"feature.txt": "Feature work"}, branch_name="feature-x")
        _approve_commit(env, commit_id)

        # Switch back to main
        branch.switch_branch("main", env["base_dir"])

        # Merge feature branch commit into main
        merge_mod.merge(commit_id, source_branch="feature-x", target_branch="main", base_dir=env["base_dir"])

        # Verify file exists in production
        prod_file = os.path.join(env["prod_dir"], "feature.txt")
        assert os.path.exists(prod_file)
        with open(prod_file) as f:
            assert f.read() == "Feature work"

        # Verify feature branch is marked as merged
        feature_meta = branch.get_branch("feature-x", env["base_dir"])
        assert feature_meta["status"] == branch.BRANCH_STATUS_MERGED

    def test_cross_branch_merge_conflict_detection(self, env):
        """Cross-branch merge should detect conflicts when both branches modify same file."""
        # Create a file on main first
        with open(os.path.join(env["prod_dir"], "shared.txt"), "w") as f:
            f.write("Main content")

        # Commit on main
        main_commit = _create_commit(env, "TASK-310", {"shared.txt": "Main content"})

        # Create feature branch
        branch.create_branch("feature-y", parent_branch="main", base_dir=env["base_dir"])
        branch.switch_branch("feature-y", env["base_dir"])

        # Modify same file on feature branch
        with open(os.path.join(env["prod_dir"], "shared.txt"), "w") as f:
            f.write("Feature content")

        feature_commit = _create_commit(env, "TASK-311", {"shared.txt": "Feature content"}, branch_name="feature-y")
        _approve_commit(env, feature_commit)

        # Switch to main
        branch.switch_branch("main", env["base_dir"])

        # This should raise due to conflict
        with pytest.raises(ValueError, match="conflict"):
            merge_mod.merge(feature_commit, source_branch="feature-y", target_branch="main", base_dir=env["base_dir"])