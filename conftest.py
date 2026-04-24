"""
Shared pytest fixtures for AVCPM tests.

Provides reusable fixtures for creating isolated test environments
with mock agents, sessions, branches, and commits.
"""

import os
import sys
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

import pytest

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the modules under test
from avcpm_agent import create_agent, get_agent
from avcpm_branch import create_branch, get_branch, switch_branch
from avcpm_commit import commit as commit_files
from avcpm_auth import create_session, get_session_token_from_env
from avcpm_lifecycle import init_lifecycle_config
from avcpm_task import create_task, COLUMNS
from avcpm_audit import get_audit_log_path


@pytest.fixture
def tmp_avcpm_dir(tmp_path):
    """
    Create an isolated .avcpm directory inside tmp_path.
    Automatically cleaned up after test.
    
    Returns:
        str: Path to the created .avcpm directory
    """
    avcpm_dir = tmp_path / ".avcpm"
    avcpm_dir.mkdir(parents=True, exist_ok=True)
    
    # Create default directory structure
    (avcpm_dir / "agents").mkdir(exist_ok=True)
    (avcpm_dir / "branches" / "main" / "staging").mkdir(parents=True, exist_ok=True)
    (avcpm_dir / "branches" / "main" / "ledger").mkdir(parents=True, exist_ok=True)
    (avcpm_dir / "tasks" / "todo").mkdir(parents=True, exist_ok=True)
    (avcpm_dir / "tasks" / "in-progress").mkdir(parents=True, exist_ok=True)
    (avcpm_dir / "tasks" / "review").mkdir(parents=True, exist_ok=True)
    (avcpm_dir / "tasks" / "done").mkdir(parents=True, exist_ok=True)
    (avcpm_dir / "reviews").mkdir(exist_ok=True)
    
    yield str(avcpm_dir)
    
    # Cleanup happens automatically via tmp_path


@pytest.fixture
def mock_agent(tmp_avcpm_dir):
    """
    Create a test agent with keys.
    
    Returns:
        dict: Agent metadata with agent_id
    """
    agent = create_agent(
        name="Test Agent",
        email="test@example.com",
        base_dir=tmp_avcpm_dir,
        encrypt=False  # No encryption for tests
    )
    return agent


@pytest.fixture
def mock_session(mock_agent, tmp_avcpm_dir):
    """
    Create an authenticated session for the mock agent.
    
    Returns:
        dict: Session info with agent_id and session_token
    """
    # Create session
    session = create_session(mock_agent["agent_id"], base_dir=tmp_avcpm_dir)
    
    # Set environment for authentication
    os.environ["AVCPM_AGENT_ID"] = mock_agent["agent_id"]
    os.environ["AVCPM_SESSION_TOKEN"] = session["session_token"]
    
    return session


@pytest.fixture
def mock_branch(tmp_avcpm_dir):
    """
    Create a test branch (main branch already exists).
    
    Returns:
        dict: Branch metadata
    """
    # Switch to main branch (already exists)
    switch_branch("main", base_dir=tmp_avcpm_dir)
    
    # Create a test branch
    branch = create_branch(
        name="test-branch",
        parent_branch="main",
        base_dir=tmp_avcpm_dir
    )
    
    return branch


@pytest.fixture
def mock_commit(mock_branch, mock_agent, tmp_avcpm_dir):
    """
    Create a test commit with a file.
    
    Returns:
        tuple: (commit_id, test_file_path)
    """
    # Create a test file
    test_dir = Path(tmp_avcpm_dir).parent
    test_file = test_dir / "test_file.txt"
    test_file.write_text("Test content")
    
    # Create task first
    task_id = "TASK-TEST-001"
    create_task(task_id, "Test task", base_dir=tmp_avcpm_dir)
    
    # Create commit
    commit_id = commit_files(
        task_id=task_id,
        agent_id=mock_agent["agent_id"],
        rationale="Test commit",
        files_to_commit=[str(test_file)],
        branch_name="main",
        base_dir=tmp_avcpm_dir,
        skip_validation=True  # Skip for testing
    )
    
    return commit_id


@pytest.fixture
def test_file(tmp_avcpm_dir):
    """
    Create a temporary test file.
    
    Returns:
        Path: Path to the test file
    """
    test_dir = Path(tmp_avcpm_dir).parent
    test_file = test_dir / "test_file.txt"
    test_file.write_text("Test content")
    return test_file


# ----- Audit-specific fixtures -----

@pytest.fixture
def audit_log_path(tmp_avcpm_dir):
    """
    Provide path to audit log and ensure directory exists.
    
    Returns:
        str: Full path to audit.log
    """
    log_path = get_audit_log_path(tmp_avcpm_dir)
    return log_path


# ----- Task-related fixtures -----

@pytest.fixture
def task_dirs(tmp_avcpm_dir):
    """
    Ensure all task column directories exist.
    
    Returns:
        dict: Paths to each column directory
    """
    dirs = {}
    for col in COLUMNS:
        path = os.path.join(tmp_avcpm_dir, "tasks", col)
        os.makedirs(path, exist_ok=True)
        dirs[col] = path
    return dirs


@pytest.fixture
def sample_task(mock_agent, tmp_avcpm_dir, task_dirs):
    """
    Create a sample task for testing.
    
    Returns:
        dict: Task ID and task data
    """
    task_id = "TASK-SAMPLE-001"
    create_task(
        task_id,
        "Sample task description",
        assignee=mock_agent["agent_id"],
        base_dir=tmp_avcpm_dir
    )
    return task_id