#!/usr/bin/env python3
"""
Tests for AVCPM Status Dashboard
"""

import os
import sys
import json
import tempfile
import shutil
import unittest
from datetime import datetime
from io import StringIO
from unittest.mock import patch

# Import the module under test
import avcpm_status as status


class TestAVCPMStatus(unittest.TestCase):
    """Test suite for AVCPM Status Dashboard."""
    
    def setUp(self):
        """Set up test environment with temporary directories."""
        self.test_dir = tempfile.mkdtemp()
        self.original_base_dir = status.BASE_DIR
        
        # Update module paths to use test directory
        status.BASE_DIR = os.path.join(self.test_dir, '.avcpm')
        status.TASKS_DIR = os.path.join(status.BASE_DIR, 'tasks')
        status.LEDGER_DIR = os.path.join(status.BASE_DIR, 'ledger')
        status.STAGING_DIR = os.path.join(status.BASE_DIR, 'staging')
        status.REVIEWS_DIR = os.path.join(status.BASE_DIR, 'reviews')
        
        # Create directory structure
        for col in status.COLUMNS:
            os.makedirs(os.path.join(status.TASKS_DIR, col), exist_ok=True)
        os.makedirs(status.LEDGER_DIR, exist_ok=True)
        os.makedirs(status.STAGING_DIR, exist_ok=True)
        os.makedirs(status.REVIEWS_DIR, exist_ok=True)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
        # Restore original paths
        status.BASE_DIR = self.original_base_dir
        status.TASKS_DIR = os.path.join(self.original_base_dir, 'tasks')
        status.LEDGER_DIR = os.path.join(self.original_base_dir, 'ledger')
        status.STAGING_DIR = os.path.join(self.original_base_dir, 'staging')
        status.REVIEWS_DIR = os.path.join(self.original_base_dir, 'reviews')
    
    def create_task(self, task_id, status_col, **kwargs):
        """Helper to create a task file."""
        task_data = {
            'id': task_id,
            'title': kwargs.get('title', f'Task {task_id}'),
            'description': kwargs.get('description', f'Description for {task_id}'),
            'assignee': kwargs.get('assignee', 'test-user'),
            'priority': kwargs.get('priority', 'medium'),
            'status_history': [
                {'status': status_col, 'timestamp': datetime.now().isoformat()}
            ]
        }
        
        filepath = os.path.join(status.TASKS_DIR, status_col, f'{task_id}.json')
        with open(filepath, 'w') as f:
            json.dump(task_data, f)
        
        return task_data
    
    def create_ledger_entry(self, commit_id, **kwargs):
        """Helper to create a ledger entry."""
        entry = {
            'commit_id': commit_id,
            'timestamp': kwargs.get('timestamp', datetime.now().isoformat()),
            'agent_id': kwargs.get('agent_id', 'TestAgent'),
            'task_id': kwargs.get('task_id', 'TASK-1'),
            'rationale': kwargs.get('rationale', 'Test commit'),
            'changes': kwargs.get('changes', [])
        }
        
        filepath = os.path.join(status.LEDGER_DIR, f'{commit_id}.json')
        with open(filepath, 'w') as f:
            json.dump(entry, f)
        
        return entry
    
    def create_staging_file(self, filename, content='test content'):
        """Helper to create a staging file."""
        filepath = os.path.join(status.STAGING_DIR, filename)
        with open(filepath, 'w') as f:
            f.write(content)
        return filepath
    
    # ==================== Task Tests ====================
    
    def test_get_tasks_by_status_empty(self):
        """Test getting tasks when no tasks exist."""
        tasks = status.get_tasks_by_status()
        for col in status.COLUMNS:
            self.assertEqual(tasks[col], [])
    
    def test_get_tasks_by_status_with_tasks(self):
        """Test getting tasks from multiple columns."""
        self.create_task('TASK-1', 'todo', title='Test Task 1')
        self.create_task('TASK-2', 'in-progress', title='Test Task 2')
        self.create_task('TASK-3', 'done', title='Test Task 3')
        
        tasks = status.get_tasks_by_status()
        
        self.assertEqual(len(tasks['todo']), 1)
        self.assertEqual(len(tasks['in-progress']), 1)
        self.assertEqual(len(tasks['done']), 1)
        self.assertEqual(len(tasks['review']), 0)
        
        self.assertEqual(tasks['todo'][0]['id'], 'TASK-1')
        self.assertEqual(tasks['in-progress'][0]['id'], 'TASK-2')
        self.assertEqual(tasks['done'][0]['id'], 'TASK-3')
    
    def test_generate_tasks_report(self):
        """Test task report generation."""
        self.create_task('TASK-1', 'todo')
        self.create_task('TASK-2', 'todo')
        self.create_task('TASK-3', 'in-progress')
        
        report = status.generate_tasks_report()
        
        self.assertEqual(report['summary']['todo'], 2)
        self.assertEqual(report['summary']['in-progress'], 1)
        self.assertEqual(report['summary']['done'], 0)
        
        self.assertEqual(len(report['columns']['todo']), 2)
    
    # ==================== Ledger Tests ====================
    
    def test_get_ledger_entries_empty(self):
        """Test getting ledger entries when none exist."""
        entries = status.get_ledger_entries()
        self.assertEqual(entries, [])
    
    def test_get_ledger_entries_sorted(self):
        """Test that ledger entries are sorted by timestamp."""
        self.create_ledger_entry('20230101000000', timestamp='2023-01-01T00:00:00')
        self.create_ledger_entry('20230103000000', timestamp='2023-01-03T00:00:00')
        self.create_ledger_entry('20230102000000', timestamp='2023-01-02T00:00:00')
        
        entries = status.get_ledger_entries(limit=10)
        
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0]['commit_id'], '20230103000000')  # Most recent
        self.assertEqual(entries[1]['commit_id'], '20230102000000')
        self.assertEqual(entries[2]['commit_id'], '20230101000000')  # Oldest
    
    def test_get_ledger_entries_limit(self):
        """Test that ledger entry limit is respected."""
        for i in range(15):
            self.create_ledger_entry(f'202301{i:02d}000000', timestamp=f'2023-01-{i+1:02d}T00:00:00')
        
        entries = status.get_ledger_entries(limit=10)
        self.assertEqual(len(entries), 10)
    
    def test_generate_ledger_report(self):
        """Test ledger report generation."""
        self.create_ledger_entry('20230101000000', agent_id='Agent1', task_id='TASK-1')
        self.create_ledger_entry('20230102000000', agent_id='Agent2', task_id='TASK-2')
        
        report = status.generate_ledger_report()
        
        self.assertEqual(len(report['entries']), 2)
        self.assertEqual(report['entries'][0]['agent_id'], 'Agent2')
    
    # ==================== Staging Tests ====================
    
    def test_get_staging_files_empty(self):
        """Test getting staging files when none exist."""
        files = status.get_staging_files()
        self.assertEqual(files, [])
    
    def test_get_staging_files_with_files(self):
        """Test getting staging files."""
        self.create_staging_file('file1.txt', 'content 1')
        self.create_staging_file('file2.txt', 'content 2' * 1000)  # Larger file
        
        files = status.get_staging_files()
        
        self.assertEqual(len(files), 2)
        
        names = {f['name'] for f in files}
        self.assertEqual(names, {'file1.txt', 'file2.txt'})
        
        # Check that size is recorded
        for f in files:
            self.assertIn('size', f)
            self.assertIn('modified', f)
    
    def test_generate_staging_report(self):
        """Test staging report generation."""
        self.create_staging_file('test.txt')
        
        report = status.generate_staging_report()
        
        self.assertEqual(len(report['files']), 1)
        self.assertEqual(report['files'][0]['name'], 'test.txt')
    
    # ==================== Health Tests ====================
    
    def test_check_system_health_healthy(self):
        """Test health check with no issues."""
        self.create_task('TASK-1', 'todo')
        self.create_ledger_entry('20230101000000', task_id='TASK-1')
        
        health = status.check_system_health()
        
        self.assertTrue(health['healthy'])
        self.assertEqual(health['issues'], [])
        self.assertEqual(health['warnings'], [])
    
    def test_check_system_health_orphaned_task(self):
        """Test health check detects orphaned task in ledger."""
        self.create_ledger_entry('20230101000000', task_id='NONEXISTENT')
        
        health = status.check_system_health()
        
        self.assertFalse(health['healthy'])
        self.assertEqual(len(health['issues']), 1)
        self.assertIn('NONEXISTENT', health['issues'][0])
    
    def test_check_system_health_untracked_staging(self):
        """Test health check detects untracked staging files."""
        self.create_staging_file('untracked.txt')
        
        health = status.check_system_health()
        
        self.assertTrue(health['healthy'])  # Warnings don't make it unhealthy
        self.assertEqual(len(health['warnings']), 1)
        self.assertIn('untracked', health['warnings'][0])
    
    # ==================== Format Tests ====================
    
    def test_format_task_row(self):
        """Test task formatting."""
        task = {
            'id': 'TASK-1',
            'title': 'Test Task',
            'assignee': 'user',
            'priority': 'high'
        }
        
        row = status.format_task_row(task)
        
        self.assertEqual(row[0], 'TASK-1')
        self.assertEqual(row[1], 'Test Task')
        self.assertEqual(row[2], 'user')
        self.assertEqual(row[3], 'high')
    
    def test_format_task_row_no_title(self):
        """Test task formatting falls back to description."""
        task = {
            'id': 'TASK-1',
            'description': 'Task Description Here',
            'assignee': 'user'
        }
        
        row = status.format_task_row(task)
        
        self.assertEqual(row[1], 'Task Description Here')
    
    def test_format_ledger_row(self):
        """Test ledger entry formatting."""
        entry = {
            'commit_id': '20230101000000',
            'timestamp': '2023-01-01T12:30:45.123456',
            'agent_id': 'TestAgent',
            'task_id': 'TASK-1',
            'changes': [{'file': 'test.py'}]
        }
        
        row = status.format_ledger_row(entry)
        
        self.assertEqual(row[0], '20230101000000')
        self.assertEqual(row[1], '2023-01-01T12:30')  # Truncated
        self.assertEqual(row[2], 'TestAgent')
        self.assertEqual(row[3], 'TASK-1')
        self.assertEqual(row[4], '1')  # File count
    
    def test_format_staging_row(self):
        """Test staging file formatting."""
        file_info = {
            'name': 'test.txt',
            'size': 1024,
            'modified': '2023-01-01T12:00:00'
        }
        
        row = status.format_staging_row(file_info)
        
        self.assertEqual(row[0], 'test.txt')
        self.assertEqual(row[1], '1KB')  # Converted
    
    def test_format_staging_row_small_file(self):
        """Test staging file formatting for small files."""
        file_info = {
            'name': 'tiny.txt',
            'size': 100,
            'modified': '2023-01-01T12:00:00'
        }
        
        row = status.format_staging_row(file_info)
        
        self.assertEqual(row[1], '100B')  # Bytes, not KB
    
    # ==================== Display Tests ====================
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_print_table(self, mock_stdout):
        """Test table printing."""
        status.print_table('Test Title', ['Col1', 'Col2'], [['A', 'B'], ['C', 'D']])
        
        output = mock_stdout.getvalue()
        self.assertIn('Test Title', output)
        self.assertIn('Col1', output)
        self.assertIn('A', output)
        self.assertIn('D', output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_print_table_empty(self, mock_stdout):
        """Test table printing with empty data."""
        status.print_table('Empty Table', ['Col1', 'Col2'], [])
        
        output = mock_stdout.getvalue()
        self.assertIn('(empty)', output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_display_health_report_healthy(self, mock_stdout):
        """Test healthy status display."""
        report = {'healthy': True, 'issues': [], 'warnings': []}
        status.display_health_report(report)
        
        output = mock_stdout.getvalue()
        self.assertIn('All systems operational', output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_display_health_report_issues(self, mock_stdout):
        """Test health display with issues."""
        report = {
            'healthy': False,
            'issues': ['Error 1', 'Error 2'],
            'warnings': ['Warning 1']
        }
        status.display_health_report(report)
        
        output = mock_stdout.getvalue()
        self.assertIn('Error 1', output)
        self.assertIn('Warning 1', output)
    
    # ==================== JSON Output Tests ====================
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_output_json(self, mock_stdout):
        """Test JSON output."""
        data = {'key': 'value', 'number': 42}
        status.output_json(data)
        
        output = mock_stdout.getvalue()
        parsed = json.loads(output)
        self.assertEqual(parsed['key'], 'value')
        self.assertEqual(parsed['number'], 42)
    
    # ==================== Integration Tests ====================
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_default_output(self, mock_stdout):
        """Test main function with default output."""
        self.create_task('TASK-1', 'todo', title='Integration Test')
        self.create_ledger_entry('20230101000000')
        self.create_staging_file('test.txt')
        
        with patch.object(sys, 'argv', ['avcpm_status.py']):
            status.main()
        
        output = mock_stdout.getvalue()
        self.assertIn('TASK BOARD', output)
        self.assertIn('LEDGER ACTIVITY', output)
        self.assertIn('STAGING STATUS', output)
        self.assertIn('SYSTEM HEALTH', output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_tasks_only(self, mock_stdout):
        """Test main function with --tasks flag."""
        self.create_task('TASK-1', 'todo')
        
        with patch.object(sys, 'argv', ['avcpm_status.py', '--tasks']):
            status.main()
        
        output = mock_stdout.getvalue()
        self.assertIn('TASK BOARD', output)
        self.assertNotIn('LEDGER ACTIVITY', output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_json_output(self, mock_stdout):
        """Test main function with --json flag."""
        self.create_task('TASK-1', 'todo')
        
        with patch.object(sys, 'argv', ['avcpm_status.py', '--json']):
            status.main()
        
        output = mock_stdout.getvalue()
        # Should be valid JSON
        parsed = json.loads(output)
        self.assertIn('tasks', parsed)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_ledger_only(self, mock_stdout):
        """Test main function with --ledger flag."""
        self.create_ledger_entry('20230101000000')
        
        with patch.object(sys, 'argv', ['avcpm_status.py', '--ledger']):
            status.main()
        
        output = mock_stdout.getvalue()
        self.assertIn('LEDGER ACTIVITY', output)
        self.assertNotIn('TASK BOARD', output)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_staging_only(self, mock_stdout):
        """Test main function with --staging flag."""
        self.create_staging_file('test.txt')
        
        with patch.object(sys, 'argv', ['avcpm_status.py', '--staging']):
            status.main()
        
        output = mock_stdout.getvalue()
        self.assertIn('STAGING STATUS', output)
        self.assertNotIn('LEDGER ACTIVITY', output)


def run_tests():
    """Run the test suite."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAVCPMStatus)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
