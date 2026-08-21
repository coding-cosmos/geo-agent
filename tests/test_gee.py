import pytest
from unittest.mock import patch
from app.gee import initialize_gee


def test_initialize_gee_success():
    """Test that initialize_gee succeeds when ee.Initialize succeeds."""
    with patch("app.gee.ee.Initialize") as mock_initialize:
        initialize_gee("test-project")
        mock_initialize.assert_called_once_with(project="test-project")


def test_initialize_gee_failure():
    """Test that initialize_gee raises a RuntimeError when ee.Initialize fails."""
    with patch("app.gee.ee.Initialize") as mock_initialize:
        # Simulate an authentication or initialization failure
        mock_initialize.side_effect = Exception("Google Cloud error")

        with pytest.raises(RuntimeError) as exc_info:
            initialize_gee("test-project")

        assert "Failed to initialize Earth Engine" in str(exc_info.value)
        mock_initialize.assert_called_once_with(project="test-project")


def test_initialize_gee_no_authenticate():
    """Test that initialize_gee does not call ee.Authenticate under any circumstances."""
    with patch("app.gee.ee.Initialize") as mock_initialize, \
         patch("app.gee.ee.Authenticate") as mock_authenticate:

        # Test success case
        initialize_gee("test-project")
        mock_authenticate.assert_not_called()

        # Test failure case
        mock_initialize.side_effect = Exception("Google Cloud error")
        with pytest.raises(RuntimeError):
            initialize_gee("test-project")

        mock_authenticate.assert_not_called()
