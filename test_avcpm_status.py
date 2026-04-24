#!/usr/bin/env python3
"""
Tests for AVCPM Status Dashboard

Converted from unittest.TestCase to pytest fixtures (M-T5).
Run with: pytest test_avcpm_status.py -v
"""

import os
import sys
import json
import shutil
import tempfile
from datetime import datetime
from io import StringIO
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import avcpm_status as status


@pytest.fixture(autouse=True)
def setup_teardown(tmp_path):
    """Set up test environment with temporary directories; restore after."""
    test_dir = str(tmp_path)
    original_base_dir = status.BASE_DIR

    # Update module paths to use test directory
    status.BASE_DIR = os.path.join(test_dir, '.avcpm')
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

    yield

    # Restore original paths
    status.BASE_DIR = original_base_dir
    status.TASKS_DIR = os.path.join(original_base_dir, 'tasks')
    status.LEDGER_DIR = os.path.join(original_base_dir, 'ledger')
    status.STAGING_DIR = os.path.join(original_base_dir, 'staging')
    status.REVIEWS_DIR = os.path.join(original_base_dir, 'reviews')


def create_task(task_id, status_col, **kwargs):
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


def create_ledger_entry(commit_id, **kwargs):
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


def create_staging_file(filename, content='test content'):
    """Helper to create a staging file."""
    filepath = os.path.join(status.STAGING_DIR, filename)
    with open(filepath, 'w') as f:
        f.write(content)
    return filepath


# ==================== Task Tests ====================

class TestTasksByStatus:
    def test_get_tasks_by_status_empty(self):
        """Test getting tasks when no tasks exist."""
        tasks = status.get_tasks_by_status()
        for col in status.COLUMNS:
            assert tasks[col] == []

    def test_get_tasks_by_status_with_tasks(self):
        """Test getting tasks from multiple columns."""
        create_task('TASK-1', 'todo', title='Test Task 1')
        create_task('TASK-2', 'in-progress', title='Test Task 2')
        create_task('TASK-3', 'done', title='Test Task 3')

        tasks = status.get_tasks_by_status()

        assert len(tasks['todo']) == 1
        assert len(tasks['in-progress']) == 1
        assert len(tasks['done']) == 1
        assert len(tasks['review']) == 0

        assert tasks['todo'][0]['id'] == 'TASK-1'
        assert tasks['in-progress'][0]['id'] == 'TASK-2'
        assert tasks['done'][0]['id'] == 'TASK-3'

    def test_generate_tasks_report(self):
        """Test task report generation."""
        create_task('TASK-1', 'todo')
        create_task('TASK-2', 'todo')
        create_task('TASK-3', 'in-progress')

        report = status.generate_tasks_report()

        assert report['summary']['todo'] == 2
        assert report['summary']['in-progress'] == 1
        assert report['summary']['done'] == 0
        assert len(report['columns']['todo']) == 2


# ==================== Ledger Tests ====================

class TestLedgerEntries:
    def test_get_ledger_entries_empty(self):
        """Test getting ledger entries when none exist."""
        entries = status.get_ledger_entries()
        assert entries == []

    def test_get_ledger_entries_sorted(self):
        """Test that ledger entries are sorted by timestamp."""
        create_ledger_entry('20230101000000', timestamp='2023-01-01T00:00:00')
        create_ledger_entry('20230103000000', timestamp='2023-01-03T00:00:00')
        create_ledger_entry('20230102000000', timestamp='2023-01-02T00:00:00')

        entries = status.get_ledger_entries(limit=10)

        assert len(entries) == 3
        assert entries[0]['commit_id'] == '20230103000000'
        assert entries[1]['commit_id'] == '20230102000000'
        assert entries[2]['commit_id'] == '20230101000000'

    def test_get_ledger_entries_limit(self):
        """Test that ledger entry limit is respected."""
        for i in range(15):
            create_ledger_entry(f'202301{i:02d}000000', timestamp=f'2023-01-{i+1:02d}T00:00:00')

        entries = status.get_ledger_entries(limit=10)
        assert len(entries) == 10

    def test_generate_ledger_report(self):
        """Test ledger report generation."""
        create_ledger_entry('20230101000000', agent_id='Agent1', task_id='TASK-1')
        create_ledger_entry('20230102000000', agent_id='Agent2', task_id='TASK-2')

        report = status.generate_ledger_report()

        assert len(report['entries']) == 2
        assert report['entries'][0]['agent_id'] == 'Agent2'


# ==================== Staging Tests ====================

class TestStagingFiles:
    def test_get_staging_files_empty(self):
        """Test getting staging files when none exist."""
        files = status.get_staging_files()
        assert files == []

    def test_get_staging_files_with_files(self):
        """Test getting staging files."""
        create_staging_file('file1.txt', 'content 1')
        create_staging_file('file2.txt', 'content 2' * 1000)

        files = status.get_staging_files()

        assert len(files) == 2
        names = {f['name'] for f in files}
        assert names == {'file1.txt', 'file2.txt'}

        for f in files:
            assert 'size' in f
            assert 'modified' in f

    def test_generate_staging_report(self):
        """Test staging report generation."""
        create_staging_file('test.txt')

        report = status.generate_staging_report()

        assert len(report['files']) == 1
        assert report['files'][0]['name'] == 'test.txt'


# ==================== Health Tests ====================

class TestSystemHealth:
    def test_check_system_health_healthy(self):
        """Test health check with no issues."""
        create_task('TASK-1', 'todo')
        create_ledger_entry('20230101000000', task_id='TASK-1')

        health = status.check_system_health()

        assert health['healthy'] is True
        assert health['issues'] == []
        assert health['warnings'] == []

    def test_check_system_health_orphaned_task(self):
        """Test health check detects orphaned task in ledger."""
        create_ledger_entry('20230101000000', task_id='NONEXISTENT')

        health = status.check_system_health()

        assert health['healthy'] is False
        assert len(health['issues']) == 1
        assert 'NONEXISTENT' in health['issues'][0]

    def test_check_system_health_untracked_staging(self):
        """Test health check detects untracked staging files."""
        create_staging_file('untracked.txt')

        health = status.check_system_health()

        assert health['healthy'] is True  # Warnings don't make it unhealthy
        assert len(health['warnings']) == 1
        assert 'untracked' in health['warnings'][0]


# ==================== Format Tests ====================

class TestFormatting:
    def test_format_task_row(self):
        """Test task formatting."""
        task = {
            'id': 'TASK-1',
            'title': 'Test Task',
            'assignee': 'user',
            'priority': 'high'
        }
        row = status.format_task_row(task)
        assert row[0] == 'TASK-1'
        assert row[1] == 'Test Task'
        assert row[2] == 'user'
        assert row[3] == 'high'

    def test_format_task_row_no_title(self):
        """Test task formatting falls back to description."""
        task = {
            'id': 'TASK-1',
            'description': 'Task Description Here',
            'assignee': 'user'
        }
        row = status.format_task_row(task)
        assert row[1] == 'Task Description Here'

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
        assert row[0] == '20230101000000'
        assert row[1] == '2023-01-01T12:30'
        assert row[2] == 'TestAgent'
        assert row[3] == 'TASK-1'
        assert row[4] == '1'

    def test_format_staging_row(self):
        """Test staging file formatting."""
        file_info = {
            'name': 'test.txt',
            'size': 1024,
            'modified': '2023-01-01T12:00:00'
        }
        row = status.format_staging_row(file_info)
        assert row[0] == 'test.txt'
        assert row[1] == '1KB'

    def test_format_staging_row_small_file(self):
        """Test staging file formatting for small files."""
        file_info = {
            'name': 'tiny.txt',
            'size': 100,
            'modified': '2023-01-01T12:00:00'
        }
        row = status.format_staging_row(file_info)
        assert row[1] == '100B'


# ==================== Display Tests ====================

class TestDisplay:
    def test_print_table(self, capsys):
        """Test table printing."""
        status.print_table('Test Title', ['Col1', 'Col2'], [['A', 'B'], ['C', 'D']])
        output = capsys.readouterr().out
        assert 'Test Title' in output
        assert 'Col1' in output
        assert 'A' in output
        assert 'D' in output

    def test_print_table_empty(self, capsys):
        """Test table printing with empty data."""
        status.print_table('Empty Table', ['Col1', 'Col2'], [])
        output = capsys.readouterr().out
        assert '(empty)' in output

    def test_display_health_report_healthy(self, capsys):
        """Test healthy status display."""
        report = {'healthy': True, 'issues': [], 'warnings': []}
        status.display_health_report(report)
        output = capsys.readouterr().out
        assert 'All systems operational' in output

    def test_display_health_report_issues(self, capsys):
        """Test health display with issues."""
        report = {
            'healthy': False,
            'issues': ['Error 1', 'Error 2'],
            'warnings': ['Warning 1']
        }
        status.display_health_report(report)
        output = capsys.readouterr().out
        assert 'Error 1' in output
        assert 'Warning 1' in output


# ==================== JSON Output Tests ====================

class TestJSONOutput:
    def test_output_json(self, capsys):
        """Test JSON output."""
        data = {'key': 'value', 'number': 42}
        status.output_json(data)
        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert parsed['key'] == 'value'
        assert parsed['number'] == 42


# ==================== Integration Tests ====================

class TestMainIntegration:
    def test_main_default_output(self, capsys):
        """Test main function with default output."""
        create_task('TASK-1', 'todo', title='Integration Test')
        create_ledger_entry('20230101000000')
        create_staging_file('test.txt')

        with patch.object(sys, 'argv', ['avcpm_status.py']):
            status.main()

        output = capsys.readouterr().out
        assert 'TASK BOARD' in output
        assert 'LEDGER ACTIVITY' in output
        assert 'STAGING STATUS' in output
        assert 'SYSTEM HEALTH' in output

    def test_main_tasks_only(self, capsys):
        """Test main function with --tasks flag."""
        create_task('TASK-1', 'todo')

        with patch.object(sys, 'argv', ['avcpm_status.py', '--tasks']):
            status.main()

        output = capsys.readouterr().out
        assert 'TASK BOARD' in output
        assert 'LEDGER ACTIVITY' not in output

    def test_main_json_output(self, capsys):
        """Test main function with --json flag."""
        create_task('TASK-1', 'todo')

        with patch.object(sys, 'argv', ['avcpm_status.py', '--json']):
            status.main()

        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert 'tasks' in parsed

    def test_main_ledger_only(self, capsys):
        """Test main function with --ledger flag."""
        create_ledger_entry('20230101000000')

        with patch.object(sys, 'argv', ['avcpm_status.py', '--ledger']):
            status.main()

        output = capsys.readouterr().out
        assert 'LEDGER ACTIVITY' in output
        assert 'TASK BOARD' not in output

    def test_main_staging_only(self, capsys):
        """Test main function with --staging flag."""
        create_staging_file('test.txt')

        with patch.object(sys, 'argv', ['avcpm_status.py', '--staging']):
            status.main()

        output = capsys.readouterr().out
        assert 'STAGING STATUS' in output
        assert 'LEDGER ACTIVITY' not in output