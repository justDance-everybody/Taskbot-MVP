"""
Property-based tests for Task Scheduler
Feature: taskbot-completion, Property 4: Reminder Idempotence, Property 5: Archive Timing
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import sys

# Mock the Lark SDK before importing scheduler
sys.modules['lark_oapi'] = MagicMock()
sys.modules['lark_oapi.api'] = MagicMock()
sys.modules['lark_oapi.api.im'] = MagicMock()
sys.modules['lark_oapi.api.im.v1'] = MagicMock()

from app.services.scheduler import task_scheduler


# Strategy for generating task data
def task_strategy():
    """Generate valid task dictionaries"""
    return st.fixed_dictionaries({
        'record_id': st.text(min_size=10, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        'taskid': st.text(min_size=5, max_size=15, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        'title': st.text(min_size=1, max_size=100),
        'description': st.text(min_size=1, max_size=500),
        'creator': st.text(min_size=1, max_size=50),
        'assignee': st.text(min_size=1, max_size=50),
        'status': st.just('in_progress'),
        'create_time': st.datetimes(
            min_value=datetime(2024, 1, 1),
            max_value=datetime.now() - timedelta(days=1)
        ).map(lambda dt: dt.strftime('%Y-%m-%d %H:%M:%S')),
        'deadline': st.datetimes(
            min_value=datetime.now() + timedelta(days=1),
            max_value=datetime.now() + timedelta(days=30)
        ).map(lambda dt: dt.strftime('%Y-%m-%d %H:%M:%S')),
        'reminded': st.booleans(),
        'chat_id': st.text(min_size=10, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    })


def completed_task_strategy():
    """Generate completed task dictionaries"""
    return st.fixed_dictionaries({
        'record_id': st.text(min_size=10, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        'taskid': st.text(min_size=5, max_size=15, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        'title': st.text(min_size=1, max_size=100),
        'description': st.text(min_size=1, max_size=500),
        'creator': st.text(min_size=1, max_size=50),
        'assignee': st.text(min_size=1, max_size=50),
        'status': st.just('completed'),
        'create_time': st.datetimes(
            min_value=datetime(2024, 1, 1),
            max_value=datetime.now() - timedelta(days=30)
        ).map(lambda dt: dt.strftime('%Y-%m-%d %H:%M:%S')),
        'completed_at': st.datetimes(
            min_value=datetime.now() - timedelta(days=20),
            max_value=datetime.now() - timedelta(days=1)
        ).map(lambda dt: dt.strftime('%Y-%m-%d %H:%M:%S')),
        'chat_id': st.text(min_size=10, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    })


@pytest.mark.asyncio
@settings(max_examples=100)
@given(task=task_strategy())
async def test_reminder_idempotence_property(task):
    """
    Property 4: Reminder Idempotence
    
    For any task that has been reminded, calling the reminder check function again
    SHALL NOT send duplicate reminders (idempotence property).
    
    Validates: Requirements 2.2, 2.5
    Feature: taskbot-completion, Property 4: Reminder Idempotence
    """
    # Set task as already reminded
    task['reminded'] = True
    
    # Mock the internal methods
    with patch.object(task_scheduler, '_get_in_progress_tasks', new_callable=AsyncMock) as mock_get_tasks:
        with patch.object(task_scheduler, '_send_reminder', new_callable=AsyncMock) as mock_send_reminder:
            with patch.object(task_scheduler, '_mark_reminded', new_callable=AsyncMock) as mock_mark_reminded:
                # Return our test task
                mock_get_tasks.return_value = [task]
                
                # Call check_deadline_reminders
                await task_scheduler.check_deadline_reminders()
                
                # Property assertion: _send_reminder should NOT be called for already reminded tasks
                assert mock_send_reminder.call_count == 0, \
                    f"Expected no reminders for already reminded task, but got {mock_send_reminder.call_count} calls"
                
                # Property assertion: _mark_reminded should NOT be called for already reminded tasks
                assert mock_mark_reminded.call_count == 0, \
                    f"Expected no mark_reminded calls for already reminded task, but got {mock_mark_reminded.call_count} calls"


@pytest.mark.asyncio
@settings(max_examples=100)
@given(task=task_strategy())
async def test_reminder_idempotence_multiple_calls(task):
    """
    Property 4: Reminder Idempotence - Multiple Calls
    
    For any task, calling the reminder check function multiple times SHALL result
    in at most one reminder being sent (idempotence across multiple invocations).
    
    Validates: Requirements 2.2, 2.5
    Feature: taskbot-completion, Property 4: Reminder Idempotence
    """
    # Set task as not reminded initially
    task['reminded'] = False
    
    # Ensure task is past half deadline
    create_time = datetime.strptime(task['create_time'], '%Y-%m-%d %H:%M:%S')
    deadline = datetime.strptime(task['deadline'], '%Y-%m-%d %H:%M:%S')
    
    # Set create_time to ensure we're past half deadline
    total_span = deadline - datetime.now()
    if total_span.total_seconds() > 0:
        # Adjust create_time to be far enough in the past
        task['create_time'] = (datetime.now() - total_span * 2).strftime('%Y-%m-%d %H:%M:%S')
    
    reminder_count = 0
    
    # Mock the internal methods
    with patch.object(task_scheduler, '_get_in_progress_tasks', new_callable=AsyncMock) as mock_get_tasks:
        with patch.object(task_scheduler, '_send_reminder', new_callable=AsyncMock) as mock_send_reminder:
            with patch.object(task_scheduler, '_mark_reminded', new_callable=AsyncMock) as mock_mark_reminded:
                
                # First call - task not reminded
                mock_get_tasks.return_value = [task.copy()]
                await task_scheduler.check_deadline_reminders()
                first_call_count = mock_send_reminder.call_count
                
                # Simulate marking as reminded
                task['reminded'] = True
                
                # Second call - task already reminded
                mock_get_tasks.return_value = [task.copy()]
                await task_scheduler.check_deadline_reminders()
                second_call_count = mock_send_reminder.call_count
                
                # Property assertion: total reminders should be at most 1
                # (first call might send 0 or 1, second call should send 0)
                total_reminders = second_call_count
                assert total_reminders <= 1, \
                    f"Expected at most 1 reminder across multiple calls, but got {total_reminders}"


@pytest.mark.asyncio
@settings(max_examples=100)
@given(task=completed_task_strategy())
async def test_archive_timing_property(task):
    """
    Property 5: Archive Timing
    
    For any task marked Done, the task SHALL be archived exactly when 7 days have
    passed since completion, not before.
    
    Validates: Requirements 2.3
    Feature: taskbot-completion, Property 5: Archive Timing
    """
    # Parse completed_at time
    completed_at = datetime.strptime(task['completed_at'], '%Y-%m-%d %H:%M:%S')
    days_since_completion = (datetime.now() - completed_at).days
    
    # Mock the internal methods
    with patch.object(task_scheduler, '_get_completed_tasks', new_callable=AsyncMock) as mock_get_tasks:
        with patch.object(task_scheduler, '_archive_task', new_callable=AsyncMock) as mock_archive:
            # Return our test task
            mock_get_tasks.return_value = [task]
            
            # Call archive_completed_tasks
            await task_scheduler.archive_completed_tasks()
            
            # Property assertion: archive should only be called if >= 7 days have passed
            if days_since_completion >= 7:
                assert mock_archive.call_count == 1, \
                    f"Expected task to be archived after {days_since_completion} days, but archive was not called"
            else:
                assert mock_archive.call_count == 0, \
                    f"Expected task NOT to be archived after only {days_since_completion} days, but archive was called"


@pytest.mark.asyncio
@settings(max_examples=100)
@given(tasks=st.lists(completed_task_strategy(), min_size=1, max_size=10))
async def test_archive_timing_boundary(tasks):
    """
    Property 5: Archive Timing - Boundary Test
    
    For any set of completed tasks, only those completed >= 7 days ago SHALL be archived.
    Tasks completed < 7 days ago SHALL NOT be archived.
    
    Validates: Requirements 2.3
    Feature: taskbot-completion, Property 5: Archive Timing
    """
    # Mock the internal methods
    with patch.object(task_scheduler, '_get_completed_tasks', new_callable=AsyncMock) as mock_get_tasks:
        with patch.object(task_scheduler, '_archive_task', new_callable=AsyncMock) as mock_archive:
            # Return our test tasks
            mock_get_tasks.return_value = tasks
            
            # Call archive_completed_tasks
            await task_scheduler.archive_completed_tasks()
            
            # Count how many tasks should be archived
            expected_archives = 0
            for task in tasks:
                completed_at = datetime.strptime(task['completed_at'], '%Y-%m-%d %H:%M:%S')
                days_since_completion = (datetime.now() - completed_at).days
                if days_since_completion >= 7:
                    expected_archives += 1
            
            # Property assertion: archive should be called exactly for tasks >= 7 days old
            actual_archives = mock_archive.call_count
            assert actual_archives == expected_archives, \
                f"Expected {expected_archives} tasks to be archived, but {actual_archives} were archived"


@pytest.mark.asyncio
@settings(max_examples=100)
@given(task=completed_task_strategy())
async def test_archive_exactly_7_days(task):
    """
    Property 5: Archive Timing - Exact 7 Day Boundary
    
    For any task completed exactly 7 days ago, the task SHALL be archived.
    
    Validates: Requirements 2.3
    Feature: taskbot-completion, Property 5: Archive Timing
    """
    # Set completed_at to exactly 7 days ago
    exactly_7_days_ago = datetime.now() - timedelta(days=7)
    task['completed_at'] = exactly_7_days_ago.strftime('%Y-%m-%d %H:%M:%S')
    
    # Mock the internal methods
    with patch.object(task_scheduler, '_get_completed_tasks', new_callable=AsyncMock) as mock_get_tasks:
        with patch.object(task_scheduler, '_archive_task', new_callable=AsyncMock) as mock_archive:
            # Return our test task
            mock_get_tasks.return_value = [task]
            
            # Call archive_completed_tasks
            await task_scheduler.archive_completed_tasks()
            
            # Property assertion: task completed exactly 7 days ago should be archived
            assert mock_archive.call_count == 1, \
                f"Expected task completed exactly 7 days ago to be archived, but archive was not called"
