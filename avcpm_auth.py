"""
AVCPM Agent Authentication System

Provides challenge-response authentication for agents to prevent impersonation.
"""

import os
import sys
import json
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

from avcpm_audit import audit_log, EVENT_AUTH_SUCCESS, EVENT_AUTH_FAILURE

DEFAULT_BASE_DIR = ".avcpm"
SESSION_DURATION_MINUTES = 60  # Sessions expire after 60 minutes


def get_sessions_dir(base_dir=DEFAULT_BASE_DIR):
    """Get the agent sessions directory path."""
    return os.path.join(base_dir, "agent_sessions")


def get_challenges_dir(base_dir=DEFAULT_BASE_DIR):
    """Get the challenges directory path."""
    return os.path.join(base_dir, "agent_challenges")


def ensure_auth_directories(base_dir=DEFAULT_BASE_DIR):
    """Ensure authentication directories exist."""
    os.makedirs(get_sessions_dir(base_dir), exist_ok=True)
    os.makedirs(get_challenges_dir(base_dir), exist_ok=True)


def generate_challenge():
    """Generate a cryptographically secure random challenge."""
    return secrets.token_hex(32)  # 64 hex characters = 256 bits


def create_challenge(agent_id, base_dir=DEFAULT_BASE_DIR):
    """
    Create a new challenge for an agent to sign.
    
    Args:
        agent_id: The agent to challenge
        base_dir: Base directory for AVCPM
    
    Returns:
        str: The challenge string
    """
    from avcpm_security import validate_agent_id
    validate_agent_id(agent_id)
    ensure_auth_directories(base_dir)
    
    challenge = generate_challenge()
    challenge_data = {
        "challenge": challenge,
        "agent_id": agent_id,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(minutes=5)).isoformat()
    }
    
    # Store challenge
    challenges_dir = get_challenges_dir(base_dir)
    challenge_file = os.path.join(challenges_dir, f"{agent_id}.json")
    with open(challenge_file, "w") as f:
        json.dump(challenge_data, f, indent=4)
    
    return challenge


def get_challenge(agent_id, base_dir=DEFAULT_BASE_DIR):
    """
    Get the current challenge for an agent.
    
    Args:
        agent_id: The agent ID
        base_dir: Base directory for AVCPM
    
    Returns:
        str: The challenge or None if not found/expired
    """
    from avcpm_security import validate_agent_id
    validate_agent_id(agent_id)
    challenges_dir = get_challenges_dir(base_dir)
    challenge_file = os.path.join(challenges_dir, f"{agent_id}.json")
    
    if not os.path.exists(challenge_file):
        return None
    
    with open(challenge_file, "r") as f:
        challenge_data = json.load(f)
    
    # Check if expired
    expires_at = datetime.fromisoformat(challenge_data["expires_at"])
    if datetime.now() > expires_at:
        # Clean up expired challenge
        os.remove(challenge_file)
        return None
    
    return challenge_data["challenge"]


def clear_challenge(agent_id, base_dir=DEFAULT_BASE_DIR):
    """Clear the challenge for an agent (used after successful auth)."""
    from avcpm_security import validate_agent_id
    validate_agent_id(agent_id)
    challenges_dir = get_challenges_dir(base_dir)
    challenge_file = os.path.join(challenges_dir, f"{agent_id}.json")
    if os.path.exists(challenge_file):
        os.remove(challenge_file)


def sign_challenge_response(challenge, agent_id, base_dir=DEFAULT_BASE_DIR):
    """
    Sign a challenge response using the agent's private key.
    
    Args:
        challenge: The challenge string
        agent_id: The agent ID
        base_dir: Base directory for AVCPM
    
    Returns:
        str: Hex-encoded signature
    """
    from avcpm_agent import sign_data
    
    # Create payload: "AVCPM_AUTH:<agent_id>:<challenge>"
    payload = f"AVCPM_AUTH:{agent_id}:{challenge}"
    signature = sign_data(agent_id, payload, base_dir)
    return signature.hex()


def verify_challenge_response(challenge, agent_id, signature_hex, base_dir=DEFAULT_BASE_DIR):
    """
    Verify a challenge response signature.
    
    Args:
        challenge: The challenge string
        agent_id: The agent ID
        signature_hex: Hex-encoded signature
        base_dir: Base directory for AVCPM
    
    Returns:
        bool: True if valid, False otherwise
    """
    from avcpm_agent import verify_signature
    
    payload = f"AVCPM_AUTH:{agent_id}:{challenge}"
    
    try:
        signature = bytes.fromhex(signature_hex)
    except ValueError:
        return False
    
    return verify_signature(agent_id, payload, signature, base_dir)


def create_session(agent_id, base_dir=DEFAULT_BASE_DIR):
    """
    Create an authenticated session for an agent.
    
    Args:
        agent_id: The authenticated agent ID
        base_dir: Base directory for AVCPM
    
    Returns:
        dict: Session data including session token
    """
    from avcpm_security import validate_agent_id
    validate_agent_id(agent_id)
    ensure_auth_directories(base_dir)
    
    # Generate session token
    session_token = secrets.token_hex(32)
    
    session_data = {
        "session_token": session_token,
        "agent_id": agent_id,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(minutes=SESSION_DURATION_MINUTES)).isoformat(),
        "last_used": datetime.now().isoformat()
    }
    
    # Store session
    sessions_dir = get_sessions_dir(base_dir)
    session_file = os.path.join(sessions_dir, f"{agent_id}.json")
    with open(session_file, "w") as f:
        json.dump(session_data, f, indent=4)
    
    return session_data


def get_session(agent_id, base_dir=DEFAULT_BASE_DIR):
    """
    Get the current session for an agent.
    
    Args:
        agent_id: The agent ID
        base_dir: Base directory for AVCPM
    
    Returns:
        dict: Session data or None if not found/expired
    """
    from avcpm_security import validate_agent_id
    validate_agent_id(agent_id)
    sessions_dir = get_sessions_dir(base_dir)
    session_file = os.path.join(sessions_dir, f"{agent_id}.json")
    
    if not os.path.exists(session_file):
        return None
    
    with open(session_file, "r") as f:
        session_data = json.load(f)
    
    # Check if expired
    expires_at = datetime.fromisoformat(session_data["expires_at"])
    if datetime.now() > expires_at:
        # Clean up expired session
        os.remove(session_file)
        return None
    
    return session_data


def validate_session(agent_id, session_token, base_dir=DEFAULT_BASE_DIR):
    """
    Validate a session token for an agent.
    
    Args:
        agent_id: The agent ID
        session_token: The session token to validate
        base_dir: Base directory for AVCPM
    
    Returns:
        bool: True if session is valid, False otherwise
    """
    from avcpm_security import validate_agent_id
    validate_agent_id(agent_id)
    session = get_session(agent_id, base_dir)
    if session is None:
        return False
    
    if not secrets.compare_digest(session["session_token"], session_token):
        return False
    
    # Update last used time
    sessions_dir = get_sessions_dir(base_dir)
    session_file = os.path.join(sessions_dir, f"{agent_id}.json")
    session["last_used"] = datetime.now().isoformat()
    with open(session_file, "w") as f:
        json.dump(session, f, indent=4)
    
    return True


def delete_session(agent_id, base_dir=DEFAULT_BASE_DIR):
    """Delete an agent's session (logout)."""
    from avcpm_security import validate_agent_id
    validate_agent_id(agent_id)
    sessions_dir = get_sessions_dir(base_dir)
    session_file = os.path.join(sessions_dir, f"{agent_id}.json")
    if os.path.exists(session_file):
        os.remove(session_file)
        return True
    return False


def authenticate_agent(agent_id, proof, base_dir=DEFAULT_BASE_DIR):
    """
    Authenticate an agent using challenge-response.
    
    Args:
        agent_id: The agent to authenticate
        proof: The signed challenge response (signature)
        base_dir: Base directory for AVCPM
    
    Returns:
        tuple: (success: bool, result: dict or error message)
            - On success: (True, session_data)
            - On failure: (False, error_message)
    """
    from avcpm_security import validate_agent_id
    validate_agent_id(agent_id)
    from avcpm_agent import get_agent
    
    # Check if agent exists
    agent = get_agent(agent_id, base_dir)
    if agent is None:
        audit_log(EVENT_AUTH_FAILURE, agent_id, {"reason": "agent_not_found"})
        return False, f"Agent {agent_id} not found"
    
    # Get the current challenge
    challenge = get_challenge(agent_id, base_dir)
    if challenge is None:
        audit_log(EVENT_AUTH_FAILURE, agent_id, {"reason": "no_active_challenge"})
        return False, "No active challenge found. Request a challenge first."
    
    # Verify the challenge response
    if not verify_challenge_response(challenge, agent_id, proof, base_dir):
        audit_log(EVENT_AUTH_FAILURE, agent_id, {"reason": "invalid_signature"})
        return False, "Invalid signature. Authentication failed."
    
    # Clear the used challenge
    clear_challenge(agent_id, base_dir)
    
    # Create session
    session = create_session(agent_id, base_dir)
    
    audit_log(EVENT_AUTH_SUCCESS, agent_id, {"session_expires_at": session.get("expires_at")})
    return True, session


def require_auth(agent_id, base_dir=DEFAULT_BASE_DIR):
    """
    Decorator helper to require authentication for an operation.
    Checks if the agent has a valid session.
    
    Args:
        agent_id: The agent ID claiming to perform the operation
        base_dir: Base directory for AVCPM
    
    Returns:
        tuple: (success: bool, error_message or None)
    """
    from avcpm_security import validate_agent_id
    validate_agent_id(agent_id)
    session = get_session(agent_id, base_dir)
    if session is None:
        return False, f"Agent {agent_id} is not authenticated. Run 'avcpm agent authenticate {agent_id}' first."
    
    return True, None


def get_session_token_from_env():
    """Get session token from environment variable."""
    return os.environ.get("AVCPM_SESSION_TOKEN")


def get_authenticated_agent_from_env(base_dir=DEFAULT_BASE_DIR):
    """
    Get authenticated agent from environment.
    
    Returns:
        tuple: (agent_id, session_token) or (None, None) if not set
    """
    agent_id = os.environ.get("AVCPM_AGENT_ID")
    session_token = os.environ.get("AVCPM_SESSION_TOKEN")
    
    if not agent_id or not session_token:
        return None, None
    
    # Validate the session
    if validate_session(agent_id, session_token, base_dir):
        return agent_id, session_token
    
    return None, None


def list_active_sessions(base_dir=DEFAULT_BASE_DIR):
    """
    List all active sessions.
    
    Returns:
        list: List of active session data
    """
    ensure_auth_directories(base_dir)
    sessions_dir = get_sessions_dir(base_dir)
    
    sessions = []
    if not os.path.exists(sessions_dir):
        return sessions
    
    for filename in os.listdir(sessions_dir):
        if filename.endswith(".json"):
            session_file = os.path.join(sessions_dir, filename)
            try:
                with open(session_file, "r") as f:
                    session_data = json.load(f)
                
                # Check if expired
                expires_at = datetime.fromisoformat(session_data["expires_at"])
                if datetime.now() <= expires_at:
                    sessions.append(session_data)
                else:
                    # Clean up expired session
                    os.remove(session_file)
            except (json.JSONDecodeError, OSError) as e:
                # Quarantine corrupted session file
                corrupt_path = session_file + ".corrupt"
                try:
                    os.rename(session_file, corrupt_path)
                    print(f"Warning: Quarantined corrupted session file: {filename} -> {filename}.corrupt")
                except OSError:
                    pass  # Can't quarantine, skip
                continue
    
    return sessions


def cleanup_expired_sessions(base_dir=DEFAULT_BASE_DIR):
    """Clean up all expired sessions and challenges."""
    ensure_auth_directories(base_dir)
    
    # Clean up expired sessions
    sessions_dir = get_sessions_dir(base_dir)
    if os.path.exists(sessions_dir):
        for filename in os.listdir(sessions_dir):
            if filename.endswith(".json"):
                session_file = os.path.join(sessions_dir, filename)
                try:
                    with open(session_file, "r") as f:
                        session_data = json.load(f)
                    
                    expires_at = datetime.fromisoformat(session_data["expires_at"])
                    if datetime.now() > expires_at:
                        os.remove(session_file)
                except (json.JSONDecodeError, OSError) as e:
                    # Quarantine corrupted session file
                    corrupt_path = session_file + ".corrupt"
                    try:
                        os.rename(session_file, corrupt_path)
                        print(f"Warning: Quarantined corrupted session file: {filename} -> {filename}.corrupt")
                    except OSError:
                        pass  # Can't quarantine, skip
                    continue
    
    # Clean up expired challenges
    challenges_dir = get_challenges_dir(base_dir)
    if os.path.exists(challenges_dir):
        for filename in os.listdir(challenges_dir):
            if filename.endswith(".json"):
                challenge_file = os.path.join(challenges_dir, filename)
                try:
                    with open(challenge_file, "r") as f:
                        challenge_data = json.load(f)
                    
                    expires_at = datetime.fromisoformat(challenge_data["expires_at"])
                    if datetime.now() > expires_at:
                        os.remove(challenge_file)
                except (json.JSONDecodeError, OSError) as e:
                    # Quarantine corrupted challenge file
                    corrupt_path = challenge_file + ".corrupt"
                    try:
                        os.rename(challenge_file, corrupt_path)
                        print(f"Warning: Quarantined corrupted challenge file: {filename} -> {filename}.corrupt")
                    except OSError:
                        pass  # Can't quarantine, skip
                    continue


def print_help():
    """Print CLI help message."""
    print("AVCPM Agent Authentication System")
    print("Usage:")
    print("  python avcpm_auth.py challenge <agent_id>      - Generate a challenge")
    print("  python avcpm_auth.py respond <agent_id>        - Sign challenge response")
    print("  python avcpm_auth.py verify <agent_id> <sig>   - Verify and create session")
    print("  python avcpm_auth.py check <agent_id>            - Check if authenticated")
    print("  python avcpm_auth.py logout <agent_id>         - End session")
    print("  python avcpm_auth.py list                      - List active sessions")
    print("  python avcpm_auth.py cleanup                     - Clean up expired sessions")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "challenge":
        if len(sys.argv) < 3:
            print("Error: challenge requires agent_id")
            sys.exit(1)
        agent_id = sys.argv[2]
        challenge = create_challenge(agent_id)
        print(f"Challenge for {agent_id}: {challenge}")
    
    elif cmd == "respond":
        if len(sys.argv) < 3:
            print("Error: respond requires agent_id")
            sys.exit(1)
        agent_id = sys.argv[2]
        challenge = get_challenge(agent_id)
        if not challenge:
            print(f"No active challenge for {agent_id}. Generate one first.")
            sys.exit(1)
        signature = sign_challenge_response(challenge, agent_id)
        print(f"Challenge: {challenge}")
        print(f"Signature: {signature}")
    
    elif cmd == "verify":
        if len(sys.argv) < 4:
            print("Error: verify requires agent_id and signature")
            sys.exit(1)
        agent_id = sys.argv[2]
        signature = sys.argv[3]
        success, result = authenticate_agent(agent_id, signature)
        if success:
            print(f"Authentication successful!")
            print(f"Session token: {result['session_token']}")
            print(f"Expires at: {result['expires_at']}")
        else:
            print(f"Authentication failed: {result}")
            sys.exit(1)
    
    elif cmd == "check":
        if len(sys.argv) < 3:
            print("Error: check requires agent_id")
            sys.exit(1)
        agent_id = sys.argv[2]
        session = get_session(agent_id)
        if session:
            print(f"Agent {agent_id} is authenticated")
            print(f"Session expires at: {session['expires_at']}")
        else:
            print(f"Agent {agent_id} is not authenticated")
            sys.exit(1)
    
    elif cmd == "logout":
        if len(sys.argv) < 3:
            print("Error: logout requires agent_id")
            sys.exit(1)
        agent_id = sys.argv[2]
        if delete_session(agent_id):
            print(f"Session for {agent_id} ended")
        else:
            print(f"No active session for {agent_id}")
    
    elif cmd == "list":
        sessions = list_active_sessions()
        if not sessions:
            print("No active sessions")
        else:
            print(f"{'Agent ID':<15} {'Created':<25} {'Expires':<25} {'Last Used'}")
            print("-" * 100)
            for session in sessions:
                agent_id = session.get("agent_id", "unknown")
                created = session.get("created_at", "unknown")[:19]
                expires = session.get("expires_at", "unknown")[:19]
                last_used = session.get("last_used", "unknown")[:19]
                print(f"{agent_id:<15} {created:<25} {expires:<25} {last_used}")
    
    elif cmd == "cleanup":
        cleanup_expired_sessions()
        print("Expired sessions cleaned up")
    
    else:
        print(f"Unknown command: {cmd}")
        print_help()
        sys.exit(1)