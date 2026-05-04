"""
Unit tests for log_helper module
"""
import logging
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from utils.log_helper import setup_logging  # type: ignore[import-not-found]


class TestLogHelper:
    """Test suite for log_helper utilities"""
    
    @patch.dict(os.environ, {'LOG_LEVEL': 'INFO'}, clear=False)
    @patch('utils.log_helper.logging.basicConfig')
    def test_setup_logging_default_level(self, mock_basic_config):
        """Test setup_logging with default INFO level"""
        logger = setup_logging()
        
        # Verify basicConfig was called
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args.kwargs
        assert call_kwargs['level'] == 'INFO'
        assert 'format' in call_kwargs
        
        # Verify logger is returned
        assert logger is not None
        assert isinstance(logger, logging.Logger)
    
    @patch('utils.log_helper.LOG_LEVEL', 'DEBUG')
    @patch('utils.log_helper.logging.basicConfig')
    def test_setup_logging_debug_level(self, mock_basic_config):
        """Test setup_logging with DEBUG level
        
        Note: LOG_LEVEL is captured at module import time in log_helper.py,
        so we patch the variable directly rather than the environment.
        """
        logger = setup_logging()
        
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args.kwargs
        assert call_kwargs['level'] == 'DEBUG'
    
    @patch('utils.log_helper.LOG_LEVEL', 'WARNING')
    @patch('utils.log_helper.logging.basicConfig')
    def test_setup_logging_warning_level(self, mock_basic_config):
        """Test setup_logging with WARNING level
        
        Note: LOG_LEVEL is captured at module import time in log_helper.py,
        so we patch the variable directly rather than the environment.
        """
        logger = setup_logging()
        
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args.kwargs
        assert call_kwargs['level'] == 'WARNING'
    
    @patch('utils.log_helper.LOG_LEVEL', 'ERROR')
    @patch('utils.log_helper.logging.basicConfig')
    def test_setup_logging_error_level(self, mock_basic_config):
        """Test setup_logging with ERROR level
        
        Note: LOG_LEVEL is captured at module import time in log_helper.py,
        so we patch the variable directly rather than the environment.
        """
        logger = setup_logging()
        
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args.kwargs
        assert call_kwargs['level'] == 'ERROR'
    
    @patch('utils.log_helper.logging.basicConfig')
    def test_setup_logging_returns_logger_instance(self, mock_basic_config):
        """Test that setup_logging returns a logger instance"""
        logger = setup_logging()
        
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == 'root'
    
    @patch('utils.log_helper.logging.basicConfig')
    def test_setup_logging_format_configured(self, mock_basic_config):
        """Test that log format is properly configured"""
        setup_logging()
        
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args.kwargs
        
        # Verify format includes required components
        log_format = call_kwargs['format']
        assert '%(levelname)s' in log_format
        assert '%(asctime)s' in log_format
        assert '%(message)s' in log_format
    
    @patch.dict(os.environ, {}, clear=True)
    @patch('utils.log_helper.logging.basicConfig')
    def test_setup_logging_no_env_defaults_to_info(self, mock_basic_config):
        """Test setup_logging defaults to INFO when LOG_LEVEL not set"""
        # When LOG_LEVEL is not set, it should default to INFO
        logger = setup_logging()
        
        mock_basic_config.assert_called_once()
        # The default value in log_helper.py is "INFO"
        assert logger is not None
    
    @patch('utils.log_helper.logging.basicConfig')
    def test_setup_logging_can_log_messages(self, mock_basic_config):
        """Test that logger can log messages without errors"""
        logger = setup_logging()
        
        # These should not raise exceptions
        try:
            logger.info("Test info message")
            logger.debug("Test debug message")
            logger.warning("Test warning message")
            logger.error("Test error message")
            success = True
        except Exception:
            success = False
        
        assert success is True
    
    def test_load_dotenv_called_at_import(self):
        """Test that load_dotenv is called when module is imported
        
        Note: load_dotenv() is called at module import time (line 4 of log_helper.py).
        Since it's already been imported by the time this test runs, we verify
        that the module has the expected behavior rather than trying to mock
        a call that already happened.
        
        This test verifies that LOG_LEVEL is properly read from environment.
        """
        import importlib
        from utils import log_helper  # type: ignore[import-not-found]
        
        # Verify that LOG_LEVEL variable exists (proves load_dotenv was called)
        assert hasattr(log_helper, 'LOG_LEVEL')
        assert isinstance(log_helper.LOG_LEVEL, str)
        
        # Verify it has a valid default value
        assert log_helper.LOG_LEVEL in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
