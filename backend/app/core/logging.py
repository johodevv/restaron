import logging
import re


class RedactTokenFilter(logging.Filter):
    def filter(self, record):
        def redact(value):
            if isinstance(value, str):
                return re.sub(r'(token=)[^&\s\"\']+', r'\1[redacted]', value)
            return value

        # Uvicorn's AccessFormatter reads the original five positional args.
        # Flattening them into msg causes a formatter exception on every request.
        if record.name == 'uvicorn.access' and isinstance(record.args, tuple) and len(record.args) == 5:
            record.args = tuple(redact(value) for value in record.args)
        else:
            record.msg = redact(record.getMessage())
            record.args = ()
        return True


def install_token_redaction():
    for name in ('uvicorn.error', 'uvicorn.access'):
        logger = logging.getLogger(name)
        if not any(isinstance(f, RedactTokenFilter) for f in logger.filters):
            logger.addFilter(RedactTokenFilter())
