import logging
import logging.config
import logging.handlers


config = {
  "version": 1,
  "disable_existing_loggers": False,
  "formatters": {
    "simple": {
      "format": "[%(asctime)s] - %(levelname)s - %(module)s(L%(lineno)d) : %(message)s",
      "datefmt": "%Y-%m-%dT%H:%M:%S%z"
    },
  },
  "handlers": {
    "stderr": {
      "class": "logging.StreamHandler",
      "level": "DEBUG",
      "formatter": "simple",
    },
  },
  "loggers": {
    "root": {
      "level": "DEBUG",
      "handlers": [
        "stderr"
      ]
    }
  }
}

def setup_logging(logger_name: str) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.WARNING)

    logging.config.dictConfig(config)

    return logger


logger = setup_logging("my_app")