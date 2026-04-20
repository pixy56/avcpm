# AVCPM Security Review

**Review Date:** 2026-04-20  
**Scope:** All AVCPM Python modules  
**Reviewer:** Security-Focused Code Reviewer  
**Risk Level:** MEDIUM - Several issues require attention

---

## Executive Summary

AVCPM implements a git-like version control system with RSA-based agent identity, commit signing, and branching. The codebase shows awareness of security concepts but has several vulnerabilities ranging from low to high severity that should be addressed.

### Risk Overview
| Category | Risk Level | Notes |
|----------|------------|-------|
| Cryptography | MEDIUM | RSA-2048 with proper padding, but key storage has issues |
| Input Validation | HIGH | Multiple injection risks, insufficient sanitization |
| Access Control | HIGH | Agent impersonation possible, missing authentication |
| Data Integrity | MEDIUM | TOCTOU issues, missing verification in some paths |
| Race Conditions | MEDIUM | File operations lack atomicity |

---

## 1. Cryptography Analysis

### 1.1 RSA Key Generation (avcpm_agent.py)

**Finding: GOOD** - RSA 2048-bit key generation uses proper parameters.
```python
private_key = rsa.generate_private_key(
    public_exponent=65537,  # Standard F4 exponent
    key_size=2048           # Adequate for current security
)
```

**Finding: MEDIUM** - Private key serialization uses PKCS#8 without password encryption:
```python
def _serialize_private_key(private_key):
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()  # UNENCRYPTED
    )
```

**Risk:** Private keys are stored unencrypted on disk. Physical access or backup compromise exposes keys.

**Recommendation:** 
- Implement optional password-based encryption for private keys
- Document the security trade-off
- Consider using agent environment variables for key material

### 1.2 Signature Scheme (avcpm_agent.py)

**Finding: GOOD** - Uses RSA-PSS with SHA-256:
```python
signature = private_key.sign(
    data,
    padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH
    ),
    hashes.SHA256()
)
```

This follows modern best practices (PSS padding > PKCS#1 v1.5).

### 1.3 Key Storage Permissions (avcpm_agent.py)

**Finding: MEDIUM** - Permissions are set but not verified:
```python
os.chmod(private_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
```

**Issues:**
1. No verification that permissions were actually applied
2. `public.pem` has no explicit permissions (default 644, which is fine)
3. No check for umask interference
4. Windows systems ignore Unix permissions - no Windows ACL handling

**Recommendation:**
```python
def _set_secure_permissions(filepath):
    """Set restrictive permissions, cross-platform."""
    os.chmod(filepath, stat.S_IRUSR | stat.S_IWUSR)
    # Verify permissions were set
    actual = stat.S_IMODE(os.stat(filepath).st_mode)
    if actual != 0o600:
        raise PermissionError(f"Could not set secure permissions on {filepath}")
```

### 1.4 Commit Signing Payload

**Finding: LOW** - Simple concatenation for payload:
```python
payload = f"{commit_id}:{timestamp}:{changes_hash}"
```

**Risk:** Potential ambiguity if `commit_id` or `timestamp` contain colons. Low risk in practice given timestamp format.

**Recommendation:** Use structured serialization (JSON with canonical ordering) or explicit length prefixes.

---

## 2. Input Validation

### 2.1 File Path Traversal

**Finding: HIGH** - Multiple path traversal vulnerabilities:

**avcpm_cli.py** - File arguments passed directly to commit:
```python
commit(args.task_id, args.agent_id, args.rationale, args.files, None, base_dir, skip_validation)
# args.files can contain: ../../../etc/passwd
```

**avcpm_commit.py** - No path sanitization:
```python
for filepath in files_to_commit:
    if not os.path.exists(filepath):
        print(f"Warning: File {filepath} not found. Skipping.")
        continue
    # filepath could be absolute or traverse outside repo
```

**avcpm_wip.py** - Claims on arbitrary paths:
```python
def _normalize_path(filepath: str, base_dir: str = DEFAULT_BASE_DIR) -> str:
    abs_path = os.path.abspath(os.path.join(base_dir, filepath))
    base_abs = os.path.abspath(base_dir)
    try:
        rel_path = os.path.relpath(abs_path, base_abs)
        return rel_path
    except ValueError:
        return filepath  # Falls back to potentially absolute path!
```

**Exploit Example:**
```bash
python avcpm_cli.py commit TASK-001 agent-1 "test" ../../../etc/shadow
```

**Recommendation:**
```python
def sanitize_path(filepath: str, base_dir: str) -> str:
    """Sanitize and validate file path."""
    # Resolve to absolute path
    abs_path = os.path.abspath(os.path.join(base_dir, filepath))
    base_abs = os.path.abspath(base_dir)
    
    # Verify path is within base directory
    try:
        rel_path = os.path.relpath(abs_path, base_abs)
        if rel_path.startswith('..'):
            raise ValueError(f"Path traversal detected: {filepath}")
        return rel_path
    except ValueError:
        raise ValueError(f"Invalid path: {filepath}")
```

### 2.2 Branch Name Validation

**Finding: MEDIUM** - Branch name validation is incomplete:

**avcpm_branch.py:**
```python
if "/" in name or "\\" in name or name.startswith("."):
    raise ValueError(f"Invalid branch name: {name}")

if name in [".", ".."]:
    raise ValueError(f"Reserved branch name: {name}")
```

**Missing checks:**
- Control characters (`\x00-\x1f`)
- Reserved Windows names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
- Names starting with `-` (could be interpreted as CLI flags)
- Names over 255 characters (filesystem limits)
- Unicode normalization attacks

**Recommendation:**
```python
def validate_branch_name(name: str) -> None:
    """Validate branch name against security constraints."""
    import re
    
    if not name or len(name) > 255:
        raise ValueError("Branch name must be 1-255 characters")
    
    if re.search(r'[\x00-\x1f\x7f/\\<>:"|?*]', name):
        raise ValueError("Branch name contains invalid characters")
    
    if name.startswith('.') or name.startswith('-'):
        raise ValueError("Branch name cannot start with '.' or '-'")
    
    reserved = {'con', 'prn', 'aux', 'nul'} | {f'com{i}' for i in range(1,10)} | {f'lpt{i}' for i in range(1,10)}
    if name.lower() in reserved:
        raise ValueError(f"Branch name '{name}' is reserved")
```

### 2.3 JSON Parsing Safety

**Finding: LOW** - Multiple modules parse JSON without size limits:

```python
# avcpm_branch.py, avcpm_task.py, etc.
with open(metadata_path, "r") as f:
    return json.load(f)  # Could exhaust memory with large files
```

**Risk:** Malformed or malicious JSON files could cause DoS.

**Recommendation:** Implement size limits:
```python
import io

MAX_JSON_SIZE = 10 * 1024 * 1024  # 10MB

def safe_json_load(filepath: str) -> dict:
    """Load JSON with size limit."""
    size = os.path.getsize(filepath)
    if size > MAX_JSON_SIZE:
        raise ValueError(f"JSON file too large: {size} bytes")
    with open(filepath, 'r') as f:
        return json.load(f)
```

### 2.4 Command Injection via CLI

**Finding: MEDIUM** - Some CLI arguments may be passed to shell operations:

**avcpm_rollback.py** - Files restored with shutil:
```python
dest_file = change["file"]  # Could contain shell metacharacters
shutil.copy2(staging_file, dest_file)
```

**Note:** `shutil.copy2` is safe from shell injection, but other operations may not be.

---

## 3. Access Control

### 3.1 Agent Impersonation

**Finding: HIGH** - No mechanism prevents agent impersonation:

**avcpm_commit.py:**
```python
def commit(task_id, agent_id, rationale, files_to_commit, ...):
    agent = get_agent(agent_id, base_dir)
    if agent is None:
        raise ValueError(f"Agent {agent_id} not found.")
    # Anyone can claim any agent_id if they know it!
```

**Issue:** The `agent_id` is passed as a parameter with no authentication. Any process can use any agent's identity if they know the agent_id.

**Exploit:**
```python
# Attacker uses another agent's identity
commit("TASK-001", "victim-agent", "malicious change", ["backdoor.py"])
```

**Recommendation:** Implement agent authentication:
```python
def authenticate_agent(agent_id: str, private_key_pem: bytes, base_dir: str) -> bool:
    """Verify agent has possession of private key."""
    # Load expected public key
    public_key_pem = get_public_key(agent_id, base_dir)
    if not public_key_pem:
        return False
    
    # Verify private key matches by signing a challenge
    challenge = os.urandom(32)
    # ... crypto verification ...
```

### 3.2 WIP Claim Bypass

**Finding: MEDIUM** - Claims can be released by anyone:

**avcpm_wip.py:**
```python
def release_file(filepath: str, agent_id: str, base_dir: str = DEFAULT_BASE_DIR) -> Dict[str, Any]:
    if existing["claimed_by"] != agent_id:
        return {
            "success": False,
            "message": f"Cannot release: file claimed by {existing['claimed_by']}"
        }
```

**Issue:** Relies on caller-provided `agent_id`. If CLI is used, the `--agent` flag can be spoofed.

**Recommendation:** Derive agent identity from authenticated session, not caller input.

### 3.3 Backup Deletion Access Control

**Finding: MEDIUM** - Anyone can delete backups:

**avcpm_rollback.py:**
```python
def delete_backup(backup_id: str, base_dir=DEFAULT_BASE_DIR) -> Dict:
    backup_path = get_backup_path(backup_id, base_dir)
    if not os.path.exists(backup_path):
        result["error"] = f"Backup {backup_id} not found"
        return result
    
    shutil.rmtree(backup_path)  # No authorization check!
    result["success"] = True
```

**Recommendation:** Implement role-based access control for destructive operations.

### 3.4 Branch Protection Bypass

**Finding: MEDIUM** - `force` flag bypasses all protections:

**avcpm_branch.py:**
```python
def delete_branch(name, force=False, base_dir=DEFAULT_BASE_DIR):
    if name == "main" and not force:
        raise ValueError("Cannot delete 'main' branch without force flag")
    # With force=True, all checks are bypassed
```

**Issue:** Single flag bypasses unmerged commit checks, dependent branch checks, and main branch protection.

**Recommendation:** Implement tiered authorization (regular user vs admin) instead of a single flag.

---

## 4. Data Integrity

### 4.1 Checksum Verification Coverage

**Finding: MEDIUM** - Checksums calculated but not always verified:

**avcpm_commit.py** - Calculates checksums:
```python
checksum = calculate_checksum(filepath)
```

**avcpm_merge.py** - Verifies signatures but not file checksums:
```python
is_valid = verify_commit_signature(commit_id, timestamp, changes, agent_id, signature, base_dir)
```

**Issue:** File contents could be modified in staging after commit without detection until explicit validation.

**Recommendation:** Verify checksums at merge time:
```python
for change in commit_data["changes"]:
    staging_path = change.get("staging_path")
    expected_checksum = change.get("checksum")
    if staging_path and os.path.exists(staging_path):
        actual_checksum = calculate_checksum(staging_path)
        if actual_checksum != expected_checksum:
            raise IntegrityError(f"Checksum mismatch for {change['file']}")
```

### 4.2 Ledger Tampering Detection

**Finding: MEDIUM** - No ledger integrity verification:

**Issue:** JSON files in ledger can be manually edited. The system has no mechanism to detect tampering.

**Recommendation:** Implement commit chaining with hash linking:
```python
{
    "commit_id": "abc123",
    "parent_hash": "sha256_of_previous_commit_json",
    "commit_hash": "sha256_of_this_commit_content_excluding_hash_field"
}
```

### 4.3 Backup Integrity

**Finding: LOW** - No backup integrity verification:

**avcpm_rollback.py:**
```python
def create_backup(...):
    # Copies files without checksum verification
    _copy_directory_tree(staging_dir, staging_backup)
```

**Recommendation:** Store manifest with checksums in backup metadata.

---

## 5. Vulnerabilities

### 5.1 Race Conditions (TOCTOU)

**Finding: MEDIUM** - Multiple Time-of-Check to Time-of-Use vulnerabilities:

**avcpm_agent.py:**
```python
if os.path.exists(agent_dir):
    raise ValueError(f"Branch '{name}' already exists")  # TOCTOU
# ... later ...
os.makedirs(agent_dir, exist_ok=True)
```

**avcpm_wip.py:**
```python
registry = _load_registry(base_dir)
if normalized_path in registry["claims"]:
    existing = registry["claims"][normalized_path]
    # Race: another process could modify registry between load and save
```

**Recommendation:** Use file locking or atomic operations:
```python
import fcntl

def with_locked_registry(func):
    def wrapper(*args, **kwargs):
        with open(REGISTRY_LOCK_FILE, 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                return func(*args, **kwargs)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
    return wrapper
```

### 5.2 Symlink Attacks

**Finding: HIGH** - Vulnerable to symlink attacks:

**avcpm_commit.py:**
```python
staging_path = os.path.join(staging_dir, os.path.basename(filepath))
shutil.copy2(filepath, staging_path)  # Follows symlinks!
```

**Exploit:**
```bash
ln -s /etc/shadow ./myfile.txt
python avcpm_commit.py commit TASK-001 agent "evil" myfile.txt
# Now /etc/shadow is copied to staging
```

**Recommendation:** Check for symlinks before operations:
```python
def is_safe_path(path: str) -> bool:
    """Check path is not a symlink and is within allowed directory."""
    if os.path.islink(path):
        return False
    real_path = os.path.realpath(path)
    # Additional checks...
    return True
```

### 5.3 Temporary File Security

**Finding: LOW** - Uses `os.urandom` but not for temp files:

**Issue:** No sensitive temp file handling. If temp files were used, they might have predictable names.

**Current Status:** Not currently using temp files, but future code should use `tempfile.mkstemp()`.

### 5.4 Signature Replay

**Finding: MEDIUM** - Signatures lack replay protection:

**avcpm_agent.py:**
```python
def sign_commit(commit_id, timestamp, changes, agent_id, base_dir=DEFAULT_BASE_DIR):
    changes_hash = calculate_changes_hash(changes)
    payload = f"{commit_id}:{timestamp}:{changes_hash}"
    signature = sign_data(agent_id, payload, base_dir)
```

**Issue:** Same commit could be replayed across different AVCPM instances or after deletion/re-creation.

**Recommendation:** Include domain separation or instance-specific nonce:
```python
payload = f"AVCPM_v1:{instance_id}:{commit_id}:{timestamp}:{changes_hash}"
```

---

## 6. Recommendations

### Priority 1 (Critical - Fix Immediately)

1. **Implement Path Traversal Protection**
   - Add `sanitize_path()` function used by all file operations
   - Validate all file paths are within allowed directories

2. **Add Agent Authentication**
   - Require private key proof for commit/sign operations
   - Don't trust caller-provided agent_id

3. **Fix Symlink Attacks**
   - Check `os.path.islink()` before file operations
   - Use `os.lstat()` instead of `os.stat()` where appropriate

### Priority 2 (High - Fix Soon)

4. **Implement File Locking**
   - Prevent race conditions in registry operations
   - Use atomic file operations

5. **Add Checksum Verification at Merge**
   - Verify all file checksums match ledger before merging

6. **Implement Branch Name Restrictions**
   - Add comprehensive validation for branch/task/agent names

### Priority 3 (Medium - Fix When Convenient)

7. **Add Ledger Integrity Chain**
   - Link commits with cryptographic hashes
   - Implement tamper detection

8. **Implement Role-Based Access Control**
   - Replace `force` flags with proper authorization
   - Add admin/user role separation

9. **Encrypt Private Keys**
   - Add optional password protection for private keys

10. **Add JSON Size Limits**
    - Prevent DoS from malformed files

### Priority 4 (Low - Documentation/Enhancement)

11. **Document Security Model**
    - Write security documentation
    - Define threat model

12. **Add Audit Logging**
    - Log all destructive operations
    - Include agent identity and timestamp

13. **Windows ACL Support**
    - Set appropriate permissions on Windows

---

## 7. Security Documentation Gaps

### Missing Documentation:

1. **Threat Model** - No document describing what threats AVCPM protects against
2. **Security Architecture** - No overview of security components
3. **Key Management Guide** - No guidance on key backup/rotation
4. **Incident Response** - No procedures for compromised keys
5. **Secure Deployment Guide** - No guidance on production deployment
6. **Agent Authentication** - No documentation on agent identity verification

### Suggested Documents to Create:

- `SECURITY.md` - Security policy and vulnerability reporting
- `THREAT_MODEL.md` - Documented threat model
- `KEY_MANAGEMENT.md` - Key lifecycle management
- `DEPLOYMENT_SECURITY.md` - Secure deployment guidelines

---

## 8. Summary of Findings

| ID | Severity | Category | Description |
|----|----------|----------|-------------|
| C1 | MEDIUM | Crypto | Private keys stored unencrypted |
| C2 | MEDIUM | Crypto | Key permissions not verified |
| I1 | **HIGH** | Input | Path traversal in file operations |
| I2 | MEDIUM | Input | Incomplete branch name validation |
| I3 | LOW | Input | JSON parsing without size limits |
| A1 | **HIGH** | Access | Agent impersonation possible |
| A2 | MEDIUM | Access | Anyone can delete backups |
| A3 | MEDIUM | Access | Force flag bypasses protections |
| D1 | MEDIUM | Data | Checksums not verified at merge |
| D2 | MEDIUM | Data | No ledger tampering detection |
| V1 | MEDIUM | Vuln | Race conditions in file operations |
| V2 | **HIGH** | Vuln | Symlink attacks possible |
| V3 | MEDIUM | Vuln | Signature replay possible |

**Total Findings:** 13  
**Critical/High:** 3  
**Medium:** 8  
**Low:** 2

---

*End of Security Review*
