import os
import logging
from dotenv import load_dotenv
load_dotenv()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

def setup_logging():
    LOG_FORMAT = "%(levelname)s %(asctime)s - %(message)s"
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
    )

    logger = logging.getLogger()
    return logger
