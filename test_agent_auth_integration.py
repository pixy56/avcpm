#!/usr/bin/env python3
"""
Test suite for AVCPM Agent Authentication Integration.

This module tests the authentication protections integrated into:
- avcpm_commit.py - commit operations now require agent authentication
- avcpm_task.py - task operations now verify agent identity
- avcpm_cli.py - CLI now supports agent authentication commands

Security features tested:
1. Agent identity verification points
2. Cryptographic signature verification
3. Agent ID matching signing keys
4. Session validation on operations
5. Impersonation attack prevention
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open
import json

# Ensure we can import from the workspace
sys.path.insert(0, '/home/user/.openclaw/workspace')

# Mock the cryptography module to avoid import errors
sys.modules['cryptography'] = MagicMock()
sys.modules['cryptography.hazmat'] = MagicMock()
sys.modules['cryptography.hazmat.primitives'] = MagicMock()
sys.modules['cryptography.hazmat.primitives.hashes'] = MagicMock()
sys.modules['cryptography.hazmat.primitives.serialization'] = MagicMock()
sys.modules['cryptography.hazmat.primitives.asymmetric'] = MagicMock()
sys.modules['cryptography.hazmat.primitives.asymmetric.rsa'] = MagicMock()
sys.modules['cryptography.hazmat.primitives.asymmetric.padding'] = MagicMock()
sys.modules['cryptography.exceptions'] = MagicMock()
sys.modules['cryptography.hazmat.primitives.ciphers'] = MagicMock()
sys.modules['cryptography.hazmat.primitives.ciphers.algorithms'] = MagicMock()
sys.modules['cryptography.hazmat.primitives.ciphers.modes'] = MagicMock()
sys.modules['cryptography.hazmat.primitives.kdf'] = MagicMock()
sys.modules['cryptography.hazmat.primitives.kdf.pbkdf2'] = MagicMock()
sys.modules['cryptography.hazmat.backends'] = MagicMock()


class TestAgentAuthenticationIntegration(unittest.TestCase):
    """Test the integrated agent authentication system."""
    
    def setUp(self):
        """Set up test environment."""
        self.base_dir = ".avcpm_test"
        self.agent_id = "agent123"
        self.task_id = "TASK-001"
        
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)
    
    # ========================================================================
    # Test 1: verify_agent_identity function in avcpm_commit.py
    # ========================================================================
    
    @patch('avcpm_commit.get_agent')
    @patch('avcpm_commit.get_public_key')
    def test_verify_agent_identity_success(self, mock_get_public_key, mock_get_agent):
        """Test successful agent identity verification."""
        # Import after mocking
        from avcpm_commit import verify_agent_identity
        
        # Setup mocks
        mock_get_agent.return_value = {
            'agent_id': 'agent123',
            'name': 'Test Agent',
            'email': 'test@example.com'
        }
        mock_get_public_key.return_value = b'some_public_key_data'
        
        # Test successful verification
        is_valid, error_msg = verify_agent_identity('agent123', self.base_dir)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error_msg)
        mock_get_agent.assert_called_once_with('agent123', self.base_dir)
        mock_get_public_key.assert_called_once_with('agent123', self.base_dir)
    
    @patch('avcpm_commit.get_agent')
    def test_verify_agent_identity_agent_not_found(self, mock_get_agent):
        """Test verification when agent doesn't exist."""
        from avcpm_commit import verify_agent_identity
        
        mock_get_agent.return_value = None
        
        is_valid, error_msg = verify_agent_identity('nonexistent', self.base_dir)
        
        self.assertFalse(is_valid)
        self.assertIn("not found in registry", error_msg)
    
    @patch('avcpm_commit.get_agent')
    @patch('avcpm_commit.get_public_key')
    def test_verify_agent_identity_no_public_key(self, mock_get_public_key, mock_get_agent):
        """Test verification when public key is missing."""
        from avcpm_commit import verify_agent_identity
        
        mock_get_agent.return_value = {
            'agent_id': 'agent123',
            'name': 'Test Agent'
        }
        mock_get_public_key.return_value = None
        
        is_valid, error_msg = verify_agent_identity('agent123', self.base_dir)
        
        self.assertFalse(is_valid)
        self.assertIn("Public key not found", error_msg)
    
    @patch('avcpm_commit.get_agent')
    def test_verify_agent_identity_id_mismatch(self, mock_get_agent):
        """Test verification when agent ID doesn't match registry."""
        from avcpm_commit import verify_agent_identity
        
        # Simulate corrupted registry data
        mock_get_agent.return_value = {
            'agent_id': 'different_id',  # Mismatch!
            'name': 'Test Agent'
        }
        
        is_valid, error_msg = verify_agent_identity('agent123', self.base_dir)
        
        self.assertFalse(is_valid)
        self.assertIn("Agent ID mismatch", error_msg)
    
    # ========================================================================
    # Test 2: verify_task_permission function in avcpm_task.py
    # ========================================================================
    
    @patch('avcpm_task.get_authenticated_agent_from_env')
    @patch('avcpm_task.validate_session')
    @patch('avcpm_task.get_agent')
    @patch('avcpm_task.get_public_key')
    def test_verify_task_permission_success(self, mock_get_public_key, mock_get_agent,
                                             mock_validate_session, mock_get_auth):
        """Test successful task permission verification."""
        from avcpm_task import verify_task_permission
        
        # Setup: agent is authenticated
        mock_get_auth.return_value = ('agent123', 'valid_session_token')
        mock_validate_session.return_value = True
        mock_get_agent.return_value = {
            'agent_id': 'agent123',
            'name': 'Test Agent'
        }
        mock_get_public_key.return_value = b'public_key_data'
        
        permitted, error_msg = verify_task_permission('TASK-001', 'agent123', self.base_dir)
        
        self.assertTrue(permitted)
        self.assertIsNone(error_msg)
    
    @patch('avcpm_task.get_authenticated_agent_from_env')
    def test_verify_task_permission_not_authenticated(self, mock_get_auth):
        """Test permission denied when agent not authenticated."""
        from avcpm_task import verify_task_permission
        
        # Setup: no authenticated agent
        mock_get_auth.return_value = (None, None)
        
        permitted, error_msg = verify_task_permission('TASK-001', 'agent123', self.base_dir)
        
        self.assertFalse(permitted)
        self.assertIn("Agent authentication required", error_msg)
    
    @patch('avcpm_task.get_authenticated_agent_from_env')
    def test_verify_task_permission_agent_mismatch(self, mock_get_auth):
        """Test permission denied when claimed agent doesn't match authenticated agent."""
        from avcpm_task import verify_task_permission
        
        # Setup: authenticated as agent123 but claiming to be agent456
        mock_get_auth.return_value = ('agent123', 'valid_token')
        
        permitted, error_msg = verify_task_permission('TASK-001', 'agent456', self.base_dir)
        
        self.assertFalse(permitted)
        self.assertIn("Agent ID mismatch", error_msg)
        self.assertIn("impersonation", error_msg.lower())
    
    @patch('avcpm_task.get_authenticated_agent_from_env')
    @patch('avcpm_task.validate_session')
    def test_verify_task_permission_invalid_session(self, mock_validate_session, mock_get_auth):
        """Test permission denied when session is invalid."""
        from avcpm_task import verify_task_permission
        
        mock_get_auth.return_value = ('agent123', 'invalid_token')
        mock_validate_session.return_value = False
        
        permitted, error_msg = verify_task_permission('TASK-001', 'agent123', self.base_dir)
        
        self.assertFalse(permitted)
        self.assertIn("Session invalid or expired", error_msg)
    
    def test_verify_task_permission_auth_disabled(self):
        """Test that auth check can be disabled."""
        from avcpm_task import verify_task_permission
        
        permitted, error_msg = verify_task_permission('TASK-001', 'agent123', self.base_dir, require_auth=False)
        
        self.assertTrue(permitted)
        self.assertIsNone(error_msg)
    
    # ========================================================================
    # Test 3: validate_agent_identity function in avcpm_cli.py
    # ========================================================================
    
    @patch('avcpm_cli.get_agent')
    @patch('avcpm_cli.get_public_key')
    def test_cli_validate_agent_identity_success(self, mock_get_public_key, mock_get_agent):
        """Test CLI agent identity validation success."""
        from avcpm_cli import validate_agent_identity
        
        mock_get_agent.return_value = {
            'agent_id': 'agent123',
            'name': 'Test Agent'
        }
        mock_get_public_key.return_value = b'public_key'
        
        is_valid, error_msg = validate_agent_identity('agent123', self.base_dir)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error_msg)
    
    @patch('avcpm_cli.get_agent')
    def test_cli_validate_agent_identity_not_found(self, mock_get_agent):
        """Test CLI agent identity validation when agent not found."""
        from avcpm_cli import validate_agent_identity
        
        mock_get_agent.return_value = None
        
        is_valid, error_msg = validate_agent_identity('agent123', self.base_dir)
        
        self.assertFalse(is_valid)
        self.assertIn("not found in registry", error_msg)
    
    @patch('avcpm_cli.get_agent')
    @patch('avcpm_cli.get_public_key')
    def test_cli_validate_agent_identity_no_key(self, mock_get_public_key, mock_get_agent):
        """Test CLI agent identity validation when public key missing."""
        from avcpm_cli import validate_agent_identity
        
        mock_get_agent.return_value = {
            'agent_id': 'agent123',
            'name': 'Test Agent'
        }
        mock_get_public_key.return_value = None
        
        is_valid, error_msg = validate_agent_identity('agent123', self.base_dir)
        
        self.assertFalse(is_valid)
        self.assertIn("Public key not found", error_msg)
    
    # ========================================================================
    # Test 4: Security features integration
    # ========================================================================
    
    def test_commit_function_signature(self):
        """Test that commit function accepts auth parameters."""
        import inspect
        from avcpm_commit import commit
        
        sig = inspect.signature(commit)
        params = list(sig.parameters.keys())
        
        self.assertIn('require_authentication', params)
        self.assertIn('session_token', params)
    
    def test_create_task_function_signature(self):
        """Test that create_task function accepts auth parameters."""
        import inspect
        from avcpm_task import create_task
        
        sig = inspect.signature(create_task)
        params = list(sig.parameters.keys())
        
        # These should exist for auth integration
        self.assertIn('agent_id', params)
        self.assertIn('require_auth', params)


class TestAuthenticationFlow(unittest.TestCase):
    """Test the complete authentication flow."""
    
    @patch.dict(os.environ, {'AVCPM_AGENT_ID': 'test_agent', 'AVCPM_SESSION_TOKEN': 'test_token'})
    @patch('avcpm_task.validate_session')
    @patch('avcpm_task.get_agent')
    @patch('avcpm_task.get_public_key')
    def test_environment_based_authentication(self, mock_get_public_key, mock_get_agent, mock_validate_session):
        """Test authentication using environment variables."""
        from avcpm_task import get_authenticated_agent_from_env, verify_task_permission
        
        # Mock the session validation
        mock_validate_session.return_value = True
        mock_get_agent.return_value = {
            'agent_id': 'test_agent',
            'name': 'Test Agent'
        }
        mock_get_public_key.return_value = b'public_key'
        
        # Get agent from environment
        agent_id, token = get_authenticated_agent_from_env('.avcpm')
        
        self.assertEqual(agent_id, 'test_agent')
        self.assertEqual(token, 'test_token')
    
    def test_session_token_from_env(self):
        """Test getting session token from environment."""
        from unittest.mock import patch
        
        with patch.dict(os.environ, {'AVCPM_SESSION_TOKEN': 'my_session_token'}):
            from avcpm_auth import get_session_token_from_env
            token = get_session_token_from_env()
            self.assertEqual(token, 'my_session_token')
    
    def test_session_token_not_set(self):
        """Test when session token is not in environment."""
        from unittest.mock import patch
        
        with patch.dict(os.environ, {}, clear=True):
            from avcpm_auth import get_session_token_from_env
            token = get_session_token_from_env()
            self.assertIsNone(token)


class TestImpersonationPrevention(unittest.TestCase):
    """Test protections against agent impersonation attacks."""
    
    @patch('avcpm_task.get_authenticated_agent_from_env')
    def test_cannot_impersonate_without_session(self, mock_get_auth):
        """Test that impersonation fails without valid session."""
        from avcpm_task import verify_task_permission
        
        # Attacker tries to impersonate agent123 without authentication
        mock_get_auth.return_value = (None, None)
        
        permitted, error = verify_task_permission('TASK-001', 'agent123', '.avcpm')
        
        self.assertFalse(permitted)
        self.assertIn("authentication required", error.lower())
    
    @patch('avcpm_task.get_authenticated_agent_from_env')
    def test_cannot_impersonate_different_agent(self, mock_get_auth):
        """Test that authenticated agent cannot impersonate another."""
        from avcpm_task import verify_task_permission
        
        # Attacker is authenticated as attacker_agent but claims to be victim_agent
        mock_get_auth.return_value = ('attacker_agent', 'valid_token')
        
        permitted, error = verify_task_permission('TASK-001', 'victim_agent', '.avcpm')
        
        self.assertFalse(permitted)
        self.assertIn("mismatch", error.lower())


def run_tests():
    """Run the test suite."""
    # Create a test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAgentAuthenticationIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestAuthenticationFlow))
    suite.addTests(loader.loadTestsFromTestCase(TestImpersonationPrevention))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    print("=" * 70)
    print("AVCPM Agent Authentication Integration Tests")
    print("=" * 70)
    print()
    
    result = run_tests()
    
    print()
    print("=" * 70)
    if result.wasSuccessful():
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 70)
    
    sys.exit(0 if result.wasSuccessful() else 1)
