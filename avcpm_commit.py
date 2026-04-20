import os
import sys
import json
import hashlib
from datetime import datetime
import shutil

LEDGER_DIR = ".avcpm/ledger"
STAGING_DIR = ".avcpm/staging" # As per DESIGN.md 3.2

def calculate_checksum(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def commit(task_id, agent_id, rationale, files_to_commit):
    # Ensure staging exists
    if not os.path.exists(STAGING_DIR):
        os.makedirs(STAGING_DIR)

    commit_id = datetime.now().strftime("%Y%m%d%H%M%S")
    commit_meta = {
        "commit_id": commit_id,
        "timestamp": datetime.now().isoformat(),
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
        staging_path = os.path.join(STAGING_DIR, os.path.basename(filepath))
        shutil.copy2(filepath, staging_path)
        
        commit_meta["changes"].append({
            "file": filepath,
            "checksum": checksum,
            "staging_path": staging_path
        })

    # Write to ledger
    ledger_path = os.path.join(LEDGER_DIR, f"{commit_id}.json")
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
