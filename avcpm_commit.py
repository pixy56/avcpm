import os
import sys
import json
import hashlib
from datetime import datetime
import shutil

from avcpm_agent import get_agent, sign_commit

DEFAULT_BASE_DIR = ".avcpm"

def get_ledger_dir(base_dir=DEFAULT_BASE_DIR):
    """Get the ledger directory path."""
    return os.path.join(base_dir, "ledger")

def get_staging_dir(base_dir=DEFAULT_BASE_DIR):
    """Get the staging directory path."""
    return os.path.join(base_dir, "staging")

def ensure_directories(base_dir=DEFAULT_BASE_DIR):
    """Ensure ledger and staging directories exist."""
    os.makedirs(get_ledger_dir(base_dir), exist_ok=True)
    os.makedirs(get_staging_dir(base_dir), exist_ok=True)

def calculate_checksum(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def commit(task_id, agent_id, rationale, files_to_commit, base_dir=DEFAULT_BASE_DIR):
    ensure_directories(base_dir)
    
    # Validate agent_id exists
    agent = get_agent(agent_id, base_dir)
    if agent is None:
        raise ValueError(f"Agent {agent_id} not found. Create agent first using avcpm_agent.create_agent()")
    
    staging_dir = get_staging_dir(base_dir)
    ledger_dir = get_ledger_dir(base_dir)

    commit_id = datetime.now().strftime("%Y%m%d%H%M%S")
    timestamp = datetime.now().isoformat()
    
    commit_meta = {
        "commit_id": commit_id,
        "timestamp": timestamp,
        "agent_id": agent_id,
        "task_id": task_id,
        "rationale": rationale,
        "changes": []
    }

    for filepath in files_to_commit:
        if not os.path.exists(filepath):
            print(f"Warning: File {filepath} not found. Skipping.")
            continue
        
        checksum = calculate_checksum(filepath)
        # Copy file to staging
        staging_path = os.path.join(staging_dir, os.path.basename(filepath))
        shutil.copy2(filepath, staging_path)
        
        commit_meta["changes"].append({
            "file": filepath,
            "checksum": checksum,
            "staging_path": staging_path
        })

    # Generate signature for the commit
    signature_data = sign_commit(commit_id, timestamp, commit_meta["changes"], agent_id, base_dir)
    commit_meta["signature"] = signature_data["signature"]
    commit_meta["changes_hash"] = signature_data["changes_hash"]
    
    # Write to ledger
    ledger_path = os.path.join(ledger_dir, f"{commit_id}.json")
    with open(ledger_path, "w") as f:
        json.dump(commit_meta, f, indent=4)
    
    print(f"Commit {commit_id} written to ledger. Files moved to staging.")

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python avcpm_commit.py <task_id> <agent_id> <rationale> <file1> [file2...]")
        sys.exit(1)
    
    task_id = sys.argv[1]
    agent_id = sys.argv[2]
    rationale = sys.argv[3]
    files = sys.argv[4:]
    
    commit(task_id, agent_id, rationale, files)
