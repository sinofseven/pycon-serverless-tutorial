import logging
import logging.config


def get_logging_config():
    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'logFormatter': {
                '()': 'logger.json_formatter.JsonLogFormatter'
            }
        },
        'loggers': {
            'console': {
                'handlers': ['consoleHandler'],
                'level': 'DEBUG'
            },
            'botocore': {
                'handlers': ['consoleHandler'],
                'level': 'INFO'
            }
        },
        'handlers': {
            'consoleHandler': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'logFormatter'
            }
        },
        'root': {
            'handlers': ['consoleHandler'],
            'level': 'DEBUG'
        }
    }


def get_logger(name):
    logging.config.dictConfig(get_logging_config())
    return logging.getLogger(name)
