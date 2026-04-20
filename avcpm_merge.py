import os
import sys
import shutil
import json

REVIEWS_DIR = ".avcpm/reviews"
STAGING_DIR = ".avcpm/staging"

def merge(commit_id):
    # 1. Validate Approval
    review_path = os.path.join(REVIEWS_DIR, f"{commit_id}.review")
    if not os.path.exists(review_path):
        print(f"Error: No review file found for commit {commit_id} at {review_path}")
        sys.exit(1)
    
    with open(review_path, "r") as f:
        content = f.read()
    
    if "APPROVED" not in content:
        print(f"Error: Commit {commit_id} is not APPROVED. Merge aborted.")
        sys.exit(1)
    
    # 2. Identify files in the commit
    ledger_path = os.path.join(".avcpm/ledger", f"{commit_id}.json")
    if not os.path.exists(ledger_path):
        print(f"Error: Commit {commit_id} not found in ledger.")
        sys.exit(1)
    
    with open(ledger_path, "r") as f:
        commit_data = json.load(f)
    
    # 3. Move files from staging to production (current directory)
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
