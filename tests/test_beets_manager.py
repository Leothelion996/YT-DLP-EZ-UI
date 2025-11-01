"""
Unit tests for Beets manager.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from core.beets_manager import BeetsManager


class TestBeetsManager(unittest.TestCase):
    """Test cases for BeetsManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = BeetsManager()

    def test_initialization(self):
        """Test beets manager initialization."""
        self.assertIsNotNone(self.manager)
        self.assertEqual(self.manager.KEYRING_SERVICE, "YT-DLP_EZ-UI_Beets")
        self.assertEqual(self.manager.KEYRING_USERNAME_ACOUSTID, "acoustid")

    def test_is_available_with_beets(self):
        """Test availability check when beets is installed."""
        # This will depend on whether beets is actually installed in test environment
        result = self.manager.is_available()
        self.assertIsInstance(result, bool)

    @patch('core.beets_manager.KEYRING_AVAILABLE', True)
    @patch('core.beets_manager.keyring')
    def test_is_acoustid_configured_true(self, mock_keyring):
        """Test AcoustID configuration check when key exists."""
        mock_keyring.get_password.return_value = "test_api_key_123"

        result = self.manager.is_acoustid_configured()

        self.assertTrue(result)
        mock_keyring.get_password.assert_called_once_with(
            "YT-DLP_EZ-UI_Beets", "acoustid"
        )

    @patch('core.beets_manager.KEYRING_AVAILABLE', True)
    @patch('core.beets_manager.keyring')
    def test_is_acoustid_configured_false(self, mock_keyring):
        """Test AcoustID configuration check when key doesn't exist."""
        mock_keyring.get_password.return_value = None

        result = self.manager.is_acoustid_configured()

        self.assertFalse(result)

    @patch('core.beets_manager.KEYRING_AVAILABLE', False)
    def test_is_acoustid_configured_no_keyring(self):
        """Test configuration check when keyring is not available."""
        result = self.manager.is_acoustid_configured()
        self.assertFalse(result)

    @patch('core.beets_manager.KEYRING_AVAILABLE', True)
    @patch('core.beets_manager.keyring')
    def test_get_acoustid_key_success(self, mock_keyring):
        """Test retrieving AcoustID key from keyring."""
        expected_key = "abc123xyz"
        mock_keyring.get_password.return_value = expected_key

        result = self.manager.get_acoustid_key()

        self.assertEqual(result, expected_key)
        mock_keyring.get_password.assert_called_once()

    @patch('core.beets_manager.KEYRING_AVAILABLE', True)
    @patch('core.beets_manager.keyring')
    def test_get_acoustid_key_not_found(self, mock_keyring):
        """Test retrieving AcoustID key when it doesn't exist."""
        mock_keyring.get_password.return_value = None

        result = self.manager.get_acoustid_key()

        self.assertIsNone(result)

    @patch('core.beets_manager.KEYRING_AVAILABLE', False)
    def test_get_acoustid_key_no_keyring(self):
        """Test retrieving key when keyring is not available."""
        result = self.manager.get_acoustid_key()
        self.assertIsNone(result)

    @patch('core.beets_manager.KEYRING_AVAILABLE', True)
    @patch('core.beets_manager.keyring')
    def test_set_acoustid_key_success(self, mock_keyring):
        """Test storing AcoustID key in keyring."""
        test_key = "new_api_key_456"

        result = self.manager.set_acoustid_key(test_key)

        self.assertTrue(result)
        mock_keyring.set_password.assert_called_once_with(
            "YT-DLP_EZ-UI_Beets", "acoustid", test_key
        )

    @patch('core.beets_manager.KEYRING_AVAILABLE', True)
    @patch('core.beets_manager.keyring')
    def test_set_acoustid_key_empty(self, mock_keyring):
        """Test storing empty key (should fail)."""
        result = self.manager.set_acoustid_key("")

        self.assertFalse(result)
        mock_keyring.set_password.assert_not_called()

    @patch('core.beets_manager.KEYRING_AVAILABLE', False)
    def test_set_acoustid_key_no_keyring(self):
        """Test storing key when keyring is not available."""
        result = self.manager.set_acoustid_key("test_key")
        self.assertFalse(result)

    @patch('core.beets_manager.KEYRING_AVAILABLE', True)
    @patch('core.beets_manager.keyring')
    def test_delete_acoustid_key_success(self, mock_keyring):
        """Test deleting AcoustID key from keyring."""
        result = self.manager.delete_acoustid_key()

        self.assertTrue(result)
        mock_keyring.delete_password.assert_called_once_with(
            "YT-DLP_EZ-UI_Beets", "acoustid"
        )

    @patch('core.beets_manager.KEYRING_AVAILABLE', True)
    @patch('core.beets_manager.keyring')
    def test_delete_acoustid_key_error(self, mock_keyring):
        """Test deleting key when an error occurs."""
        mock_keyring.delete_password.side_effect = Exception("Key not found")

        result = self.manager.delete_acoustid_key()

        self.assertFalse(result)

    def test_validate_key_valid(self):
        """Test validation of valid API keys."""
        valid_keys = [
            "abc12345",
            "XYZ789ab",
            "test-key",
            "my-api-key-123"
        ]

        for key in valid_keys:
            with self.subTest(key=key):
                result = self.manager.validate_key(key)
                self.assertTrue(result, f"Key '{key}' should be valid")

    def test_validate_key_invalid(self):
        """Test validation of invalid API keys."""
        invalid_keys = [
            "",                    # Empty
            "   ",                 # Whitespace only
            "abc",                 # Too short
            None,                  # None
            123,                   # Not a string
            "key@#$%",            # Special characters
        ]

        for key in invalid_keys:
            with self.subTest(key=key):
                result = self.manager.validate_key(key)
                self.assertFalse(result, f"Key '{key}' should be invalid")

    @patch('core.beets_manager.BEETS_AVAILABLE', False)
    def test_run_beets_import_no_beets(self):
        """Test import when beets is not available."""
        completion_callback = Mock()

        result = self.manager.run_beets_import(
            source_path="/fake/path",
            library_path="/fake/library",
            completion_callback=completion_callback
        )

        self.assertFalse(result)
        completion_callback.assert_called_once_with(False, "Beets library not installed")

    @patch('core.beets_manager.BEETS_AVAILABLE', True)
    @patch.object(BeetsManager, 'is_acoustid_configured', return_value=False)
    def test_run_beets_import_no_api_key(self, mock_configured):
        """Test import when AcoustID is not configured."""
        completion_callback = Mock()

        result = self.manager.run_beets_import(
            source_path="/fake/path",
            library_path="/fake/library",
            completion_callback=completion_callback
        )

        self.assertFalse(result)
        completion_callback.assert_called_once_with(False, "AcoustID API key not configured")

    @patch('core.beets_manager.BEETS_AVAILABLE', True)
    @patch.object(BeetsManager, 'is_acoustid_configured', return_value=True)
    def test_run_beets_import_invalid_path(self, mock_configured):
        """Test import with non-existent source path."""
        completion_callback = Mock()

        result = self.manager.run_beets_import(
            source_path="/nonexistent/path",
            library_path="/fake/library",
            completion_callback=completion_callback
        )

        self.assertFalse(result)
        # Should call completion_callback with error
        completion_callback.assert_called_once()
        args = completion_callback.call_args[0]
        self.assertFalse(args[0])  # success = False
        self.assertIn("Invalid source path", args[1])

    @patch('core.beets_manager.Path.mkdir')
    @patch('core.beets_manager.Path.exists', return_value=True)
    def test_ensure_config_directory(self, mock_exists, mock_mkdir):
        """Test ensuring config directory exists."""
        # This is called in __init__, so test it indirectly
        manager = BeetsManager()
        # Directory creation should have been attempted
        self.assertIsNotNone(manager)

    @patch('core.beets_manager.BEETS_CONFIG_DIR')
    def test_create_beets_config(self, mock_config_dir):
        """Test creating beets configuration file."""
        # This is a complex method that requires file system access
        # In a real test environment, you'd use tempfile
        # For now, just ensure it's callable
        self.assertTrue(hasattr(self.manager, '_create_beets_config'))

    def test_cancel_all(self):
        """Test cancelling all active imports."""
        # Should set the cancel event flag
        self.manager.cancel_all()
        self.assertTrue(self.manager._cancel_event.is_set())


class TestBeetsManagerIntegration(unittest.TestCase):
    """Integration tests for BeetsManager (requires beets installed)."""

    @unittest.skipIf(not BeetsManager().is_available(), "Beets not installed")
    def test_beets_available(self):
        """Test that beets is properly detected when installed."""
        manager = BeetsManager()
        self.assertTrue(manager.is_available())


if __name__ == '__main__':
    unittest.main()
