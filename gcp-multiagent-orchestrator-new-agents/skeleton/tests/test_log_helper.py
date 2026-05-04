"""Unit tests for log_helper module."""

import sys
import os
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Setup path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


class TestLogHelper:
    """Test suite for logging helper utilities."""

    def test_setup_logging_default_level(self):
        """Test that setup_logging uses INFO level by default."""
        from utils.log_helper import setup_logging
        
        # Clear existing handlers
        root = logging.getLogger()
        root.handlers.clear()
        
        with patch.dict(os.environ, {}, clear=True):
            logger = setup_logging()
            
            assert logger is not None
            assert logger.level == logging.INFO

    def test_setup_logging_custom_level(self, monkeypatch):
        """Test that setup_logging respects LOG_LEVEL environment variable."""
        from utils.log_helper import setup_logging
        
        # Clear existing handlers
        root = logging.getLogger()
        root.handlers.clear()
        
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        logger = setup_logging()
        
        assert logger.level == logging.DEBUG

    def test_setup_logging_case_insensitive(self, monkeypatch):
        """Test that log level is case-insensitive."""
        from utils.log_helper import setup_logging
        
        # Clear existing handlers
        root = logging.getLogger()
        root.handlers.clear()
        
        monkeypatch.setenv("LOG_LEVEL", "debug")
        logger = setup_logging()
        
        assert logger.level == logging.DEBUG

    def test_setup_logging_idempotent(self):
        """Test that setup_logging can be called multiple times safely."""
        from utils.log_helper import setup_logging
        
        # Clear existing handlers
        root = logging.getLogger()
        root.handlers.clear()
        
        logger1 = setup_logging()
        logger2 = setup_logging()
        
        # Should return the same root logger
        assert logger1 is logger2

    def test_utc_formatter(self):
        """Test that _UTCFormatter uses UTC time."""
        from utils.log_helper import _UTCFormatter
        import time
        
        formatter = _UTCFormatter()
        
        # Check that converter is set to gmtime
        assert formatter.converter == time.gmtime

    def test_logging_format(self):
        """Test that log messages use the expected format."""
        from utils.log_helper import setup_logging, _DEFAULT_FMT, _UTCFormatter
        
        # Clear existing handlers
        root = logging.getLogger()
        root.handlers.clear()
        
        logger = setup_logging()
        
        # Check that a handler exists with the correct formatter
        assert len(logger.handlers) > 0
        handler = logger.handlers[0]
        assert handler.formatter is not None
        # Check it's the UTC formatter
        assert isinstance(handler.formatter, _UTCFormatter)
        # Check the format string
        assert handler.formatter._fmt == _DEFAULT_FMT

    def test_logging_handler_creation(self):
        """Test that logging handler is created correctly."""
        from utils.log_helper import setup_logging
        
        # Clear existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        logger = setup_logging()
        
        # Should have at least one handler
        assert len(logger.handlers) >= 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)

    def test_setup_logging_returns_root_logger(self):
        """Test that setup_logging returns the root logger."""
        from utils.log_helper import setup_logging
        
        logger = setup_logging()
        root_logger = logging.getLogger()
        
        assert logger is root_logger

    def test_logging_error_level(self, monkeypatch):
        """Test ERROR log level."""
        from utils.log_helper import setup_logging
        
        # Clear existing handlers
        root = logging.getLogger()
        root.handlers.clear()
        
        monkeypatch.setenv("LOG_LEVEL", "ERROR")
        logger = setup_logging()
        
        assert logger.level == logging.ERROR

    def test_logging_warning_level(self, monkeypatch):
        """Test WARNING log level."""
        from utils.log_helper import setup_logging
        
        # Clear existing handlers
        root = logging.getLogger()
        root.handlers.clear()
        
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        logger = setup_logging()
        
        assert logger.level == logging.WARNING
