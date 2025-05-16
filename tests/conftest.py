"""
Configuration for pytest.
"""
import sys
import os
from unittest import mock

# Add the parent directory to the Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Mock the src module imports
sys.modules['src.agent_manager'] = mock.MagicMock()
sys.modules['src.config'] = mock.MagicMock()
sys.modules['src.models'] = mock.MagicMock()
sys.modules['src.context'] = mock.MagicMock()
sys.modules['src.api_client'] = mock.MagicMock()
sys.modules['src.utils.error_handler'] = mock.MagicMock()
