"""
AVCPM Agent Identity System

Provides cryptographic identity for AVCPM agents using RSA 2048-bit key pairs.
"""

import os
import sys
import json
import hashlib
import uuid
import stat
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.exceptions import InvalidSignature

DEFAULT_BASE_DIR = ".avcpm"


def get_agents_dir(base_dir=DEFAULT_BASE_DIR):
    """Get the agents directory path."""
    return os.path.join(base_dir, "agents")


def get_agent_dir(agent_id, base_dir=DEFAULT_BASE_DIR):
    """Get a specific agent's directory path."""
    return os.path.join(get_agents_dir(base_dir), agent_id)


def get_registry_path(base_dir=DEFAULT_BASE_DIR):
    """Get the registry.json file path."""
    return os.path.join(get_agents_dir(base_dir), "registry.json")


def ensure_directories(base_dir=DEFAULT_BASE_DIR):
    """Ensure agents directory exists."""
    os.makedirs(get_agents_dir(base_dir), exist_ok=True)


def _load_registry(base_dir=DEFAULT_BASE_DIR):
    """Load the agent registry."""
    registry_path = get_registry_path(base_dir)
    if os.path.exists(registry_path):
        with open(registry_path, "r") as f:
            return json.load(f)
    return {"agents": {}}


def _save_registry(registry, base_dir=DEFAULT_BASE_DIR):
    """Save the agent registry."""
    ensure_directories(base_dir)
    registry_path = get_registry_path(base_dir)
    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=4)


def _generate_agent_id():
    """Generate a unique agent ID."""
    return str(uuid.uuid4())[:8]


def _generate_key_pair():
    """Generate RSA 2048-bit key pair."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    return private_key, private_key.public_key()


def _serialize_private_key(private_key):
    """Serialize private key to PEM format."""
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )


def _serialize_public_key(public_key):
    """Serialize public key to PEM format."""
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )


def _load_private_key(agent_id, base_dir=DEFAULT_BASE_DIR):
    """Load a private key from file."""
    private_path = os.path.join(get_agent_dir(agent_id, base_dir), "private.pem")
    if not os.path.exists(private_path):
        raise ValueError(f"Private key not found for agent {agent_id}")
    
    with open(private_path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def _load_public_key(agent_id, base_dir=DEFAULT_BASE_DIR):
    """Load a public key from file."""
    public_path = os.path.join(get_agent_dir(agent_id, base_dir), "public.pem")
    if not os.path.exists(public_path):
        raise ValueError(f"Public key not found for agent {agent_id}")
    
    with open(public_path, "rb") as f:
        return serialization.load_pem_public_key(f.read())


def create_agent(name, email, base_dir=DEFAULT_BASE_DIR):
    """
    Create a new agent with RSA key pair.
    
    Args:
        name: Agent name
        email: Agent email
        base_dir: Base directory for AVCPM (default: .avcpm)
    
    Returns:
        dict: Agent metadata including agent_id, name, email, created_at
    """
    ensure_directories(base_dir)
    
    agent_id = _generate_agent_id()
    agent_dir = get_agent_dir(agent_id, base_dir)
    
    # Check for collision (unlikely but possible)
    while os.path.exists(agent_dir):
        agent_id = _generate_agent_id()
        agent_dir = get_agent_dir(agent_id, base_dir)
    
    os.makedirs(agent_dir, exist_ok=True)
    
    # Generate key pair
    private_key, public_key = _generate_key_pair()
    
    # Serialize keys
    private_pem = _serialize_private_key(private_key)
    public_pem = _serialize_public_key(public_key)
    
    # Write keys to files
    private_path = os.path.join(agent_dir, "private.pem")
    public_path = os.path.join(agent_dir, "public.pem")
    
    with open(private_path, "wb") as f:
        f.write(private_pem)
    
    with open(public_path, "wb") as f:
        f.write(public_pem)
    
    # Set permissions on private key (readable only by owner)
    os.chmod(private_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    
    # Create agent metadata
    agent_data = {
        "agent_id": agent_id,
        "name": name,
        "email": email,
        "created_at": datetime.now().isoformat(),
        "public_key_path": public_path,
        "private_key_path": private_path
    }
    
    # Update registry
    registry = _load_registry(base_dir)
    registry["agents"][agent_id] = {
        "name": name,
        "email": email,
        "created_at": agent_data["created_at"]
    }
    _save_registry(registry, base_dir)
    
    return agent_data


def list_agents(base_dir=DEFAULT_BASE_DIR):
    """
    List all registered agents.
    
    Args:
        base_dir: Base directory for AVCPM (default: .avcpm)
    
    Returns:
        dict: Dictionary mapping agent_id to agent info
    """
    registry = _load_registry(base_dir)
    return registry.get("agents", {})


def get_agent(agent_id, base_dir=DEFAULT_BASE_DIR):
    """
    Get agent details by ID.
    
    Args:
        agent_id: The agent ID
        base_dir: Base directory for AVCPM (default: .avcpm)
    
    Returns:
        dict: Agent details or None if not found
    """
    registry = _load_registry(base_dir)
    agent_info = registry.get("agents", {}).get(agent_id)
    if agent_info:
        return {**agent_info, "agent_id": agent_id}
    return None


def get_public_key(agent_id, base_dir=DEFAULT_BASE_DIR):
    """
    Get the public key for an agent.
    
    Args:
        agent_id: The agent ID
        base_dir: Base directory for AVCPM (default: .avcpm)
    
    Returns:
        bytes: PEM-encoded public key or None if not found
    """
    public_path = os.path.join(get_agent_dir(agent_id, base_dir), "public.pem")
    if os.path.exists(public_path):
        with open(public_path, "rb") as f:
            return f.read()
    return None


def sign_data(agent_id, data, base_dir=DEFAULT_BASE_DIR):
    """
    Sign data with an agent's private key.
    
    Args:
        agent_id: The agent ID
        data: Data to sign (string or bytes)
        base_dir: Base directory for AVCPM (default: .avcpm)
    
    Returns:
        bytes: The signature
    """
    # Convert string to bytes if needed
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    private_key = _load_private_key(agent_id, base_dir)
    
    signature = private_key.sign(
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    
    return signature


def verify_signature(agent_id, data, signature, base_dir=DEFAULT_BASE_DIR):
    """
    Verify data signature with an agent's public key.
    
    Args:
        agent_id: The agent ID
        data: Data that was signed (string or bytes)
        signature: The signature to verify (bytes)
        base_dir: Base directory for AVCPM (default: .avcpm)
    
    Returns:
        bool: True if signature is valid, False otherwise
    """
    # Convert string to bytes if needed
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    try:
        public_key = _load_public_key(agent_id, base_dir)
        
        public_key.verify(
            signature,
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except (InvalidSignature, ValueError):
        return False


def calculate_changes_hash(changes):
    """
    Calculate a hash of the changes for commit signing.
    
    Args:
        changes: List of change dictionaries with file and checksum
    
    Returns:
        str: Hex digest of the changes hash
    """
    hasher = hashlib.sha256()
    for change in sorted(changes, key=lambda x: x.get('file', '')):
        file_path = change.get('file', '')
        checksum = change.get('checksum', '')
        hasher.update(f"{file_path}:{checksum}\n".encode('utf-8'))
    return hasher.hexdigest()


def sign_commit(commit_id, timestamp, changes, agent_id, base_dir=DEFAULT_BASE_DIR):
    """
    Sign commit metadata (commit_id + timestamp + changes hash).
    
    Args:
        commit_id: The commit ID
        timestamp: ISO format timestamp
        changes: List of change dictionaries
        agent_id: The agent ID signing the commit
        base_dir: Base directory for AVCPM (default: .avcpm)
    
    Returns:
        dict: Signed commit metadata with signature and agent_id
    """
    changes_hash = calculate_changes_hash(changes)
    
    # Create signing payload
    payload = f"{commit_id}:{timestamp}:{changes_hash}"
    
    # Sign the payload
    signature = sign_data(agent_id, payload, base_dir)
    
    return {
        "commit_id": commit_id,
        "timestamp": timestamp,
        "changes_hash": changes_hash,
        "agent_id": agent_id,
        "signature": signature.hex()
    }


def verify_commit_signature(commit_id, timestamp, changes, agent_id, signature_hex, base_dir=DEFAULT_BASE_DIR):
    """
    Verify a commit signature.
    
    Args:
        commit_id: The commit ID
        timestamp: ISO format timestamp
        changes: List of change dictionaries
        agent_id: The agent ID that signed
        signature_hex: Hex-encoded signature
        base_dir: Base directory for AVCPM (default: .avcpm)
    
    Returns:
        bool: True if signature is valid, False otherwise
    """
    changes_hash = calculate_changes_hash(changes)
    payload = f"{commit_id}:{timestamp}:{changes_hash}"
    
    try:
        signature = bytes.fromhex(signature_hex)
    except ValueError:
        return False
    
    return verify_signature(agent_id, payload, signature, base_dir)


def print_help():
    """Print CLI help message."""
    print("AVCPM Agent Identity System")
    print("Usage:")
    print("  python avcpm_agent.py create <name> <email>")
    print("  python avcpm_agent.py list")
    print("  python avcpm_agent.py show <agent_id>")
    print("  python avcpm_agent.py sign <agent_id> <file>")
    print("  python avcpm_agent.py verify <agent_id> <file> <signature_file>")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "create":
        if len(sys.argv) < 4:
            print("Error: create requires name and email")
            print("Usage: python avcpm_agent.py create <name> <email>")
            sys.exit(1)
        
        name = sys.argv[2]
        email = sys.argv[3]
        
        try:
            agent = create_agent(name, email)
            print(f"Agent created successfully!")
            print(f"  ID: {agent['agent_id']}")
            print(f"  Name: {agent['name']}")
            print(f"  Email: {agent['email']}")
            print(f"  Created: {agent['created_at']}")
        except Exception as e:
            print(f"Error creating agent: {e}")
            sys.exit(1)
    
    elif cmd == "list":
        agents = list_agents()
        if not agents:
            print("No agents registered.")
        else:
            print("Registered Agents:")
            print("-" * 60)
            for agent_id, info in agents.items():
                print(f"  ID: {agent_id}")
                print(f"  Name: {info.get('name', 'N/A')}")
                print(f"  Email: {info.get('email', 'N/A')}")
                print(f"  Created: {info.get('created_at', 'N/A')}")
                print("-" * 60)
    
    elif cmd == "show":
        if len(sys.argv) < 3:
            print("Error: show requires agent_id")
            print("Usage: python avcpm_agent.py show <agent_id>")
            sys.exit(1)
        
        agent_id = sys.argv[2]
        agent = get_agent(agent_id)
        
        if agent:
            print(f"Agent: {agent['name']}")
            print(f"  ID: {agent['agent_id']}")
            print(f"  Email: {agent['email']}")
            print(f"  Created: {agent['created_at']}")
        else:
            print(f"Agent {agent_id} not found.")
            sys.exit(1)
    
    elif cmd == "sign":
        if len(sys.argv) < 4:
            print("Error: sign requires agent_id and file")
            print("Usage: python avcpm_agent.py sign <agent_id> <file>")
            sys.exit(1)
        
        agent_id = sys.argv[2]
        file_path = sys.argv[3]
        
        if not os.path.exists(file_path):
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
        
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            
            signature = sign_data(agent_id, data)
            sig_path = f"{file_path}.sig"
            
            with open(sig_path, "wb") as f:
                f.write(signature)
            
            print(f"Signature saved to: {sig_path}")
        except Exception as e:
            print(f"Error signing file: {e}")
            sys.exit(1)
    
    elif cmd == "verify":
        if len(sys.argv) < 5:
            print("Error: verify requires agent_id, file, and signature_file")
            print("Usage: python avcpm_agent.py verify <agent_id> <file> <signature_file>")
            sys.exit(1)
        
        agent_id = sys.argv[2]
        file_path = sys.argv[3]
        sig_path = sys.argv[4]
        
        if not os.path.exists(file_path):
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
        
        if not os.path.exists(sig_path):
            print(f"Error: Signature file not found: {sig_path}")
            sys.exit(1)
        
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            
            with open(sig_path, "rb") as f:
                signature = f.read()
            
            if verify_signature(agent_id, data, signature):
                print("Signature is VALID")
            else:
                print("Signature is INVALID")
                sys.exit(1)
        except Exception as e:
            print(f"Error verifying signature: {e}")
            sys.exit(1)
    
    else:
        print(f"Unknown command: {cmd}")
        print_help()
        sys.exit(1)
