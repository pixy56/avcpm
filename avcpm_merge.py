import os
import sys
import shutil
import json

from avcpm_agent import verify_commit_signature

DEFAULT_BASE_DIR = ".avcpm"

def get_reviews_dir(base_dir=DEFAULT_BASE_DIR):
    """Get the reviews directory path."""
    return os.path.join(base_dir, "reviews")

def get_staging_dir(base_dir=DEFAULT_BASE_DIR):
    """Get the staging directory path."""
    return os.path.join(base_dir, "staging")

def get_ledger_dir(base_dir=DEFAULT_BASE_DIR):
    """Get the ledger directory path."""
    return os.path.join(base_dir, "ledger")

def merge(commit_id, base_dir=DEFAULT_BASE_DIR):
    reviews_dir = get_reviews_dir(base_dir)
    staging_dir = get_staging_dir(base_dir)
    ledger_dir = get_ledger_dir(base_dir)
    
    # 1. Validate Approval
    review_path = os.path.join(reviews_dir, f"{commit_id}.review")
    if not os.path.exists(review_path):
        print(f"Error: No review file found for commit {commit_id} at {review_path}")
        sys.exit(1)
    
    with open(review_path, "r") as f:
        content = f.read()
    
    if "APPROVED" not in content:
        print(f"Error: Commit {commit_id} is not APPROVED. Merge aborted.")
        sys.exit(1)
    
    # 2. Identify files in the commit
    ledger_path = os.path.join(ledger_dir, f"{commit_id}.json")
    if not os.path.exists(ledger_path):
        print(f"Error: Commit {commit_id} not found in ledger.")
        sys.exit(1)
    
    with open(ledger_path, "r") as f:
        commit_data = json.load(f)
    
    # 3. Verify commit signature before merging
    signature = commit_data.get("signature")
    agent_id = commit_data.get("agent_id")
    timestamp = commit_data.get("timestamp")
    changes = commit_data.get("changes", [])
    
    if not signature:
        print(f"Error: Commit {commit_id} has no signature. Merge aborted.")
        sys.exit(1)
    
    if not agent_id:
        print(f"Error: Commit {commit_id} has no agent_id. Merge aborted.")
        sys.exit(1)
    
    is_valid = verify_commit_signature(commit_id, timestamp, changes, agent_id, signature, base_dir)
    if not is_valid:
        print(f"Error: Commit {commit_id} has invalid signature. Merge aborted.")
        sys.exit(1)
    
    print(f"Signature verified for commit {commit_id} (agent: {agent_id})")
    
    # 4. Move files from staging to production (current directory)
    for change in commit_data["changes"]:
        staging_file = change["staging_path"]
        if os.path.exists(staging_file):
            dest_file = change["file"]
            # Simple copy/overwrite for Phase 1
            shutil.copy2(staging_file, dest_file)
            print(f"Merged: {dest_file}")
        else:
            print(f"Warning: Staging file {staging_file} missing.")

    print(f"Successfully merged commit {commit_id} into production.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python avcpm_merge.py <commit_id>")
        sys.exit(1)
    
    merge(sys.argv[1])
