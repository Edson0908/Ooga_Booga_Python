import logging
from colorama import Fore, Style

class CustomFormatter(logging.Formatter):
    """
    Custom Formatter to add colors to log messages based on their severity level.
    """
    LOG_COLORS = {
        logging.DEBUG: Fore.BLUE,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        log_color = self.LOG_COLORS.get(record.levelno, "")
        reset_color = Style.RESET_ALL
        record.msg = f"{log_color}{record.msg}{reset_color}"
        return super().format(record)


def get_logger(name: str, level=logging.INFO) -> logging.Logger:
    """
    Creates and configures a logger with colorized output.

    Args:
        name (str): Name of the logger.
        level (int): Logging level.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    handler = logging.StreamHandler()
    handler.setFormatter(CustomFormatter())

    # Clear existing handlers and set the custom handler
    logger.handlers = []
    logger.addHandler(handler)

    return logger
