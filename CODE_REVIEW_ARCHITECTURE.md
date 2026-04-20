# AVCPM Architecture & Design Review

**Reviewer:** Senior Code Reviewer (Architecture & Design Patterns)  
**Date:** 2026-04-20  
**Files Reviewed:** avcpm_task.py, avcpm_commit.py, avcpm_merge.py, avcpm_branch.py, avcpm_agent.py, avcpm_diff.py, avcpm_conflict.py

---

## Executive Summary

AVCPM is a version control and project management system for AI agents. The codebase shows clear intent to build git-like functionality with task tracking. Overall, the code is functional but suffers from several architectural inconsistencies and design patterns that will create maintenance challenges as the codebase grows.

**Overall Grade: C+** — Functional but needs structural improvements before scaling.

---

## 1. Architecture Review

### 1.1 Module Organization & Separation of Concerns

| Module | Responsibility | Assessment |
|--------|---------------|------------|
| `avcpm_task.py` | Task management (Kanban-style) | ✅ Well-focused |
| `avcpm_branch.py` | Git-like branching | ✅ Well-focused |
| `avcpm_commit.py` | Commit creation & staging | ⚠️ Mixed concerns |
| `avcpm_merge.py` | Merge operations | ⚠️ Overlaps with conflict.py |
| `avcpm_agent.py` | Identity/cryptography | ✅ Well-focused |
| `avcpm_diff.py` | History & diff visualization | ✅ Well-focused |
| `avcpm_conflict.py` | Conflict detection & resolution | ✅ Well-focused |

**Issues:**
- **avcpm_commit.py** imports from `avcpm_lifecycle` (not in review list) — circular dependency risk
- **avcpm_merge.py** duplicates staging/ledger path logic that belongs in branch.py
- **avcpm_diff.py** has good type hints (Python 3.9+) but other modules don't — inconsistency

### 1.2 Consistency Across Modules

**Inconsistent Patterns Found:**

1. **Default Base Directory:**
   ```python
   # All modules define this, but inconsistently used
   DEFAULT_BASE_DIR = ".avcpm"  # task, commit, merge, conflict
   DEFAULT_BASE_DIR = ".avcpm"  # branch (with docstring)
   ```

2. **Directory Path Functions:**
   ```python
   # Pattern A (commit/merge): global vs branch-specific
   get_global_ledger_dir()  # legacy
   get_ledger_dir()         # branch-aware
   
   # Pattern B (branch): explicit branch methods
   get_branch_ledger_dir(branch_name)
   ```

3. **Error Handling:**
   ```python
   # Some raise exceptions
   raise ValueError(f"Branch '{name}' already exists")
   
   # Some print and exit
   print(f"Error: Task {task_id} not found.")
   sys.exit(1)
   
   # Some return None
   return None
   ```

4. **Import Organization:**
   - `avcpm_diff.py` uses `from typing import ...`
   - Other modules don't import typing at all

### 1.3 Data Flow Between Components

```
┌─────────────────────────────────────────────────────────────┐
│  CURRENT DATA FLOW (simplified)                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  task.py ─────┐                                              │
│               │                                              │
│  agent.py ────┼───> commit.py ────> merge.py               │
│               │       │               │                      │
│  branch.py ───┘       │               │                      │
│               │       ▼               ▼                      │
│               └──> conflict.py <─────┘                      │
│                      │                                       │
│               diff.py ◄──────┘                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Data Flow Issues:**
- **avcpm_commit.py** reads branch config directly instead of using branch.py's `get_current_branch()`
- Cross-module dependencies create tight coupling
- No clear "core" module — every module imports from others
- JSON file I/O scattered across all modules (no persistence layer)

### 1.4 Configuration Management (base_dir Patterns)

**Current Pattern (Repeated 50+ times):**
```python
def some_function(base_dir=DEFAULT_BASE_DIR):
    path = os.path.join(base_dir, "subdir")
    # ...
```

**Problems:**
1. `base_dir` is passed explicitly in every function call
2. No context manager or configuration object
3. No validation that base_dir is initialized
4. Race conditions possible if multiple `base_dir` values used simultaneously

**Recommended Pattern:**
```python
# Single configuration object
class AVCPMConfig:
    def __init__(self, base_dir: str = ".avcpm"):
        self.base_dir = Path(base_dir)
        self._validate()
    
    def tasks_dir(self) -> Path:
        return self.base_dir / "tasks"
```

---

## 2. Design Patterns Analysis

### 2.1 Patterns Used (Inconsistently)

| Pattern | Used In | Assessment |
|---------|---------|------------|
| **Module-level constants** | All | ✅ Good |
| **Function-based API** | All | ⚠️ No encapsulation |
| **CLI + Library mixed** | All | ❌ Needs separation |
| **Registry pattern** | agent.py | ✅ Good for agents |
| **File-based state** | All | ⚠️ No transactions |

### 2.2 Missing Patterns That Would Help

1. **Repository Pattern**: Wrap all file I/O
2. **Command Pattern**: CLI commands as objects
3. **Observer Pattern**: For lifecycle hooks (mentioned but not reviewed)
4. **Factory Pattern**: For creating tasks, commits, branches

### 2.3 Module API Intuitiveness

**Good Examples:**
```python
# branch.py - clear, predictable
create_branch(name, parent_branch="main", ...)
delete_branch(name, force=False, ...)
switch_branch(name)
get_current_branch()

# task.py - straightforward
create_task(task_id, description, ...)
move_task(task_id, new_status, ...)
```

**Poor Examples:**
```python
# commit.py - inconsistent parameter order
commit(task_id, agent_id, rationale, files_to_commit, branch_name=None, base_dir=DEFAULT_BASE_DIR, skip_validation=False)
# Why is base_dir in the middle? Why no task object?

# merge.py - side effects not clear
merge(commit_id, source_branch=None, target_branch=None, ...)
# Does this modify files? Create records? Both?
```

### 2.4 CLI vs Library Interface Separation

**Current State: MIXED (Problematic)**

Every module has `if __name__ == "__main__":` with CLI code mixed with library functions.

**Example of the problem (avcpm_task.py):**
```python
def create_task(task_id, description, ...):  # Library function
    # ... logic ...
    if os.path.exists(path):
        print(f"Error: Task {task_id} already exists.")  # ❌ Side effect!
        sys.exit(1)  # ❌ Should raise exception
```

**Recommendation:**
```
avcpm/
├── __init__.py          # Public API
├── core/                # Library code (no prints, no sys.exit)
│   ├── task.py
│   ├── branch.py
│   └── ...
└── cli/                 # CLI interface
    ├── __init__.py
    ├── commands.py
    └── main.py
```

---

## 3. Code Structure Analysis

### 3.1 Function Sizes & Responsibilities

**Function Size Distribution:**

| Module | Small (<20 lines) | Medium (20-50) | Large (>50) | Violations |
|--------|-------------------|----------------|-------------|------------|
| task.py | 15 | 8 | 4 | `create_task()` does validation + I/O + side effects |
| branch.py | 12 | 10 | 3 | `create_branch()` too long |
| commit.py | 3 | 2 | 1 | `commit()` is 70+ lines, 8 params |
| merge.py | 4 | 2 | 1 | `merge()` mixes validation + I/O + business logic |
| agent.py | 10 | 6 | 2 | Good separation overall |
| diff.py | 8 | 8 | 3 | `_print_commit_details()` should be formatter |
| conflict.py | 8 | 7 | 3 | `merge_three_way()` is complex but justified |

**Single Responsibility Principle Violations:**

1. **`commit()` in avcpm_commit.py** does:
   - Directory initialization
   - Agent validation
   - Lifecycle validation
   - Checksum calculation
   - File copying
   - JSON serialization
   - Signature generation
   - Print output

2. **`merge()` in avcpm_merge.py** does:
   - Branch resolution
   - Conflict detection
   - Review validation
   - Signature verification
   - File copying
   - Branch status updates
   - Lifecycle hooks

### 3.2 Class Usage (Or Lack Thereof)

**Current State: Zero classes in the entire codebase**

This is a **deliberate choice** but may not be the right one. Functional programming is fine, but the code actually uses mutable state everywhere (files, JSON mutations).

**Where Classes Would Help:**

1. **Task Entity:**
   ```python
   @dataclass
   class Task:
       id: str
       description: str
       status: TaskStatus
       dependencies: List[str]
       
       def move_to(self, new_status: TaskStatus) -> None: ...
       def is_blocked(self) -> bool: ...
   ```

2. **Commit Entity:**
   ```python
   @dataclass
   class Commit:
       id: str
       agent_id: str
       task_id: str
       changes: List[Change]
       signature: bytes
       
       def verify(self, agent_registry) -> bool: ...
   ```

3. **Repository Objects:**
   ```python
   class TaskRepository:
       def __init__(self, base_dir: Path): ...
       def get(self, task_id: str) -> Optional[Task]: ...
       def save(self, task: Task) -> None: ...
   ```

**Counter-argument:** The functional approach works for simple cases and avoids OOP complexity. However, the code already has implicit objects (dicts with known keys) — using actual classes would add type safety.

### 3.3 Error Handling Patterns

**Inconsistent Error Handling:**

```python
# Pattern 1: Print + sys.exit (CLI-style, in library code!)
print(f"Error: Task {task_id} not found.")
sys.exit(1)

# Pattern 2: Return None
return None

# Pattern 3: Raise exception
raise ValueError(f"Branch '{name}' already exists")

# Pattern 4: Return success tuple
return True  # or False

# Pattern 5: Return result dict
return {"success": True, "has_conflict": False}
```

**Best Practice Recommendations:**

Library code should:
1. Raise exceptions for error conditions
2. Return values for success
3. Never call `sys.exit()` or `print()`

CLI code should:
1. Catch exceptions
2. Print user-friendly messages
3. Call `sys.exit()` with appropriate codes

---

## 4. Specific Code Issues

### 4.1 Circular Import Risk

**avcpm_commit.py:**
```python
from avcpm_lifecycle import (
    on_commit,
    validate_commit_allowed,
    init_lifecycle_config
)
```

If `avcpm_lifecycle.py` imports from commit.py, this will break.

### 4.2 Legacy Code Still Present

**avcpm_commit.py:**
```python
def get_global_ledger_dir(base_dir=DEFAULT_BASE_DIR):
    """Get the global ledger directory path (legacy)."""
    return os.path.join(base_dir, "ledger")
```

Comment says "legacy" but code is still used. Either migrate fully or remove.

### 4.3 Unused Imports

**avcpm_merge.py:**
```python
from avcpm_conflict import (
    detect_conflicts,
    resolve_conflict,
    get_conflicts,
    CONFLICT_STATUS_OPEN,
    auto_merge_possible
)
```
`resolve_conflict`, `get_conflicts`, `CONFLICT_STATUS_OPEN` are imported but not used.

### 4.4 Hardcoded Values

**avcpm_task.py:**
```python
COLUMNS = ["todo", "in-progress", "review", "done"]
```
Should be configurable. Also inconsistent naming (why "COLUMNS" for Kanban statuses?).

### 4.5 Type Safety Issues

**avcpm_task.py:**
```python
def create_task(task_id, description, assignee="unassigned", depends_on=None, base_dir=DEFAULT_BASE_DIR):
    # depends_on can be str or list, handled inconsistently
    if isinstance(depends_on, str):
        deps_list = [d.strip() for d in depends_on.split(",") if d.strip()]
    elif isinstance(depends_on, list):
        deps_list = depends_on
```

This is a code smell. Should have separate functions or normalize input at CLI layer.

---

## 5. Recommendations

### 5.1 High Priority (Refactor Soon)

1. **Separate CLI from Library Code**
   ```
   # Move all CLI code to cli/ subdirectory
   # Library functions should raise exceptions, not print/exit
   ```

2. **Create a Configuration/Persistence Layer**
   ```python
   class AVCPMContext:
       def __init__(self, base_dir: Path):
           self.base_dir = base_dir
           self.tasks = TaskRepository(self)
           self.branches = BranchRepository(self)
           # ...
   ```

3. **Standardize Error Handling**
   - Define custom exceptions: `AVCPMError`, `TaskNotFoundError`, `BranchExistsError`
   - Library code raises exceptions
   - CLI code catches and formats

### 5.2 Medium Priority (Improve Quality)

4. **Add Type Hints to All Public Functions**
   ```python
   def create_task(
       task_id: str,
       description: str,
       assignee: str = "unassigned",
       depends_on: Optional[List[str]] = None,
       base_dir: str = DEFAULT_BASE_DIR
   ) -> Task:
   ```

5. **Extract Data Classes**
   ```python
   @dataclass
   class Task:
       id: str
       description: str
       status: TaskStatus
       assignee: str
       depends_on: List[str]
       priority: Priority
       status_history: List[StatusChange]
   ```

6. **Add Repository Pattern**
   ```python
   class TaskRepository:
       def get(self, task_id: str) -> Optional[Task]: ...
       def list_by_status(self, status: TaskStatus) -> List[Task]: ...
       def save(self, task: Task) -> None: ...
       def move(self, task: Task, new_status: TaskStatus) -> None: ...
   ```

### 5.3 Low Priority (Nice to Have)

7. **Add Comprehensive Tests** (None visible in reviewed files)

8. **Consider Click or Typer for CLI** instead of manual sys.argv parsing

9. **Add Logging** instead of print statements for debugging

10. **Add Transaction Support** for multi-file operations
    ```python
    with context.transaction():
        task_repo.move(task, "done")
        commit_repo.create(commit)
        # Both succeed or both rollback
    ```

---

## 6. Refactoring Roadmap

### Phase 1: Separation of Concerns (Week 1-2)
1. Create `cli/` directory
2. Move all `if __name__ == "__main__"` code there
3. Change library functions to raise exceptions
4. Add basic integration tests

### Phase 2: Data Layer (Week 3-4)
1. Create `models.py` with dataclasses
2. Create `repositories.py` with persistence logic
3. Migrate functions to use new classes
4. Keep backward compatibility layer

### Phase 3: Configuration (Week 5)
1. Create `config.py` with Context class
2. Remove `base_dir` parameter from all functions
3. Use dependency injection or thread-local context

### Phase 4: Polish (Week 6)
1. Add type hints everywhere
2. Add docstrings
3. Clean up imports
4. Remove legacy code

---

## 7. Conclusion

AVCPM has solid functionality but needs architectural cleanup. The main issues are:

1. **Mixed CLI/Library code** — Makes testing and reuse difficult
2. **Inconsistent error handling** — Creates confusion and bugs
3. **No encapsulation** — Everything is global functions with file I/O
4. **Scattered data logic** — JSON files accessed directly everywhere

**Positive Aspects:**
- Clear module responsibilities
- Good use of docstrings in some files
- Thoughtful functionality (dependency tracking, conflict detection)
- Type hints in newer files (diff.py)

**The codebase is functional but will become harder to maintain as features grow. A refactoring investment of 4-6 weeks would pay dividends in maintainability.**

---

## Appendix: File-by-File Quick Reference

| File | Lines | Functions | Classes | Key Issues |
|------|-------|-----------|---------|------------|
| avcpm_task.py | ~450 | 30+ | 0 | Mixed CLI/lib, inconsistent error handling |
| avcpm_commit.py | ~150 | 8 | 0 | 8-param function, lifecycle import risk |
| avcpm_merge.py | ~200 | 8 | 0 | Unused imports, side effects |
| avcpm_branch.py | ~450 | 25+ | 0 | Good overall, needs dataclasses |
| avcpm_agent.py | ~400 | 20+ | 0 | Well-structured crypto code |
| avcpm_diff.py | ~500 | 25+ | 0 | Good type hints, complex formatting functions |
| avcpm_conflict.py | ~600 | 25+ | 0 | Good algorithm implementation |

**Total:** ~2,750 lines of code across 7 modules
