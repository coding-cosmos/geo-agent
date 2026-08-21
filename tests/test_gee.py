import pytest
from unittest.mock import patch, call
from app.gee import initialize_gee

@patch("app.gee.ee")
def test_initialize_gee_success_first_try(mock_ee):
    """Test successful initialization where ee.Initialize works on the first try."""
    mock_ee.Initialize.return_value = None

    initialize_gee("test-project-id")

    mock_ee.Initialize.assert_called_once_with(project="test-project-id")
    mock_ee.Authenticate.assert_not_called()

@patch("app.gee.ee")
def test_initialize_gee_fallback_authentication(mock_ee):
    """Test fallback authentication where ee.Initialize fails on the first try."""
    # First call to Initialize raises an Exception, second call succeeds
    mock_ee.Initialize.side_effect = [Exception("Initialization failed"), None]

    initialize_gee("test-project-id")

    assert mock_ee.Initialize.call_count == 2
    mock_ee.Initialize.assert_has_calls([
        call(project="test-project-id"),
        call(project="test-project-id")
    ])
    mock_ee.Authenticate.assert_called_once()

@patch("app.gee.ee")
def test_initialize_gee_failure_after_authentication(mock_ee):
    """Test failure scenario where initialization continues to fail even after authentication."""
    # Both calls to Initialize raise an Exception
    mock_ee.Initialize.side_effect = [Exception("First failure"), Exception("Second failure")]

    with pytest.raises(Exception, match="Second failure"):
        initialize_gee("test-project-id")

    assert mock_ee.Initialize.call_count == 2
    mock_ee.Authenticate.assert_called_once()
