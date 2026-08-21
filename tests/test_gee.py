import pytest
from unittest.mock import patch, call
from app.gee import initialize_gee

@patch('app.gee.ee')
def test_initialize_gee_success(mock_ee):
    """Test successful initialization on first try."""
    initialize_gee("test-project")

    mock_ee.Initialize.assert_called_once_with(project="test-project")
    mock_ee.Authenticate.assert_not_called()

@patch('app.gee.ee')
def test_initialize_gee_fallback(mock_ee):
    """Test fallback to authentication when initialization fails."""
    # Set up the mock to raise an exception on the first call, then succeed
    mock_ee.Initialize.side_effect = [Exception("Init failed"), None]

    initialize_gee("test-project")

    # Initialize should be called twice
    assert mock_ee.Initialize.call_count == 2
    mock_ee.Initialize.assert_has_calls([
        call(project="test-project"),
        call(project="test-project")
    ])

    # Authenticate should be called once in between
    mock_ee.Authenticate.assert_called_once()
