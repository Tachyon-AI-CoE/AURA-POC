import json
import yaml
from typing import Optional, Any

from utils.log_helper import setup_logging
logger = setup_logging()

class ConfigReader:
    _data = None  # Class variable to store configuration

    def __init__(self, file_path: str):
        """Initialize ConfigReader with a JSON or YAML file path."""
        try:
            with open(file_path, "r") as f:
                # Determine file type by extension
                if file_path.endswith(('.yaml', '.yml')):
                    ConfigReader._data = yaml.safe_load(f)
                    logger.info(f"✅ Loaded YAML configuration from {file_path}")
                elif file_path.endswith('.json'):
                    ConfigReader._data = json.load(f)
                    logger.info(f"✅ Loaded JSON configuration from {file_path}")
                else:
                    # Try YAML first, then JSON as fallback
                    content = f.read()
                    f.seek(0)
                    try:
                        ConfigReader._data = yaml.safe_load(content)
                        logger.info(f"✅ Loaded configuration as YAML from {file_path}")
                    except yaml.YAMLError:
                        ConfigReader._data = json.loads(content)
                        logger.info(f"✅ Loaded configuration as JSON from {file_path}")
        except FileNotFoundError:
            logger.error(f"❌ Error: Configuration file not found at {file_path}")
            raise
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            logger.error(f"❌ Error: Invalid JSON/YAML format in {file_path}: {e}")
            raise

    @classmethod
    def get_value(cls, key: str, default_value: Any = None) -> Any:
        """Get value from configuration by key."""
        if cls._data is None:
            raise RuntimeError(
                "Configuration not loaded. Initialize ConfigReader first."
            )
        value = cls._data.get(key)
        if value:
            return value
        else:
            return default_value
