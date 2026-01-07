"""
Property-based tests for Daily Report Generation
Feature: taskbot-completion, Property 8: Daily Report Completeness
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import AsyncMock, patch, MagicMock, mock_open
from datetime import datetime
import json
from app.services.task_manager import task_manager


# Strategy for generating daily stats data
def daily_stats_strategy():
    """Generate valid daily stats dictionaries"""
    total = st.integers(min_value=0, max_value=1000)
    
    @st.composite
    def stats_with_valid_counts(draw):
        total_tasks = draw(total)
        completed = draw(st.integers(min_value=0, max_value=total_tasks))
        pending = draw(st.integers(min_value=0, max_value=total_tasks - completed))
        in_progress = draw(st.integers(min_value=0, max_value=total_tasks - completed - pending))
        submitted = draw(st.integers(min_value=0, max_value=total_tasks - completed - pending - in_progress))
        reviewing = draw(st.integers(min_value=0, max_value=total_tasks - completed - pending - in_progress - submitted))
        
        return {
            'date': draw(st.dates(min_value=datetime(2024, 1, 1).date(), max_value=datetime.now().date())).strftime('%Y-%m-%d'),
            'total_tasks': total_tasks,
            'completed_tasks': completed,
            'pending_tasks': pending,
            'in_progress_tasks': in_progress,
            'submitted_tasks': submitted,
            'reviewing_tasks': reviewing,
            'rejected_tasks': draw(st.integers(min_value=0, max_value=50)),
            'assigned_tasks': draw(st.integers(min_value=0, max_value=50)),
            'cancelled_tasks': draw(st.integers(min_value=0, max_value=50)),
            'average_score': draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)),
            'completion_rate': draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)),
            'tasks_by_urgency': {
                'urgent': draw(st.integers(min_value=0, max_value=100)),
                'high': draw(st.integers(min_value=0, max_value=100)),
                'normal': draw(st.integers(min_value=0, max_value=100)),
                'low': draw(st.integers(min_value=0, max_value=100))
            },
            'today_created': draw(st.integers(min_value=0, max_value=100)),
            'today_completed': draw(st.integers(min_value=0, max_value=100)),
            'top_performers': draw(st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=10))
        }
    
    return stats_with_valid_counts()


# Strategy for generating task info
def task_info_strategy():
    """Generate valid task info dictionaries"""
    return st.fixed_dictionaries({
        'total_records': st.integers(min_value=0, max_value=1000),
        'valid_records': st.integers(min_value=0, max_value=1000),
        'empty_records': st.integers(min_value=0, max_value=100)
    })


@pytest.mark.asyncio
@settings(max_examples=100)
@given(
    stats_data=daily_stats_strategy(),
    task_info=task_info_strategy()
)
async def test_daily_report_completeness_property(stats_data, task_info):
    """
    Property 8: Daily Report Completeness
    
    For any daily report generation, the output SHALL contain: total_tasks,
    completed_tasks, pending_tasks, in_progress_tasks, and average_assignment_time.
    
    Validates: Requirements 6.1, 6.2, 6.3
    Feature: taskbot-completion, Property 8: Daily Report Completeness
    """
    # Mock file operations to return our test stats data
    mock_file_content = json.dumps(stats_data)
    
    with patch('builtins.open', mock_open(read_data=mock_file_content)):
        with patch('os.path.exists', return_value=True):
            with patch.object(task_manager, '_get_simple_task_info', new_callable=AsyncMock) as mock_task_info:
                with patch.object(task_manager, '_calculate_average_assignment_time', new_callable=AsyncMock) as mock_avg_time:
                    # Setup mocks
                    mock_task_info.return_value = task_info
                    mock_avg_time.return_value = "2.5小时"
                    
                    # Call the method under test
                    report = await task_manager.generate_daily_report()
                    
                    # Property assertion: report must contain all required fields
                    required_fields = [
                        'total_tasks',
                        'completed_tasks',
                        'pending_tasks',
                        'in_progress_tasks',
                        'average_assignment_time'
                    ]
                    
                    for field in required_fields:
                        assert field in report, f"Report missing required field: {field}"
                        assert report[field] is not None, f"Required field {field} is None"
                    
                    # Additional assertions for field types
                    assert isinstance(report['total_tasks'], int), "total_tasks should be an integer"
                    assert isinstance(report['completed_tasks'], int), "completed_tasks should be an integer"
                    assert isinstance(report['pending_tasks'], int), "pending_tasks should be an integer"
                    assert isinstance(report['in_progress_tasks'], int), "in_progress_tasks should be an integer"
                    assert isinstance(report['average_assignment_time'], str), "average_assignment_time should be a string"


@pytest.mark.asyncio
@settings(max_examples=100)
@given(
    stats_data=daily_stats_strategy(),
    task_info=task_info_strategy()
)
async def test_daily_report_additional_fields(stats_data, task_info):
    """
    Property 8: Daily Report Completeness - Additional Fields
    
    For any daily report generation, the output SHALL also contain additional
    fields like submitted_tasks, reviewing_tasks, completion_rate, etc.
    
    Validates: Requirements 6.1, 6.2, 6.3
    Feature: taskbot-completion, Property 8: Daily Report Completeness
    """
    # Mock file operations
    mock_file_content = json.dumps(stats_data)
    
    with patch('builtins.open', mock_open(read_data=mock_file_content)):
        with patch('os.path.exists', return_value=True):
            with patch.object(task_manager, '_get_simple_task_info', new_callable=AsyncMock) as mock_task_info:
                with patch.object(task_manager, '_calculate_average_assignment_time', new_callable=AsyncMock) as mock_avg_time:
                    # Setup mocks
                    mock_task_info.return_value = task_info
                    mock_avg_time.return_value = "1.2天"
                    
                    # Call the method under test
                    report = await task_manager.generate_daily_report()
                    
                    # Property assertion: report should contain additional expected fields
                    additional_fields = [
                        'date',
                        'submitted_tasks',
                        'reviewing_tasks',
                        'rejected_tasks',
                        'assigned_tasks',
                        'cancelled_tasks',
                        'average_score',
                        'completion_rate',
                        'tasks_by_urgency',
                        'today_created',
                        'today_completed'
                    ]
                    
                    for field in additional_fields:
                        assert field in report, f"Report missing expected field: {field}"


@pytest.mark.asyncio
@settings(max_examples=100)
@given(
    stats_data=daily_stats_strategy(),
    task_info=task_info_strategy()
)
async def test_daily_report_non_negative_counts(stats_data, task_info):
    """
    Property 8: Daily Report Completeness - Non-negative Invariant
    
    For any daily report generation, all task count fields SHALL be non-negative.
    
    Validates: Requirements 6.1, 6.2
    Feature: taskbot-completion, Property 8: Daily Report Completeness
    """
    # Mock file operations
    mock_file_content = json.dumps(stats_data)
    
    with patch('builtins.open', mock_open(read_data=mock_file_content)):
        with patch('os.path.exists', return_value=True):
            with patch.object(task_manager, '_get_simple_task_info', new_callable=AsyncMock) as mock_task_info:
                with patch.object(task_manager, '_calculate_average_assignment_time', new_callable=AsyncMock) as mock_avg_time:
                    # Setup mocks
                    mock_task_info.return_value = task_info
                    mock_avg_time.return_value = "45分钟"
                    
                    # Call the method under test
                    report = await task_manager.generate_daily_report()
                    
                    # Property assertion: all count fields must be non-negative
                    count_fields = [
                        'total_tasks', 'completed_tasks', 'pending_tasks',
                        'in_progress_tasks', 'submitted_tasks', 'reviewing_tasks',
                        'rejected_tasks', 'assigned_tasks', 'cancelled_tasks',
                        'today_created', 'today_completed'
                    ]
                    
                    for field in count_fields:
                        if field in report:
                            assert report[field] >= 0, f"Field {field} should be non-negative, got {report[field]}"


@pytest.mark.asyncio
async def test_daily_report_error_handling():
    """
    Property 8: Daily Report Completeness - Error Handling
    
    For any error during report generation, the output SHALL still contain
    all required fields with default values.
    
    Validates: Requirements 6.1, 6.2, 6.3
    Feature: taskbot-completion, Property 8: Daily Report Completeness
    """
    # Mock file operations to simulate file not found
    with patch('os.path.exists', return_value=False):
        with patch.object(task_manager, '_get_simple_task_info', new_callable=AsyncMock) as mock_task_info:
            with patch.object(task_manager, '_calculate_average_assignment_time', new_callable=AsyncMock) as mock_avg_time:
                # Setup mocks to raise exceptions
                mock_task_info.side_effect = Exception("Database error")
                mock_avg_time.return_value = "N/A"
                
                # Call the method under test
                report = await task_manager.generate_daily_report()
                
                # Property assertion: even with errors, required fields must exist
                required_fields = [
                    'total_tasks',
                    'completed_tasks',
                    'pending_tasks',
                    'in_progress_tasks',
                    'average_assignment_time'
                ]
                
                for field in required_fields:
                    assert field in report, f"Report missing required field even after error: {field}"
                    assert report[field] is not None, f"Required field {field} is None after error"


@pytest.mark.asyncio
@settings(max_examples=100)
@given(
    stats_data=daily_stats_strategy(),
    task_info=task_info_strategy()
)
async def test_daily_report_date_format(stats_data, task_info):
    """
    Property 8: Daily Report Completeness - Date Format
    
    For any daily report generation, the date field SHALL be in YYYY-MM-DD format.
    
    Validates: Requirements 6.1, 6.3
    Feature: taskbot-completion, Property 8: Daily Report Completeness
    """
    # Mock file operations
    mock_file_content = json.dumps(stats_data)
    
    with patch('builtins.open', mock_open(read_data=mock_file_content)):
        with patch('os.path.exists', return_value=True):
            with patch.object(task_manager, '_get_simple_task_info', new_callable=AsyncMock) as mock_task_info:
                with patch.object(task_manager, '_calculate_average_assignment_time', new_callable=AsyncMock) as mock_avg_time:
                    # Setup mocks
                    mock_task_info.return_value = task_info
                    mock_avg_time.return_value = "3.0小时"
                    
                    # Call the method under test
                    report = await task_manager.generate_daily_report()
                    
                    # Property assertion: date should be in correct format
                    assert 'date' in report, "Report missing date field"
                    date_str = report['date']
                    
                    # Validate date format YYYY-MM-DD
                    try:
                        datetime.strptime(date_str, '%Y-%m-%d')
                    except ValueError:
                        pytest.fail(f"Date field '{date_str}' is not in YYYY-MM-DD format")
