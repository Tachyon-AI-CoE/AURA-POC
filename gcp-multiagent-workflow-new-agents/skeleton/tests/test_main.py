"""Tests for main.py — FastAPI app creation."""

import sys
import os
import types
import importlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from unittest.mock import MagicMock


class TestMainModule:
    """Test main.py by mocking get_fast_api_app."""

    def test_app_creation(self):
        mock_app = MagicMock()

        mock_fast_api_mod = types.ModuleType("google.adk.cli.fast_api")
        mock_fast_api_mod.get_fast_api_app = MagicMock(return_value=mock_app)

        saved_modules = {}
        modules_to_mock = {
            "google.adk.cli.fast_api": mock_fast_api_mod,
        }

        for name, mod in modules_to_mock.items():
            saved_modules[name] = sys.modules.get(name)
            sys.modules[name] = mod

        saved_main = sys.modules.pop("main", None)

        try:
            import main
            importlib.reload(main)
            assert main.app is mock_app
            assert main.SESSION_SERVICE_URI == "sqlite:///./sessions.db"
            assert main.SERVE_WEB_INTERFACE is True
        finally:
            if saved_main:
                sys.modules["main"] = saved_main
            else:
                sys.modules.pop("main", None)
            for name, saved in saved_modules.items():
                if saved is not None:
                    sys.modules[name] = saved
                else:
                    sys.modules.pop(name, None)
