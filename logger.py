import logging
import os


def setup_logger(name: str, log_dir: str = "logs") -> logging.Logger:
    """
    Configure and return a logger that writes DEBUG+ logs to a file and INFO+ to console.
    """
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # File handler (DEBUG level)
    file_path = os.path.join(log_dir, f"{name}.log")
    fh = logging.FileHandler(file_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)

    # Console handler (INFO level)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # Formatter
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)

    # Attach handlers
    if not logger.handlers:
        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger