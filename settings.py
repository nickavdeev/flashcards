import logging
import logging.config

CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        "database": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "service": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "app": {"level": "INFO", "handlers": ["console"], "propagate": False},
    },
    "root": {
        "level": "WARNING",
        "handlers": ["console"],
    },
}


def setup_logging():
    logging.config.dictConfig(CONFIG)
