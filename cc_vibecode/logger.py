import logging
import os
from datetime import datetime

# Global flag to ensure logging is configured only once
_logging_configured = False


def create_logger(name: str):
    global _logging_configured

    if not _logging_configured:
        os.makedirs("logs", exist_ok=True)
        date_fmt = datetime.now().strftime("%Y%m%d-%H%M.log")
        log_filename = f"app-{date_fmt}"
        log_path = os.path.join("logs", log_filename)

        # logging configuration with name in format
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_path), logging.StreamHandler()],
        )
        _logging_configured = True

    logger = logging.getLogger(name)
    return logger
