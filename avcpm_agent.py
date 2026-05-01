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
import getpass
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

DEFAULT_BASE_DIR = ".avcpm"

# Encryption constants
ENCRYPTION_SALT_LENGTH = 16
ENCRYPTION_IV_LENGTH = 16
ENCRYPTION_KEY_LENGTH = 32
ENCRYPTION_ITERATIONS = 100000


def get_agents_dir(base_dir=DEFAULT_BASE_DIR):
    """Get the agents directory path."""
    return os.path.join(base_dir, "agents")


def get_agent_dir(agent_id, base_dir=DEFAULT_BASE_DIR):
    """Get a specific agent's directory path."""
    return os.path.join(get_agents_dir(base_dir), agent_id)


def get_registry_path(base_dir=DEFAULT_BASE_DIR):
    """Get the registry.json file path."""
    return os.path.join(get_agents_dir(base_dir), "registry.json")


from avcpm_security import protect_avcpm_directory, validate_path_is_safe, SecurityError, safe_makedirs

def ensure_directories(base_dir=DEFAULT_BASE_DIR):
    """Ensure agents directory exists with symlink attack protection."""
    protect_avcpm_directory(base_dir)
    safe_makedirs(get_agents_dir(base_dir), base_dir, exist_ok=True)


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


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    """
    Derive encryption key from passphrase using PBKDF2HMAC.
    
    Args:
        passphrase: The passphrase to derive key from
        salt: Random salt bytes
    
    Returns:
        Derived key bytes
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=ENCRYPTION_KEY_LENGTH,
        salt=salt,
        iterations=ENCRYPTION_ITERATIONS,
    )
    return kdf.derive(passphrase.encode('utf-8'))


def _encrypt_data(data: bytes, passphrase: str) -> bytes:
    """
    Encrypt data using AES-256-CBC with PBKDF2 key derivation.
    
    Args:
        data: Data to encrypt
        passphrase: Passphrase for encryption
    
    Returns:
        Encrypted data (salt + iv + ciphertext)
    """
    # Generate random salt and IV
    salt = os.urandom(ENCRYPTION_SALT_LENGTH)
    iv = os.urandom(ENCRYPTION_IV_LENGTH)
    
    # Derive key from passphrase
    key = _derive_key(passphrase, salt)
    
    # Create cipher and encrypt
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    
    # Pad data to block size (16 bytes for AES)
    pad_length = 16 - (len(data) % 16)
    padded_data = data + bytes([pad_length] * pad_length)
    
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    
    # Return salt + iv + ciphertext
    return salt + iv + ciphertext


def _decrypt_data(encrypted_data: bytes, passphrase: str) -> bytes:
    """
    Decrypt data using AES-256-CBC with PBKDF2 key derivation.
    
    Args:
        encrypted_data: Encrypted data (salt + iv + ciphertext)
        passphrase: Passphrase for decryption
    
    Returns:
        Decrypted data
    
    Raises:
        ValueError: If passphrase is incorrect or data is corrupted
    """
    if len(encrypted_data) < ENCRYPTION_SALT_LENGTH + ENCRYPTION_IV_LENGTH:
        raise ValueError("Invalid encrypted data format")
    
    # Extract salt, iv, and ciphertext
    salt = encrypted_data[:ENCRYPTION_SALT_LENGTH]
    iv = encrypted_data[ENCRYPTION_SALT_LENGTH:ENCRYPTION_SALT_LENGTH + ENCRYPTION_IV_LENGTH]
    ciphertext = encrypted_data[ENCRYPTION_SALT_LENGTH + ENCRYPTION_IV_LENGTH:]
    
    # Derive key from passphrase
    key = _derive_key(passphrase, salt)
    
    # Create cipher and decrypt
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    
    try:
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
    except Exception:
        raise ValueError("Failed to decrypt: invalid passphrase or corrupted data")
    
    # Remove padding
    pad_length = padded_data[-1]
    if pad_length > 16 or pad_length == 0:
        raise ValueError("Failed to decrypt: invalid passphrase or corrupted data")
    
    # Verify padding
    if padded_data[-pad_length:] != bytes([pad_length] * pad_length):
        raise ValueError("Failed to decrypt: invalid passphrase or corrupted data")
    
    return padded_data[:-pad_length]


def encrypt_private_key(agent_id, passphrase, base_dir=DEFAULT_BASE_DIR):
    """
    Encrypt an agent's private key with a passphrase.
    
    Args:
        agent_id: The agent ID
        passphrase: Passphrase for encryption
        base_dir: Base directory for AVCPM
    
    Returns:
        dict: Status with success flag and message
    
    Raises:
        ValueError: If private key not found or already encrypted
    """
    agent_dir = get_agent_dir(agent_id, base_dir)
    private_path = os.path.join(agent_dir, "private.pem")
    encrypted_path = os.path.join(agent_dir, "private.pem.enc")
    
    # Check if already encrypted
    if os.path.exists(encrypted_path):
        raise ValueError(f"Private key for agent {agent_id} is already encrypted")
    
    if not os.path.exists(private_path):
        raise ValueError(f"Private key not found for agent {agent_id}")
    
    # Read the private key
    with open(private_path, "rb") as f:
        private_key_data = f.read()
    
    # Encrypt the key
    encrypted_data = _encrypt_data(private_key_data, passphrase)
    
    # Write encrypted key
    with open(encrypted_path, "wb") as f:
        f.write(encrypted_data)
    
    # Set permissions (readable only by owner)
    os.chmod(encrypted_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    
    # Remove unencrypted key
    os.remove(private_path)
    
    # Update registry to mark as encrypted
    registry = _load_registry(base_dir)
    if agent_id in registry.get("agents", {}):
        registry["agents"][agent_id]["encrypted"] = True
        _save_registry(registry, base_dir)
    
    return {"success": True, "message": f"Private key for agent {agent_id} encrypted successfully"}


def decrypt_private_key(agent_id, passphrase, base_dir=DEFAULT_BASE_DIR):
    """
    Decrypt an agent's private key using passphrase.
    
    Args:
        agent_id: The agent ID
        passphrase: Passphrase for decryption
        base_dir: Base directory for AVCPM
    
    Returns:
        The private key object
    
    Raises:
        ValueError: If decryption fails or key not found
    """
    encrypted_path = os.path.join(get_agent_dir(agent_id, base_dir), "private.pem.enc")
    
    if not os.path.exists(encrypted_path):
        raise ValueError(f"Encrypted private key not found for agent {agent_id}")
    
    # Read encrypted key
    with open(encrypted_path, "rb") as f:
        encrypted_data = f.read()
    
    # Decrypt the key
    try:
        private_key_data = _decrypt_data(encrypted_data, passphrase)
    except ValueError as e:
        raise ValueError(f"Failed to decrypt private key: {e}")
    
    # Load the private key
    return serialization.load_pem_private_key(private_key_data, password=None)


def is_key_encrypted(agent_id, base_dir=DEFAULT_BASE_DIR):
    """
    Check if an agent's private key is encrypted.
    
    Args:
        agent_id: The agent ID
        base_dir: Base directory for AVCPM
    
    Returns:
        bool: True if encrypted, False otherwise
    """
    encrypted_path = os.path.join(get_agent_dir(agent_id, base_dir), "private.pem.enc")
    return os.path.exists(encrypted_path)


def _load_private_key(agent_id, base_dir=DEFAULT_BASE_DIR, passphrase=None):
    """
    Load a private key from file.
    
    Args:
        agent_id: The agent ID
        base_dir: Base directory for AVCPM
        passphrase: REQUIRED passphrase for decrypting the encrypted key
    
    Returns:
        The private key object
    
    Raises:
        ValueError: If passphrase is not provided or key not found
    """
    if not passphrase:
        raise ValueError(f"Passphrase is required to load private key for agent {agent_id}")
    
    encrypted_path = os.path.join(get_agent_dir(agent_id, base_dir), "private.pem.enc")
    legacy_path = os.path.join(get_agent_dir(agent_id, base_dir), "private.pem")
    
    # Check for encrypted key
    if os.path.exists(encrypted_path):
        return decrypt_private_key(agent_id, passphrase, base_dir)
    
    # Check for legacy unencrypted key (should not exist in new agents)
    if os.path.exists(legacy_path):
        raise ValueError(
            f"Legacy unencrypted private key found for agent {agent_id}. "
            f"This key format is no longer supported. Please recreate the agent with a passphrase."
        )
    
    raise ValueError(f"Private key not found for agent {agent_id}")


def _load_public_key(agent_id, base_dir=DEFAULT_BASE_DIR):
    """Load a public key from file."""
    public_path = os.path.join(get_agent_dir(agent_id, base_dir), "public.pem")
    if not os.path.exists(public_path):
        raise ValueError(f"Public key not found for agent {agent_id}")
    
    with open(public_path, "rb") as f:
        return serialization.load_pem_public_key(f.read())


def create_agent(name, email, base_dir=DEFAULT_BASE_DIR, passphrase=None):
    """
    Create a new agent with RSA key pair.
    
    Args:
        name: Agent name
        email: Agent email
        base_dir: Base directory for AVCPM (default: .avcpm)
        passphrase: REQUIRED passphrase to encrypt private key (minimum 8 characters)
    
    Returns:
        dict: Agent metadata including agent_id, name, email, created_at
    
    Raises:
        ValueError: If passphrase is not provided or is too short
    """
    ensure_directories(base_dir)
    
    agent_id = _generate_agent_id()
    agent_dir = get_agent_dir(agent_id, base_dir)
    
    # Check for collision (unlikely but possible)
    while os.path.exists(agent_dir):
        agent_id = _generate_agent_id()
        agent_dir = get_agent_dir(agent_id, base_dir)
    
    safe_makedirs(agent_dir, base_dir, exist_ok=True)
    
    # Generate key pair
    private_key, public_key = _generate_key_pair()
    
    # Serialize keys
    private_pem = _serialize_private_key(private_key)
    public_pem = _serialize_public_key(public_key)
    
    # Write public key
    public_path = os.path.join(agent_dir, "public.pem")
    with open(public_path, "wb") as f:
        f.write(public_pem)
    
    # Validate passphrase is required
    if not passphrase:
        raise ValueError("Passphrase is required for private key encryption. Please provide a passphrase of at least 8 characters.")
    if len(passphrase) < 8:
        raise ValueError("Passphrase must be at least 8 characters long.")
    
    # Encrypt and store private key (always encrypted)
    encrypted_data = _encrypt_data(private_pem, passphrase)
    private_path = os.path.join(agent_dir, "private.pem.enc")
    with open(private_path, "wb") as f:
        f.write(encrypted_data)
    os.chmod(private_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    private_key_path = private_path
    
    # Create agent metadata
    agent_data = {
        "agent_id": agent_id,
        "name": name,
        "email": email,
        "created_at": datetime.now().isoformat(),
        "public_key_path": public_path,
        "private_key_path": private_key_path
    }
    
    # Update registry
    registry = _load_registry(base_dir)
    registry["agents"][agent_id] = {
        "name": name,
        "email": email,
        "created_at": agent_data["created_at"],
        "encrypted": True
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


def sign_data(agent_id, data, base_dir=DEFAULT_BASE_DIR, passphrase=None):
    """
    Sign data with an agent's private key.
    
    Args:
        agent_id: The agent ID
        data: Data to sign (string or bytes)
        base_dir: Base directory for AVCPM (default: .avcpm)
        passphrase: REQUIRED passphrase for decrypting the encrypted private key
    
    Returns:
        bytes: The signature
    
    Raises:
        ValueError: If passphrase is not provided
    """
    # Convert string to bytes if needed
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    private_key = _load_private_key(agent_id, base_dir, passphrase)
    
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


def sign_commit(commit_id, timestamp, changes, agent_id, base_dir=DEFAULT_BASE_DIR, passphrase=None):
    """
    Sign commit metadata (commit_id + timestamp + changes hash).
    
    Args:
        commit_id: The commit ID
        timestamp: ISO format timestamp
        changes: List of change dictionaries
        agent_id: The agent ID signing the commit
        base_dir: Base directory for AVCPM (default: .avcpm)
        passphrase: REQUIRED passphrase for decrypting the encrypted private key
    
    Returns:
        dict: Signed commit metadata with signature and agent_id
    
    Raises:
        ValueError: If passphrase is not provided
    """
    changes_hash = calculate_changes_hash(changes)
    
    # Create signing payload
    payload = f"{commit_id}:{timestamp}:{changes_hash}"
    
    # Sign the payload
    signature = sign_data(agent_id, payload, base_dir, passphrase)
    
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
    print("  python avcpm_agent.py create <name> <email> [--encrypt]")
    print("  python avcpm_agent.py list")
    print("  python avcpm_agent.py show <agent_id>")
    print("  python avcpm_agent.py encrypt <agent_id>")
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
            print("Usage: python avcpm_agent.py create <name> <email> [--encrypt]")
            sys.exit(1)
        
        name = sys.argv[2]
        email = sys.argv[3]
        encrypt = "--encrypt" in sys.argv
        
        passphrase = None
        if encrypt:
            # Prompt for passphrase securely
            passphrase = getpass.getpass("Enter passphrase for private key encryption: ")
            confirm = getpass.getpass("Confirm passphrase: ")
            if passphrase != confirm:
                print("Error: Passphrases do not match")
                sys.exit(1)
            if len(passphrase) < 8:
                print("Error: Passphrase must be at least 8 characters")
                sys.exit(1)
        
        try:
            agent = create_agent(name, email, passphrase=passphrase)
            print(f"Agent created successfully!")
            print(f"  ID: {agent['agent_id']}")
            print(f"  Name: {agent['name']}")
            print(f"  Email: {agent['email']}")
            print(f"  Created: {agent['created_at']}")
            if encrypt:
                print(f"  Encryption: Enabled")
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
                encrypted = info.get('encrypted', False)
                print(f"  Encrypted: {'Yes' if encrypted else 'No'}")
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
            print(f"  Encrypted: {'Yes' if agent.get('encrypted', False) else 'No'}")
        else:
            print(f"Agent {agent_id} not found.")
            sys.exit(1)
    
    elif cmd == "encrypt":
        if len(sys.argv) < 3:
            print("Error: encrypt requires agent_id")
            print("Usage: python avcpm_agent.py encrypt <agent_id>")
            sys.exit(1)
        
        agent_id = sys.argv[2]
        
        # Check agent exists
        agent = get_agent(agent_id)
        if not agent:
            print(f"Agent {agent_id} not found.")
            sys.exit(1)
        
        # Prompt for passphrase securely
        passphrase = getpass.getpass("Enter passphrase for encryption: ")
        confirm = getpass.getpass("Confirm passphrase: ")
        if passphrase != confirm:
            print("Error: Passphrases do not match")
            sys.exit(1)
        if len(passphrase) < 8:
            print("Error: Passphrase must be at least 8 characters")
            sys.exit(1)
        
        try:
            result = encrypt_private_key(agent_id, passphrase)
            print(result["message"])
        except Exception as e:
            print(f"Error encrypting key: {e}")
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
        
        # Check if key is encrypted and prompt for passphrase
        passphrase = None
        if is_key_encrypted(agent_id):
            passphrase = getpass.getpass("Enter passphrase to decrypt private key: ")
        
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            
            signature = sign_data(agent_id, data, passphrase=passphrase)
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
