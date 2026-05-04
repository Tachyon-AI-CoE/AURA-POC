"""
Unit tests for utils/log_helper.py
Tests logging configuration

Note: These tests mock logging.basicConfig() because it only works once per
Python process. We verify that basicConfig is called with correct parameters
rather than testing the actual logging output in most cases.
"""
import os
import sys
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import pytest

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from utils.log_helper import setup_logging


class TestLogHelper:
    """Test suite for log_helper module"""
    
    def setup_method(self):
        """Reset logger state before each test"""
        # Get root logger and reset its level
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.WARNING)  # Reset to default
        # Clear all handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        # Reset the logging module's internal state
        logging.root.manager.loggerDict.clear()
    
    @patch.dict(os.environ, {}, clear=True)
    @patch('utils.log_helper.load_dotenv')
    @patch('utils.log_helper.logging.basicConfig')
    def test_setup_logging_default_level(self, mock_basic_config, mock_load_dotenv):
        """Test setup_logging with default INFO level"""
        # Import after patching environment
        from utils import log_helper
        
        # Reload to pick up mocked environment
        import importlib
        importlib.reload(log_helper)
        
        logger = log_helper.setup_logging()
        
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        # Verify basicConfig was called with INFO level (default)
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args.kwargs
        assert call_kwargs['level'] == 'INFO'
    
    @patch.dict(os.environ, {'LOG_LEVEL': 'DEBUG'}, clear=True)
    @patch('utils.log_helper.load_dotenv')
    @patch('utils.log_helper.logging.basicConfig')
    def test_setup_logging_custom_level_debug(self, mock_basic_config, mock_load_dotenv):
        """Test setup_logging with DEBUG level"""
        # Import after patching environment
        from utils import log_helper
        
        # Reload to pick up mocked environment
        import importlib
        importlib.reload(log_helper)
        
        logger = log_helper.setup_logging()
        
        assert logger is not None
        # Verify basicConfig was called with DEBUG level
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args.kwargs
        assert call_kwargs['level'] == 'DEBUG'
    
    @patch.dict(os.environ, {'LOG_LEVEL': 'WARNING'}, clear=True)
    @patch('utils.log_helper.load_dotenv')
    @patch('utils.log_helper.logging.basicConfig')
    def test_setup_logging_custom_level_warning(self, mock_basic_config, mock_load_dotenv):
        """Test setup_logging with WARNING level"""
        # Import after patching environment
        from utils import log_helper
        
        # Reload to pick up mocked environment
        import importlib
        importlib.reload(log_helper)
        
        logger = log_helper.setup_logging()
        
        assert logger is not None
        # Verify basicConfig was called with WARNING level
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args.kwargs
        assert call_kwargs['level'] == 'WARNING'
    
    @patch.dict(os.environ, {'LOG_LEVEL': 'ERROR'}, clear=True)
    @patch('utils.log_helper.load_dotenv')
    @patch('utils.log_helper.logging.basicConfig')
    def test_setup_logging_custom_level_error(self, mock_basic_config, mock_load_dotenv):
        """Test setup_logging with ERROR level"""
        # Import after patching environment
        from utils import log_helper
        
        # Reload to pick up mocked environment
        import importlib
        importlib.reload(log_helper)
        
        logger = log_helper.setup_logging()
        
        assert logger is not None
        # Verify basicConfig was called with ERROR level
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args.kwargs
        assert call_kwargs['level'] == 'ERROR'
    
    def test_setup_logging_returns_logger_instance(self):
        """Test that setup_logging returns a logger instance"""
        logger = setup_logging()
        
        assert isinstance(logger, logging.Logger)
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'critical')
    
    @patch('utils.log_helper.logging.basicConfig')
    def test_setup_logging_format_configured(self, mock_basic_config):
        """Test that logging format is properly configured"""
        setup_logging()
        
        # Verify basicConfig was called with correct format
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args.kwargs
        assert 'format' in call_kwargs
        format_string = call_kwargs['format']
        # Check that format includes required elements
        assert '%(levelname)s' in format_string
        assert '%(asctime)s' in format_string
        assert '%(message)s' in format_string
    
    @patch('utils.log_helper.logging.basicConfig')
    def test_setup_logging_can_log_messages(self, mock_basic_config, caplog):
        """Test that logger can actually log messages"""
        logger = setup_logging()
        
        # Set logger level explicitly for test
        logger.setLevel(logging.INFO)
        
        with caplog.at_level(logging.INFO):
            logger.info("Test info message")
        
        # Verify the message was logged
        assert "Test info message" in caplog.text
    
    @patch('utils.log_helper.logging.basicConfig')
    def test_setup_logging_multiple_calls_same_logger(self, mock_basic_config):
        """Test that multiple calls return the same logger instance"""
        logger1 = setup_logging()
        logger2 = setup_logging()
        
        # Both should return the root logger
        assert logger1 is logger2
        assert logger1 is logging.getLogger()
    
    @patch.dict(os.environ, {'LOG_LEVEL': 'INVALID_LEVEL'}, clear=True)
    @patch('utils.log_helper.load_dotenv')
    @patch('utils.log_helper.logging.basicConfig')
    def test_setup_logging_with_invalid_level(self, mock_basic_config, mock_load_dotenv):
        """Test that invalid log level is passed to basicConfig"""
        # Import after patching environment
        from utils import log_helper
        
        # Reload to pick up mocked environment
        import importlib
        importlib.reload(log_helper)
        
        # Should not raise exception - logging handles invalid levels
        logger = log_helper.setup_logging()
        assert logger is not None
        # Verify basicConfig was called with the invalid level string
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args.kwargs
        assert call_kwargs['level'] == 'INVALID_LEVEL'
    
    @patch.dict(os.environ, {'LOG_LEVEL': 'DEBUG'}, clear=True)
    @patch('utils.log_helper.logging.basicConfig')
    def test_setup_logging_respects_dotenv(self, mock_basic_config):
        """Test that setup_logging loads configuration from environment
        
        Note: load_dotenv() is called at module import time, not during setup_logging().
        This test verifies that environment variables are properly used by setup_logging().
        """
        # Import after patching environment
        from utils import log_helper
        
        # Reload to pick up mocked environment
        import importlib
        importlib.reload(log_helper)
        
        logger = log_helper.setup_logging()
        
        # Verify basicConfig was called with DEBUG level from env
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args.kwargs
        assert call_kwargs['level'] == 'DEBUG'
    
    @patch('utils.log_helper.logging.basicConfig')
    def test_setup_logging_calls_basic_config(self, mock_basic_config):
        """Test that setup_logging calls logging.basicConfig"""
        setup_logging()
        
        # Verify basicConfig was called
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        assert 'level' in call_args.kwargs
        assert 'format' in call_args.kwargs
    
    @patch('utils.log_helper.logging.basicConfig')
    def test_log_format_includes_timestamp(self, mock_basic_config):
        """Test that log format includes timestamp"""
        setup_logging()
        
        # Verify basicConfig was called with format containing asctime
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args.kwargs
        format_string = call_kwargs.get('format', '')
        # Check for asctime
        assert 'asctime' in format_string
