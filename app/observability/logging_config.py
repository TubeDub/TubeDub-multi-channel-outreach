import logging
import re

SENSITIVE_KEYS = ["token", "password", "secret", "api_key", "access_token"]

def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

class SecretFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        # crude masking: hide anything looking like token
        # bot token pattern: \d+:[\w-]{30,}
        record.msg = re.sub(r"\d+:[\w-]{30,}", "***TOKEN***", str(record.msg))
        for k in SENSITIVE_KEYS:
            record.msg = re.sub(rf"({k})=([^\s&]+)", rf"\1=***", str(record.msg), flags=re.I)
        return True

def get_logger(name: str):
    logger = logging.getLogger(name)
    logger.addFilter(SecretFilter())
    return logger
