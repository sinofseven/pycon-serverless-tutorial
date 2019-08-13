import json
import logging
import os


class JsonLogFormatter(logging.Formatter):
    def format(self, record):
        result = {}

        for attr, value in record.__dict__.items():
            if attr == 'asctime':
                value = self.formatTime(record)
            if attr == 'exc_info' and value is not None:
                value = self.formatException(value)
            if attr == 'stack_info' and value is not None:
                value = self.formatStack(value)

            try:
                json.dumps(value)
            except Exception:
                value = str(value)

            result[attr] = value

        result['lambda_request_id'] = os.environ.get('LAMBDA_REQUEST_ID')

        return json.dumps(result, ensure_ascii=False)
