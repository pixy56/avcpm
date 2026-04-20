import os
import sys
import shutil
import json
from datetime import datetime

BASE_DIR = ".avcpm/tasks"
COLUMNS = ["todo", "in-progress", "review", "done"]

def print_help():
    print("AVCPM Task Tooling")
    print("Usage:")
    print("  python avcpm_task.py create <id> <description> [assignee]")
    print("  python avcpm_task.py move <id> <new_status>")
    print("  python avcpm_task.py list")

def create_task(task_id, description, assignee="unassigned"):
    path = os.path.join(BASE_DIR, "todo", f"{task_id}.json")
    if os.path.exists(path):
        print(f"Error: Task {task_id} already exists.")
        sys.exit(1)
    
    task_data = {
        "id": task_id,
        "description": description,
        "assignee": assignee,
        "priority": "medium",
        "dependencies": [],
        "status_history": [
            {"status": "todo", "timestamp": datetime.now().isoformat()}
        ]
    }
    
    with open(path, "w") as f:
        json.dump(task_data, f, indent=4)
    print(f"Task {task_id} created in 'todo'.")

def move_task(task_id, new_status):
    if new_status not in COLUMNS:
        print(f"Error: Invalid status. Use {COLUMNS}")
        sys.exit(1)
    
    # Find where the task is currently
    current_path = None
    for col in COLUMNS:
        p = os.path.join(BASE_DIR, col, f"{task_id}.json")
        if os.path.exists(p):
            current_path = p
            break
    
    if not current_path:
        print(f"Error: Task {task_id} not found.")
        sys.exit(1)
    
    # Update status history
    with open(current_path, "r") as f:
        task_data = json.load(f)
    
    task_data["status_history"].append({
        "status": new_status,
        "timestamp": datetime.now().isoformat()
    })
    
    # Move file
    new_path = os.path.join(BASE_DIR, new_status, f"{task_id}.json")
    shutil.move(current_path, new_path)
    
    with open(new_path, "w") as f:
        json.dump(task_data, f, indent=4)
    print(f"Task {task_id} moved to {new_status}.")

def list_tasks():
    for col in COLUMNS:
        print(f"\n--- {col.upper()} ---")
        col_path = os.path.join(BASE_DIR, col)
        files = [f for f in os.listdir(col_path) if f.endswith(".json")]
        if not files:
            print(" (empty)")
        for f in files:
            with open(os.path.join(col_path, f), "r") as task_f:
                data = json.load(task_f)
                print(f"[{data['id']}] {data['description']} ({data['assignee']})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "create" and len(sys.argv) >= 4:
        assignee = sys.argv[4] if len(sys.argv) > 4 else "unassigned"
        create_task(sys.argv[2], sys.argv[3], assignee)
    elif cmd == "move" and len(sys.argv) == 4:
        move_task(sys.argv[2], sys.argv[3])
    elif cmd == "list":
        list_tasks()
    else:
        print_help()
