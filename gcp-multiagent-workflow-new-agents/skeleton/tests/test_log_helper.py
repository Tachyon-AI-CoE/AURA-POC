"""Unit tests for log_helper module."""

import sys
import os
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Setup path for src
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
