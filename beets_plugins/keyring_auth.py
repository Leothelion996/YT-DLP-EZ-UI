"""
Keyring Authentication Plugin for Beets.
Securely loads AcoustID API key from OS keyring at runtime.
"""

import logging
from beets.plugins import BeetsPlugin
from beets import config

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False


class KeyringAuthPlugin(BeetsPlugin):
    """
    Beets plugin to load AcoustID API key from system keyring.
    Prevents storing API keys in plaintext configuration files.
    """

    def __init__(self):
        """Initialize the keyring auth plugin."""
        super().__init__()
        self.logger = logging.getLogger(__name__)

        if not KEYRING_AVAILABLE:
            self.logger.warning("keyring library not available, API key must be in config")
            return

        # Load AcoustID key from keyring
        try:
            api_key = keyring.get_password("YT-DLP_EZ-UI_Beets", "acoustid")
            if api_key:
                # Inject key into beets config at runtime
                config['chroma']['acoustid']['apikey'] = api_key
                self.logger.info("AcoustID API key loaded from keyring")
            else:
                self.logger.warning("No AcoustID API key found in keyring")
        except Exception as e:
            self.logger.error(f"Failed to load API key from keyring: {e}")
